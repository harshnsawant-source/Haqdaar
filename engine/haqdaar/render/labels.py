"""Display names for documents.

Presentation only. A document id is an internal key (`bpl_ration_card`); a citizen
reads a name (`BPL ration card`). Turning one into the other by replacing underscores
produced "bring your bpl ration card" and "proven from your land record 7 12", which
reads as though the machine does not know what it is talking about.

This is deliberately NOT in the template set. Template text is audited for digits,
because every number a citizen reads must trace back to a predicate — and "7/12
extract" is the actual name of a Maharashtra land record, digits and all. A document
name is an identifier, not a claim about anyone, so it lives here instead.

Marathi: `document_label` takes a language today only to keep the call sites honest;
there is no `mr` map yet, and it falls back to the English name rather than inventing a
transliteration. A native speaker adds the Marathi names alongside the template set.
"""

from __future__ import annotations

#: Names that are not simply title-cased. Anything absent falls through to the
#: acronym-aware default below.
_EN: dict[str, str] = {
    "aadhaar": "Aadhaar",
    "age_proof": "age proof",
    "bank_passbook": "bank passbook",
    "bpl_ration_card": "BPL ration card",
    "caste_certificate": "caste certificate",
    "divorce_decree": "divorce decree",
    "domicile_certificate": "domicile certificate",
    "husband_death_certificate": "death certificate",
    "income_certificate": "income certificate",
    "itr": "income tax return",
    "land_record_7_12": "7/12 land record",
    "pension_order": "pension order",
    "project_report": "project report",
    "self_declaration": "self-declaration",
}

#: Tokens that are acronyms and stay upper case wherever they appear.
_ACRONYMS = frozenset({"bpl", "sc", "st", "obc", "pan", "ifsc", "itr", "secc", "id"})


def field_label(profile_field: str, language: str = "en") -> str:
    """A citizen-facing name for a profile field path.

    `applicant.social_category` reads as "social category". The namespace is dropped
    because it is ours, not hers — she does not think of herself as an `applicant.`
    """
    return profile_field.rsplit(".", 1)[-1].replace("_", " ")


def document_label(document_id: str, language: str = "en") -> str:
    """A citizen-facing name for a document id.

    Lower case by default because these appear mid-sentence ("bring your caste
    certificate"). Acronyms and proper nouns keep their casing.
    """
    known = _EN.get(document_id)
    if known is not None:
        return known

    words = [w for w in document_id.replace("-", "_").split("_") if w]
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.lower() for w in words)
