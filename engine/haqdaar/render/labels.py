"""Display names for documents.

Presentation only. A document id is an internal key (`bpl_ration_card`); a citizen
reads a name (`BPL ration card`). Turning one into the other by replacing underscores
produced "bring your bpl ration card" and "proven from your land record 7 12", which
reads as though the machine does not know what it is talking about.

This is deliberately NOT in the template set. Template text is audited for digits,
because every number a citizen reads must trace back to a predicate — and "7/12
extract" is the actual name of a Maharashtra land record, digits and all. A document
name is an identifier, not a claim about anyone, so it lives here instead.

LANGUAGES: Marathi and Hindi maps were added on 2026-08-26 and are AWAITING
NATIVE-SPEAKER REVIEW along with everything else in docs/TRANSLATION-REVIEW.md.

These matter more than they look. They are the SLOT VALUES inside translated
sentences, so before they existed a Marathi card read "नियम सांगतो 70 and above.
तुमचे age आहे 60." — a translated frame around English contents, which is worse
than either language on its own.

Anything with no entry falls back to English rather than inventing a
transliteration. A missing document name should look untranslated, not made up.
"""

from __future__ import annotations

#: Names that are not simply title-cased. Anything absent falls through to the
#: acronym-aware default below.
_EN: dict[str, str] = {
    "aadhaar": "Aadhaar",
    "admission_letter": "admission letter",
    "age_proof": "age proof",
    "bonafide_certificate": "bonafide student certificate",
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
    "school_id_card": "school ID card",
    "self_declaration": "self-declaration",
}

_MR_DOCS: dict[str, str] = {
    "aadhaar": "आधार",
    "admission_letter": "प्रवेश पत्र",
    "age_proof": "वयाचा पुरावा",
    "bank_passbook": "बँक पासबुक",
    "bonafide_certificate": "बोनाफाईड दाखला",
    "bpl_ration_card": "दारिद्र्यरेषेखालील शिधापत्रिका",
    "caste_certificate": "जातीचा दाखला",
    "divorce_decree": "घटस्फोटाचा आदेश",
    "domicile_certificate": "अधिवास दाखला",
    "husband_death_certificate": "मृत्यू दाखला",
    "income_certificate": "उत्पन्नाचा दाखला",
    "itr": "प्राप्तिकर विवरणपत्र",
    "land_record_7_12": "सातबारा उतारा",
    "pension_order": "निवृत्तिवेतन आदेश",
    "project_report": "प्रकल्प अहवाल",
    "school_id_card": "शाळेचे ओळखपत्र",
    "self_declaration": "स्वयंघोषणापत्र",
}

_HI_DOCS: dict[str, str] = {
    "aadhaar": "आधार",
    "admission_letter": "प्रवेश पत्र",
    "age_proof": "आयु प्रमाण",
    "bank_passbook": "बैंक पासबुक",
    "bonafide_certificate": "बोनाफाइड प्रमाणपत्र",
    "bpl_ration_card": "गरीबी रेखा से नीचे का राशन कार्ड",
    "caste_certificate": "जाति प्रमाणपत्र",
    "divorce_decree": "तलाक का आदेश",
    "domicile_certificate": "निवास प्रमाणपत्र",
    "husband_death_certificate": "मृत्यु प्रमाणपत्र",
    "income_certificate": "आय प्रमाणपत्र",
    "itr": "आयकर विवरणी",
    "land_record_7_12": "सात बारह भू-अभिलेख",
    "pension_order": "पेंशन आदेश",
    "project_report": "परियोजना रिपोर्ट",
    "school_id_card": "स्कूल पहचान पत्र",
    "self_declaration": "स्वघोषणा पत्र",
}

_DOCS = {"mr": _MR_DOCS, "hi": _HI_DOCS}

#: Tokens that are acronyms and stay upper case wherever they appear.
_ACRONYMS = frozenset({"bpl", "sc", "st", "obc", "pan", "ifsc", "itr", "secc", "id"})


#: Field paths whose last segment does not make a readable phrase on its own.
#: Splitting `student.admission_secured` on underscores produced "Your admission
#: secured is false", which is not a sentence. Anything absent falls through to the
#: underscore split, which is fine for `applicant.age` and `household.annual_income`.
_FIELD_EN: dict[str, str] = {
    "applicant.constitutional_post": "having held a constitutional post",
    "applicant.government_employee": "being a government employee",
    "applicant.monthly_pension": "monthly pension",
    "applicant.paid_income_tax": "having paid income tax last year",
    "applicant.registered_professional": "being a registered practising professional",
    "applicant.social_category": "social category",
    "household.annual_income": "annual family income",
    "household.bpl": "being on the BPL list",
    "household.institutional_landholder": "the land being held by an institution",
    "household.landholding_hectares": "cultivable land held",
    "student.admission_secured": "having secured admission to a full time course",
    "student.other_central_prematric_scholarship": (
        "receiving another centrally funded pre-matric scholarship"
    ),
    "student.school_recognised": "studying full time at a recognised school",
}


_MR_FIELDS: dict[str, str] = {
    "applicant.age": "वय",
    "applicant.constitutional_post": "घटनात्मक पद भूषवलेले असणे",
    "applicant.gender": "लिंग",
    "applicant.government_employee": "सरकारी कर्मचारी असणे",
    "applicant.marital_status": "वैवाहिक स्थिती",
    "applicant.monthly_pension": "मासिक निवृत्तिवेतन",
    "applicant.paid_income_tax": "मागील वर्षी आयकर भरलेला असणे",
    "applicant.registered_professional": "नोंदणीकृत व्यावसायिक असणे",
    "applicant.social_category": "सामाजिक प्रवर्ग",
    "enterprise.loan_amount_sought": "मागितलेली कर्जाची रक्कम",
    "enterprise.venture_type": "व्यवसायाचा प्रकार",
    "household.annual_income": "कुटुंबाचे वार्षिक उत्पन्न",
    "household.bpl": "दारिद्र्यरेषेखालील यादीत असणे",
    "household.institutional_landholder": "जमीन संस्थेच्या नावे असणे",
    "household.landholding_hectares": "धारण केलेली लागवडीयोग्य जमीन",
    "student.admission_secured": "पूर्णवेळ अभ्यासक्रमास प्रवेश मिळालेला असणे",
    "student.class_level": "इयत्ता",
    "student.other_central_prematric_scholarship": "दुसरी केंद्र पुरस्कृत मॅट्रिकपूर्व शिष्यवृत्ती मिळणे",
    "student.school_recognised": "मान्यताप्राप्त शाळेत पूर्णवेळ शिकणे",
    "student.year_of_study": "अभ्यासक्रमाचे वर्ष",
}

_HI_FIELDS: dict[str, str] = {
    "applicant.age": "उम्र",
    "applicant.constitutional_post": "संवैधानिक पद पर रह चुके होना",
    "applicant.gender": "लिंग",
    "applicant.government_employee": "सरकारी कर्मचारी होना",
    "applicant.marital_status": "वैवाहिक स्थिति",
    "applicant.monthly_pension": "मासिक पेंशन",
    "applicant.paid_income_tax": "पिछले वर्ष आयकर भरा होना",
    "applicant.registered_professional": "पंजीकृत व्यवसायी होना",
    "applicant.social_category": "सामाजिक वर्ग",
    "enterprise.loan_amount_sought": "मांगी गई ऋण राशि",
    "enterprise.venture_type": "व्यवसाय का प्रकार",
    "household.annual_income": "परिवार की वार्षिक आय",
    "household.bpl": "गरीबी रेखा से नीचे की सूची में होना",
    "household.institutional_landholder": "ज़मीन संस्था के नाम होना",
    "household.landholding_hectares": "धारित कृषि योग्य भूमि",
    "student.admission_secured": "पूर्णकालिक पाठ्यक्रम में दाखिला मिला होना",
    "student.class_level": "कक्षा",
    "student.other_central_prematric_scholarship": "अन्य केंद्रीय मैट्रिक-पूर्व छात्रवृत्ति मिलना",
    "student.school_recognised": "मान्यता प्राप्त स्कूल में पूर्णकालिक पढ़ना",
    "student.year_of_study": "पाठ्यक्रम का वर्ष",
}

_FIELDS = {"mr": _MR_FIELDS, "hi": _HI_FIELDS}

#: Corpus value tokens a citizen reads inside a sentence.
_MR_VALUES: dict[str, str] = {
    "SC": "अनुसूचित जाती", "ST": "अनुसूचित जमाती", "OBC": "इतर मागास प्रवर्ग",
    "GENERAL": "खुला प्रवर्ग", "FEMALE": "स्त्री", "MALE": "पुरुष",
    "TRANSGENDER": "तृतीयपंथी", "WIDOW": "विधवा", "DIVORCED": "घटस्फोटित",
    "MARRIED": "विवाहित", "UNMARRIED": "अविवाहित",
    "GREENFIELD": "पहिला व्यवसाय", "EXISTING": "आधीच सुरू असलेला व्यवसाय",
    "true": "होय", "false": "नाही",
}

_HI_VALUES: dict[str, str] = {
    "SC": "अनुसूचित जाति", "ST": "अनुसूचित जनजाति", "OBC": "अन्य पिछड़ा वर्ग",
    "GENERAL": "सामान्य वर्ग", "FEMALE": "महिला", "MALE": "पुरुष",
    "TRANSGENDER": "ट्रांसजेंडर", "WIDOW": "विधवा", "DIVORCED": "तलाकशुदा",
    "MARRIED": "विवाहित", "UNMARRIED": "अविवाहित",
    "GREENFIELD": "पहला व्यवसाय", "EXISTING": "पहले से चल रहा व्यवसाय",
    "true": "हां", "false": "नहीं",
}

_VALUES = {"mr": _MR_VALUES, "hi": _HI_VALUES}

#: How a numeric range reads. Kept here beside the words rather than in render.py,
#: because "and above" is vocabulary, not logic. {n} is the number, never translated.
BOUND_PHRASES = {
    "en": {"between": "{a} to {b}", "min": "{a} and above", "max": "{a} and below", "or": " or "},
    "mr": {"between": "{a} ते {b}", "min": "{a} किंवा त्याहून अधिक", "max": "{a} किंवा त्याहून कमी", "or": " किंवा "},
    "hi": {"between": "{a} से {b}", "min": "{a} या उससे अधिक", "max": "{a} या उससे कम", "or": " या "},
}


def field_label(profile_field: str, language: str = "en") -> str:
    """A citizen-facing name for a profile field path.

    `applicant.social_category` reads as "social category". The namespace is dropped
    because it is ours, not hers — she does not think of herself as an `applicant.`
    """
    translated = _FIELDS.get(language, {}).get(profile_field)
    if translated is not None:
        return translated
    known = _FIELD_EN.get(profile_field)
    if known is not None:
        return known
    return profile_field.rsplit(".", 1)[-1].replace("_", " ")


def value_label(value: object, language: str = "en") -> str:
    """A citizen-facing rendering of a corpus value token.

    WIDOW reads as "widow", SC stays "SC". These are the corpus's own values, so this
    only changes how they are written, never what they are.

    Numbers pass through untouched. They used to go through the same word-splitting as
    category tokens, which treats "-" as a separator — so -5 rendered as "5", and a
    card told a citizen "Your age is 5" about an age of minus five. Changing the number
    a person is shown is never a formatting decision.
    """
    if isinstance(value, bool):
        value = "true" if value else "false"

    translated = _VALUES.get(language, {}).get(str(value))
    if translated is not None:
        return translated

    if isinstance(value, bool):
        return "yes" if value else "no"
    # The corpus writes booleans as the strings "true"/"false", because a CategoryBound
    # compares as strings. A citizen should still read yes and no.
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return "yes" if value.lower() == "true" else "no"
    if isinstance(value, (int, float)):
        return str(value)

    words = [w for w in str(value).replace("-", "_").split("_") if w]
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.lower() for w in words)


def document_label(document_id: str, language: str = "en") -> str:
    """A citizen-facing name for a document id.

    Lower case by default because these appear mid-sentence ("bring your caste
    certificate"). Acronyms and proper nouns keep their casing.
    """
    translated = _DOCS.get(language, {}).get(document_id)
    if translated is not None:
        return translated

    known = _EN.get(document_id)
    if known is not None:
        return known

    words = [w for w in document_id.replace("-", "_").split("_") if w]
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.lower() for w in words)
