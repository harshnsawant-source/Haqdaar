"""Form definitions: which application field is filled by which profile fact.

Data, like the scheme corpus. A form is a field map, and filling it is deterministic
slot-mapping — no model writes anything a citizen or an office reads.

Two honesty rules are enforced here rather than left to discipline:

1. A **stand-in** form (`is_stand_in: true`) is a representative layout we built, not
   the official document. Every one of its labels must carry [VERIFY AT SOURCE].
2. A stand-in form may not claim a field is REQUIRED. We have not read the official
   form, so we do not know what the government requires; every field is UNVERIFIED
   until someone reads the real one. Claiming a requirement we cannot source is the
   same failure as inventing an eligibility rule.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from haqdaar.corpus.schema import VERIFY_MARKER, VerificationStatus


class Requirement(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    #: We have not read the official form, so we do not know. The only honest value
    #: for a stand-in.
    UNVERIFIED = "UNVERIFIED"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FormField(_Frozen):
    field_id: str
    label: str
    #: Dotted path into CitizenProfile. None means nothing we hold can fill it.
    profile_field: str | None = None
    requirement: Requirement = Requirement.UNVERIFIED
    #: Documents that would supply this field, for the gap list.
    obtainable_from: list[str] = Field(default_factory=list)
    note: str | None = None


class FormSection(_Frozen):
    section_id: str
    title: str
    fields: list[FormField] = Field(min_length=1)


class FormDefinition(_Frozen):
    form_id: str
    scheme_id: str
    title: str
    verification_status: VerificationStatus
    verify_note: str
    retrieved_on: date
    #: True when this is a representative layout we built, not the official document.
    is_stand_in: bool = True
    source_url: str | None = None
    sections: list[FormSection] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> FormDefinition:
        seen: set[str] = set()
        for section in self.sections:
            for field in section.fields:
                if field.field_id in seen:
                    raise ValueError(
                        f"{self.form_id}: duplicate field_id {field.field_id}"
                    )
                seen.add(field.field_id)

                if not self.is_stand_in:
                    continue
                if VERIFY_MARKER not in field.label:
                    raise ValueError(
                        f"{self.form_id}:{field.field_id}: a stand-in form's labels "
                        f"must carry {VERIFY_MARKER} — this is not the official form"
                    )
                if field.requirement is not Requirement.UNVERIFIED:
                    raise ValueError(
                        f"{self.form_id}:{field.field_id}: a stand-in form cannot "
                        "claim a field is REQUIRED or OPTIONAL. Nobody has read the "
                        "official form, so the requirement is UNVERIFIED."
                    )
        return self

    def fields(self) -> list[FormField]:
        return [f for s in self.sections for f in s.fields]


def load_form(path: str | Path) -> FormDefinition:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: expected a mapping at the top level")
    return FormDefinition.model_validate(raw)


def load_form_for(forms_dir: str | Path, scheme_id: str) -> FormDefinition | None:
    """Return the form for a scheme, or None when we have no form for it yet."""
    path = Path(forms_dir) / f"{scheme_id}.form.yaml"
    return load_form(path) if path.is_file() else None
