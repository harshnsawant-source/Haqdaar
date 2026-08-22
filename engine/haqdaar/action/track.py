"""Tracking references for simulated submissions.

The reference must be three things at once: stable (so a golden test can pin it and a
rehearsal produces the same string twice), unique per application, and *obviously not a
government reference number*. The third matters most. A plausible-looking reference is
the one artefact of this demo a citizen could carry away and act on, so it says SIM in
the first four characters and never adopts the shape of a real portal acknowledgement.

No network, no clock read, no randomness: the date is passed in and the suffix is a
digest of the application's own identity.
"""

from __future__ import annotations

import hashlib
from datetime import date

from haqdaar.action.fill import FilledForm, Receipt

#: Deliberately not a plausible government prefix.
SIMULATED_PREFIX = "SIM"


def _slug(scheme_id: str) -> str:
    return "".join(c for c in scheme_id.upper() if c.isalnum())[:10]


def tracking_reference(
    filled_form: FilledForm, profile_id: str, submitted_on: date
) -> str:
    """Deterministic reference. Same inputs, same string, every rehearsal."""
    digest = hashlib.sha256(
        "|".join(
            [
                filled_form.form_id,
                profile_id,
                submitted_on.isoformat(),
                *(f.field_id for f in filled_form.filled),
            ]
        ).encode("utf-8")
    ).hexdigest()[:6].upper()
    return (
        f"{SIMULATED_PREFIX}-{_slug(filled_form.scheme_id)}-"
        f"{submitted_on.strftime('%Y%m%d')}-{digest}"
    )


def submit(filled_form: FilledForm, profile_id: str, submitted_on: date) -> Receipt:
    """Produce a simulated receipt. Nothing is sent anywhere.

    There is no network call here and there will not be one: real portal integration is
    explicitly out of scope for this round (PROJECT-BRIEF.md s4), and a demo that
    quietly posted to a government endpoint would be a far worse problem than a demo
    that admits it simulates.
    """
    return Receipt(
        reference=tracking_reference(filled_form, profile_id, submitted_on),
        submitted_on=submitted_on,
        scheme_id=filled_form.scheme_id,
        form_id=filled_form.form_id,
    )
