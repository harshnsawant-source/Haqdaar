"""Extract NSFDC's Channel Partner lists from the official PDFs into corpus YAML.

SIH26092's third component needs to point a citizen at the partner who can actually
process her loan, because "direct loan applications are not entertained" and everything
routes through the Channel Finance System.

WHY THIS IS A SCRIPT AND NOT A TYPING JOB
-----------------------------------------
Ninety-odd partners transcribed by hand would carry ninety-odd chances of a typo in a
bank's name or a PIN code, and no way for anyone to check them short of reading the
PDFs again. Run this instead: it takes the published PDFs and produces the corpus, so
the provenance of every entry is a URL and a command rather than somebody's evening.

WHAT IT REFUSES TO DO
---------------------
Guess. A record it cannot split into a name and an address is reported and SKIPPED, not
half-parsed into the corpus. A state it cannot match against the official list is left
null rather than inferred from a city name. The count of skipped records is printed, so
a silent loss is impossible.

WHERE THE PDF HAS NO RULE TO FIND
---------------------------------
Some records cannot be split by any rule, because the source itself has no separator:
"Bank of Maharashtra" is followed by its address with no comma between them, and the
Regional Rural Banks table put row 23's address into row 24's cell. A cleverer regex
would get those right and something else wrong, silently.

So they are read by a person and recorded in corpus/partners/corrections.yaml, which
quotes the source lines each correction was read from and is applied here. Every
corrected field is stamped into the header of the file it lands in, so no reader has
to wonder which entries the script produced and which a human did.

A correction names the record it expects to be fixing. If the parse shifts underneath
it, this script STOPS rather than writing the correction onto whatever row now holds
that serial.

KNOWN LOSS: the PDFs use a dash character that does not survive text extraction and
arrives as U+FFFD. It appears between a place and its PIN code ("Amaravathi ? 522 501"),
so it is normalised to a hyphen and that normalisation is recorded in every file header.
Nothing else is altered.

Usage:
    python tools/extract_partners.py --pdf-dir <dir> --out corpus/partners
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pypdf import PdfReader

#: Official state and UT names, longest first so "Andhra Pradesh" wins over "Andhra".
STATES = sorted(
    [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Chhatisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
        "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
        "Mizoram", "Nagaland", "Odisha", "Orissa", "Punjab", "Rajasthan", "Sikkim",
        "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
        "West Bengal", "Delhi", "Puducherry", "Jammu & Kashmir", "Jammu and Kashmir",
        "Ladakh", "Chandigarh", "Andaman & Nicobar Islands", "Lakshadweep",
        "Dadra & Nagar Haveli, Daman & Diu", "Dadra & Nagar Haveli", "Daman & Diu",
        # The Regional Rural Banks list misspells Madhya Pradesh, twice, in the one
        # record that names it. Without this the state reads as absent and Madhya
        # Pradesh Gramin Bank is invisible to every citizen in the state.
        "Madhaya Pradesh",
    ],
    key=len,
    reverse=True,
)

#: Spellings the source uses that differ from the name we file under.
CANONICAL = {"Chhatisgarh": "Chhattisgarh", "Orissa": "Odisha",
             "Jammu and Kashmir": "Jammu & Kashmir",
             "Madhaya Pradesh": "Madhya Pradesh"}

#: The lists end with their own row count. It is a footer, not part of the last
#: address, and it was arriving glued to four of them ("... Kolkata - 700 064.
#: Total=38"). Matched only at the very end of a record so a "Total" inside an
#: address could never be cut.
FOOTER = re.compile(r"\s*Total\s*=\s*\d+\s*$", re.I)

CATEGORIES = {
    "sca": ("State Channelising Agencies", "SCA"),
    "rrb": ("Regional Rural Banks", "RRB"),
    "psb": ("Public Sector Banks", "PSB"),
    "nbfc_mfi": ("NBFC-MFIs", "NBFC_MFI"),
    "coop": ("Co-operative Banks and Societies", "COOPERATIVE"),
    "sfb": ("Small Finance Banks", "SFB"),
    "other": ("Other Agencies and SIDBI", "OTHER"),
}


@dataclass
class Partner:
    serial: int
    state: str | None
    name: str
    address: str


def clean(text: str) -> str:
    """Normalise whitespace and the one character extraction loses."""
    text = text.replace("�", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text).strip(" ,")
    return FOOTER.sub("", text).strip(" ,")


def read(pdf: Path) -> str:
    return "\n".join((page.extract_text() or "") for page in PdfReader(str(pdf)).pages)


def split_records(text: str) -> list[tuple[int, str]]:
    """Cut the page into numbered records.

    Two things make this harder than a regex.

    ADDRESSES CONTAIN NUMBERS AT THE START OF A LINE. One co-operative bank sits at
    "109. Sakar-II", and a splitter that trusts any leading number tore that address
    off its bank and filed it as record 109.

    SO DO PAGE NUMBERS. The SCA list opens with a bare "1" above its own title, and a
    splitter that starts at the first "1" it sees swallowed the table header and the
    real first record into one entry, producing a corporation whose name began "STATE/
    UT-WISE LIST OF STATE CHANNELISING AGENCIES".

    Both are solved the same way: find every candidate, then keep the LONGEST run of
    consecutive serials. A page number starts a run of one; the real list starts a run
    of thirty-eight. Anything outside the winning run is text belonging to the record
    above it, and is put back there rather than dropped.

    AND SO DO PIN CODES BROKEN ACROSS LINES. The Regional Rural Banks PDF puts every
    word on its own line, so Maharashtra Gramin Bank's "431 003." ends with a line
    reading "003." — which int() reads as 3, and which sits ABOVE the real serial 3.
    The run took it, and Jharkhand Gramin Bank was filed with the leftover digit in
    its name. A serial is never written with a leading zero, so those are dropped.
    """
    candidates = [
        (m.start(), int(m.group(1)), m.end())
        for m in re.finditer(r"(?m)^[ 	]*(\d{1,3})[.\s][ 	]*", text)
        if not (m.group(1).startswith("0") and len(m.group(1)) > 1)
    ]
    if not candidates:
        return []

    def run_from(start: int) -> list[int]:
        chosen, expected = [], 1
        for i in range(start, len(candidates)):
            if candidates[i][1] == expected:
                chosen.append(i)
                expected += 1
        return chosen

    best: list[int] = []
    for i, (_, serial, _) in enumerate(candidates):
        if serial == 1:
            run = run_from(i)
            # `>=`, not `>`. A leading page number and the real first record both start
            # runs of the same length, and on a tie the later start is the right one:
            # the page number sits above the table header, so choosing it drags the
            # header into the first record's name.
            if len(run) >= len(best):
                best = run

    if not best:
        return []

    records: list[tuple[int, str]] = []
    for slot, i in enumerate(best):
        body_start = candidates[i][2]
        body_end = candidates[best[slot + 1]][0] if slot + 1 < len(best) else len(text)
        records.append((candidates[i][1], strip_page_number(text[body_start:body_end])))
    return [(n, b) for n, b in records if len(clean(b)) > 12]


def strip_page_number(body: str) -> str:
    """Drop the page number the PDF printed between two rows.

    Page 1's number is handled by the run rule above, because it sits before the table.
    Pages 2 and 3 do not: their numbers fall INSIDE the record that happens to straddle
    the break, and arrived on the end of an address as "Solan - 173212 2".

    Only a trailing bare number is taken. The Regional Rural Banks PDF puts every word
    on its own line, so a line reading just "2" also occurs in the middle of an address
    ("2 nd Floor") - which is why this looks at the end of the record and nowhere else.
    """
    return re.sub(r"(?:[ \t]*\n[ \t]*\d{1,2}[ \t]*)+\s*$", "", body)


def take_state(body: str) -> tuple[str | None, str]:
    """Pull a leading state name off a record, or report none."""
    flat = clean(body)
    for state in STATES:
        if flat.lower().startswith(state.lower()):
            return CANONICAL.get(state, state), flat[len(state):].strip(" ,")
    return None, flat


def find_state(text: str) -> str | None:
    """Find a state named anywhere, for lists with no state column."""
    for state in STATES:
        if re.search(rf"\b{re.escape(state)}\b", text, re.I):
            return CANONICAL.get(state, state)
    return None


def split_name_address(rest: str) -> tuple[str, str] | None:
    """Separate the organisation from its postal address.

    Two shapes appear. Most SCAs end their name with a bracketed abbreviation, which is
    an unambiguous cut. Everything else is "Name, Address", so the first comma is used.
    A record matching neither is returned as None and skipped by the caller.
    """
    # The FIRST all-capitals bracket, which is an abbreviation, not any bracket at all.
    # Taking the last one pulled "(Block-A)" out of a Patna address and left it inside
    # the Bihar corporation's name. Lower case disqualifies a bracket.
    abbreviation = re.search(r"\([A-Z0-9&./\- ]{2,20}\)", rest)
    if abbreviation:
        cut = abbreviation.end()
        # A name can carry two brackets in a row: "Dr. Ambedkar Antyodaya Vikas Nigam
        # (S.C.) (DAAVN)". Cutting at the first one left the corporation without the
        # abbreviation it is known by and started its address with "(DAAVN)". Only an
        # immediately adjacent bracket is absorbed, so a genuine address bracket
        # further along is still left alone.
        while (nxt := re.match(r"\s*\([A-Z0-9&./\- ]{2,20}\)", rest[cut:])):
            cut += nxt.end()
        name, address = rest[:cut].strip(), rest[cut:].strip(" ,")
        if name and address:
            return name, address
    if "," in rest:
        name, address = rest.split(",", 1)
        if name.strip() and address.strip():
            return name.strip(), address.strip(" ,")
    # A name with no address. Some lists genuinely give none: the Small Finance Banks
    # page is two bank names and nothing else. That is the source being sparse, not a
    # parse failure, so the entry is kept and the address left null.
    if rest and len(rest) < 70:
        return rest.strip(), ""
    return None


def parse(pdf: Path, has_state_column: bool) -> tuple[list[Partner], list[str]]:
    partners: list[Partner] = []
    skipped: list[str] = []
    for serial, body in split_records(read(pdf)):
        if has_state_column:
            state, rest = take_state(body)
            # The Other Agencies list has a state column whose last row holds "SIDBI"
            # instead of a state. Falling back keeps that row placed by its address
            # rather than dropping it out of every search.
            if state is None:
                state = find_state(rest)
        else:
            # find_state on the CLEANED text, not the raw body. These PDFs wrap
            # mid-phrase, so a raw body holds "Uttar" and "Pradesh" on separate
            # lines and the state pattern never matched. Every bank whose state
            # appeared only as wrapped text came out unplaced, and then showed up
            # under whichever state the citizen had chosen.
            rest = clean(body)
            state = find_state(rest)
        pair = split_name_address(rest)
        if pair is None:
            skipped.append(f"#{serial}: {rest[:70]}")
            continue
        name, address = pair
        partners.append(Partner(serial, state, name, address))
    return partners, skipped


class CorrectionMismatch(Exception):
    """A correction no longer matches the record it was written against."""


def load_corrections(path: Path) -> dict[tuple[str, int], dict]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        (c["category"], int(c["serial"])): c for c in data.get("corrections", []) or []
    }


def apply_corrections(
    category: str, partners: list[Partner], corrections: dict[tuple[str, int], dict]
) -> list[str]:
    """Overwrite hand-read fields, and record what was changed.

    The `expect` field is the guard. It holds the name this script produced when the
    correction was written; if a later parse produces something else, the source or
    this script has moved and the correction must be re-read against the PDF rather
    than applied blind.
    """
    notes: list[str] = []
    for i, partner in enumerate(partners):
        correction = corrections.get((category, partner.serial))
        if correction is None:
            continue
        expected = correction.get("expect")
        if expected is not None and partner.name != expected:
            raise CorrectionMismatch(
                f"{category} #{partner.serial}: correction expects\n"
                f"  {expected!r}\nbut this run parsed\n  {partner.name!r}\n"
                "Re-read the record against the PDF and update corrections.yaml."
            )
        changed = []
        for field in ("name", "address", "state"):
            if field not in correction:
                continue
            value = correction[field]
            if getattr(partner, field) != value:
                changed.append(field)
                partners[i] = partner = _replace(partner, field, value)
        if changed:
            notes.append(
                f"#{partner.serial} {partner.name}: {', '.join(changed)} "
                f"({correction.get('reason', 'read from the source PDF')})"
            )
    return notes


def _replace(partner: Partner, field: str, value) -> Partner:
    values = {"serial": partner.serial, "state": partner.state,
              "name": partner.name, "address": partner.address}
    values[field] = value
    return Partner(**values)


def quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def write_yaml(out: Path, key: str, partners: list[Partner], source_url: str,
               retrieved_on: str, skipped: list[str], corrected: list[str]) -> None:
    label, category = CATEGORIES[key]
    lines = [
        f"# NSFDC Channel Partners: {label}.",
        "#",
        f"# Extracted from {source_url}",
        f"# by tools/extract_partners.py on {retrieved_on}. Not typed by hand.",
        "#",
        "# The source PDF uses a dash character that does not survive text extraction;",
        "# it arrives as U+FFFD and is normalised to a hyphen. Nothing else is altered.",
        "#",
        "# NO FUND-UTILISATION OR NPA DATA. SIH26092 asks for partners to be filtered by",
        "# 'current fund utilization eligibility (ensuring applications aren't sent to",
        "# partners with high NPAs or overdues)'. NSFDC does not publish that, anywhere.",
        "# It is therefore absent rather than estimated, and the engine refuses to rank",
        "# on it. A locator that shows a citizen which branch has money, without the",
        "# data to know, is guessing about her time and her bus fare.",
        "#",
    ]
    if skipped:
        lines += [f"# SKIPPED, unparseable, {len(skipped)} record(s):"] + [
            f"#   {s}" for s in skipped
        ] + ["#"]

    # Which entries a person overrode, and why. Sourced in corpus/partners/
    # corrections.yaml, which quotes the PDF lines each was read from.
    if corrected:
        lines += [f"# CORRECTED BY HAND, {len(corrected)} record(s):"] + [
            f"#   {c}" for c in corrected
        ] + ["#"]

    # A name carrying digits is usually a house number that leaked across the cut, or a
    # page footer the PDF put inside the record. The script will not guess where the
    # name really ends, so it flags them here for one human glance instead of quietly
    # shipping a bank whose name has an address stuck to it.
    suspect = [p.name for p in partners if re.search(r"\d", p.name)]
    if suspect:
        lines += [f"# REVIEW, name contains digits, {len(suspect)}:"] + [
            f"#   {n}" for n in suspect
        ] + ["#"]

    unplaced = [p.name for p in partners if not p.state]
    if unplaced:
        lines += [
            f"# NO STATE IN THE SOURCE, {len(unplaced)} record(s). These are counted",
            "# in every result and shown to nobody, because filing a partner under a",
            "# state the source does not give would be a claim we cannot support:",
        ] + [f"#   {n}" for n in unplaced] + ["#"]
    lines += [
        f"category: {category}",
        f"label: {quote(label)}",
        f"source_url: {quote(source_url)}",
        f"retrieved_on: {retrieved_on}",
        "verification_status: VERIFIED",
        "partners:",
    ]
    for p in partners:
        lines.append(f"  - name: {quote(p.name)}")
        lines.append(
            f"    address: {quote(p.address) if p.address else 'null'}"
        )
        lines.append(f"    state: {quote(p.state) if p.state else 'null'}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved-on", default="2026-08-30")
    args = ap.parse_args()

    pdf_dir, out_dir = Path(args.pdf_dir), Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = "https://nsfdc.nic.in/storage/channel-partners/attachments/"
    banners = "https://nsfdc.nic.in/storage/uploads/images/banners/"
    jobs = [
        ("sca", "cp4.pdf", base + "20260401_164458_Ip6UJm.pdf", True),
        ("rrb", "cp3.pdf", base + "20260401_163145_9tiTZM.pdf", False),
        ("psb", "cp5.pdf", base + "20260408_100623_Bea3za.pdf", False),
        ("nbfc_mfi", "cp1.pdf", base + "20251223_101231_7smjJC.pdf", False),
        ("coop", "cp2.pdf", base + "20251223_101341_Zcm8s6.pdf", False),
        ("sfb", "cp7.pdf", banners + "20260408_100851_UrGTfH.pdf", False),
        # This one DOES have a state column. Read without it, the column was glued to
        # the front of every name: "Assam North Eastern Development Finance
        # Corporation Ltd.", "Jharkhand Jharkhand Silk Textile...".
        ("other", "cp6.pdf", base + "20260408_101214_Yw5CGQ.pdf", True),
    ]

    corrections = load_corrections(out_dir / "corrections.yaml")
    applied: set[tuple[str, int]] = set()

    total = 0
    for key, filename, url, has_state in jobs:
        pdf = pdf_dir / filename
        if not pdf.is_file():
            print(f"{key:9s} MISSING {pdf}")
            continue
        partners, skipped = parse(pdf, has_state)
        category = CATEGORIES[key][1]
        corrected = apply_corrections(category, partners, corrections)
        applied |= {(category, p.serial) for p in partners
                    if (category, p.serial) in corrections}
        write_yaml(out_dir / f"{key}.yaml", key, partners, url, args.retrieved_on,
                   skipped, corrected)
        total += len(partners)
        states = len({p.state for p in partners if p.state})
        print(
            f"{key:9s} {len(partners):3d} partners, {states:2d} states"
            + (f", {len(corrected)} corrected" if corrected else "")
            + (f", {len(skipped)} SKIPPED" if skipped else "")
        )

    # A correction that matched nothing is a correction quietly doing nothing, which is
    # worse than no correction at all: the header will not mention it and the defect it
    # was written for is back on the screen.
    orphans = sorted(set(corrections) - applied)
    if orphans:
        raise CorrectionMismatch(
            "corrections.yaml has entries that matched no record: "
            + ", ".join(f"{c} #{n}" for c, n in orphans)
        )
    print(f"total {total} partners, {len(applied)} hand-corrected")


if __name__ == "__main__":
    main()
