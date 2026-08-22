"""A+ — the action layer. Deterministic slot-mapping from profile facts to form fields.

Design doc s5. This is the third hook: it does not advise you about your loan, it fills
the application. Same rule as everywhere else — no model writes anything a citizen or
an office reads. A filled field is a value the citizen's own document supplied, carried
across with its provenance intact.

Three refusals are built into this module, because an action layer that acts when it
should not is worse than one that does nothing:

* **It will not act on a verdict the engine could not clear.** You do not file an
  application for someone whose eligibility is UNVERIFIABLE, BLOCKED or NOT_ELIGIBLE.
* **It will not invent a value.** A field the profile cannot fill goes in the gap list.
  There is no default, no placeholder, no "reasonable assumption".
* **It cannot pretend to be a real filing.** `simulated` is typed as Literal[True]; the
  model will not construct with anything else.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from haqdaar.corpus.forms import FormDefinition, FormField
from haqdaar.eligibility.verdict import ApprovalStatus, Status, Verdict
from haqdaar.profile.schema import CitizenProfile


class ActionRefused(Exception):
    """The action layer declined to act. Never a silent no-op."""


class FilledField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field_id: str
    label: str
    value: bool | int | float | str
    #: Which document supplied it. Every filled value is traceable to a document.
    source_document: str
    profile_field: str


class GapField(BaseModel):
    """A field we could not fill. Named, never guessed at."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field_id: str
    label: str
    #: Documents that would supply it, for "you still need X".
    obtainable_from: list[str] = Field(default_factory=list)
    note: str | None = None


class FilledForm(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    form_id: str
    scheme_id: str
    title: str
    #: Not removable. This is never a real filing, and the type says so.
    simulated: Literal[True] = True
    #: True when the form layout is our stand-in rather than the official document.
    is_stand_in: bool = True
    filled: list[FilledField] = Field(default_factory=list)
    gaps: list[GapField] = Field(default_factory=list)
    #: Carried through when the scheme has an outstanding discretionary condition, so
    #: the receipt never reads as "approved".
    approval_pending_by: list[str] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.gaps


class Receipt(BaseModel):
    """A simulated submission. The reference is local and says so."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference: str
    simulated: Literal[True] = True
    submitted_on: date
    scheme_id: str
    form_id: str


def _document_for(field: FormField, profile: CitizenProfile) -> str | None:
    if not field.profile_field:
        return None
    value = profile.get(field.profile_field)
    return value.document_id if value else None


def fill_form(
    form: FormDefinition, verdict: Verdict, profile: CitizenProfile
) -> FilledForm:
    """Map profile facts onto form fields. Unfillable fields become gaps.

    Refuses unless the verdict cleared eligibility. Note that an outstanding *approval*
    condition does not block filing: eligibility is what entitles her to apply, and the
    bank's appraisal happens after the application exists. Suppressing the application
    because the bank has not yet decided would be the approval-is-not-eligibility
    mistake all over again, one layer up.
    """
    if verdict.scheme_id != form.scheme_id:
        raise ActionRefused(
            f"form {form.form_id} is for {form.scheme_id}, verdict is for "
            f"{verdict.scheme_id}"
        )
    if verdict.status is not Status.ELIGIBLE:
        raise ActionRefused(
            f"{verdict.scheme_id}: will not fill an application on a "
            f"{verdict.status.value} verdict — the engine could not clear eligibility"
        )

    filled: list[FilledField] = []
    gaps: list[GapField] = []

    for field in form.fields():
        document = _document_for(field, profile)
        if field.profile_field and document:
            value = profile.get(field.profile_field)
            filled.append(
                FilledField(
                    field_id=field.field_id,
                    label=field.label,
                    value=value.value,
                    source_document=document,
                    profile_field=field.profile_field,
                )
            )
        else:
            gaps.append(
                GapField(
                    field_id=field.field_id,
                    label=field.label,
                    obtainable_from=list(field.obtainable_from),
                    note=field.note,
                )
            )

    approval_pending: list[str] = []
    if (
        verdict.approval is not None
        and verdict.approval.status is not ApprovalStatus.SETTLED
    ):
        approval_pending = list(verdict.approval.deciders)

    return FilledForm(
        form_id=form.form_id,
        scheme_id=form.scheme_id,
        title=form.title,
        is_stand_in=form.is_stand_in,
        filled=filled,
        gaps=gaps,
        approval_pending_by=approval_pending,
    )


def missing_documents(filled_form: FilledForm) -> list[str]:
    """Documents that would close gaps, most useful first, deduplicated.

    Ranked by how many gaps each one closes, ties broken alphabetically so the order is
    stable on stage. Same honesty rule as the unlock aggregator: this says which
    documents help, and the count is of gaps closed, not of promises made.
    """
    counts: dict[str, int] = {}
    for gap in filled_form.gaps:
        for document in gap.obtainable_from:
            counts[document] = counts.get(document, 0) + 1
    return sorted(counts, key=lambda d: (-counts[d], d))
