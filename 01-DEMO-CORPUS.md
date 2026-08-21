# Haqdaar Demo Corpus v1

**For:** corpus/content lane
**Scope:** 1 state (Maharashtra) + 4 central schemes + 1 optional sixth
**Rule:** depth on a few, not breadth. Every rule below is transcribed from an official
source and carries its link. Anything I could not open from here is marked
**[VERIFY AT SOURCE]** and must NOT go on a slide until someone opens the page.

---

## 0. The citable stat for slide 2

### Verified, use this one

> **Only 21.8% of persons with disabilities in India received any aid or help from
> the Government.** Another 1.8% received aid from non-government organisations.

- **Source:** NSS Report No. 583, *Persons with Disabilities in India*, NSS 76th Round
  (July to December 2018), National Statistical Office, Ministry of Statistics and
  Programme Implementation.
- **Announced via:** Press Information Bureau, Government of India (release dated
  December 2019).
- **Link:** https://www.pib.gov.in/PressReleasePage.aspx?PRID=1593253&reg=48&lang=2
- **Why it works for us:** it is a Government of India survey number, it is about a
  legally entitled group, and it is a *delivery* gap not an awareness opinion poll.
  Nobody can call it soft.
- **How to phrase it on the slide (do not overreach):**
  "India's own national survey found that fewer than 1 in 4 persons with disabilities
  received any government aid at all. NSS 76th Round, 2018."
  Do not say "78% are unaware." The survey measured receipt, not awareness. If a judge
  catches that stretch, the whole deck loses credibility.

### Second candidate, NOT yet verified

NFHS-5 (2019-21, IIPS / Ministry of Health and Family Welfare) reports the share of
households with any usual member covered under a health insurance or financing scheme.
The figure is widely reported as around 41% nationally, but the primary factsheet PDF at
rchiips.org and dhsprogram.com both refused my requests. **[VERIFY AT SOURCE]** before use:
open the NFHS-5 India factsheet directly, find the exact indicator row, and quote the
number and page. Do not cite the secondary news reports.

I did not find a single clean, government-published number for "percentage of eligible
citizens unaware of schemes they qualify for." I believe that number does not exist in a
citable national form. Do not let anyone on the team invent one.

---

## 1. Sanjay Gandhi Niradhar Anudan Yojana (STATE, Maharashtra)

This is the anchor of the demo. It is a state scheme, it is genuinely obscure, and its
eligibility list is long enough that "am I eligible?" is a real question.

- **Administered by:** Social Justice & Special Assistance Department, Government of
  Maharashtra.
- **Official page:** https://sjsa.maharashtra.gov.in/en/scheme/sanjay-gandhi-niradhar-anudan-yojana/
- **Benefit:** Rs 1,500 per month.

**Eligibility rules (official wording, condensed):**

1. Destitute men and women aged **18 to 65 years**.
2. Category must be one of: orphaned children, persons with disability, persons with a
   severe illness (tuberculosis, cancer, AIDS, leprosy, sickle cell disease), **destitute
   widows**, divorced women not receiving alimony, abuse survivors, transgender persons,
   devadasis, unmarried women over 35, wives of prisoners.
3. **Income test:** family annual income must not exceed **Rs 21,000**, OR the applicant's
   name appears on the **BPL list**.

**Documents needed:**
Age proof, residence/domicile proof, income certificate (Tehsildar) or BPL ration card,
and category proof (for a widow, the husband's death certificate). Bank account and
Aadhaar for the transfer.
**[VERIFY AT SOURCE]** the official page did not print a document list. Get the exact list
from the Tehsildar office form or the district collectorate page and transcribe it verbatim.

**Where the form lives:** submitted at the District Collector's Office, Tehsildar's Office,
or Talathi Office. Online portal: **https://sas.mahait.org/**

**RULE AMBIGUITY, FLAG THIS (and it is a gift):**
The Rs 21,000 per year income ceiling is roughly Rs 1,750 per month. That threshold is
almost certainly a legacy figure that has never been indexed. This is exactly the kind of
rule that a human clerk interprets loosely and a naive AI states as hard fact. Haqdaar
should quote the clause, state the number, and say "this threshold is set by the scheme
rules as written; confirm current interpretation with your Tehsildar." That is a refusal-
adjacent behaviour and it is a very good look on stage.

---

## 2. Indira Gandhi National Widow Pension Scheme, IGNWPS (CENTRAL, via NSAP)

The persona scheme. Sunita is a 60 year old widow.

- **Administered by:** National Social Assistance Programme, Ministry of Rural Development,
  delivered through the state.
- **Maharashtra official page:** https://sjsa.maharashtra.gov.in/en/scheme/indira-gandhi-national-widow-pension-scheme/
- **NSAP portal:** https://nsap.nic.in/

**Eligibility rules:**

1. Applicant is a **widow**, all categories.
2. Age **40 to 79 years**.
3. Family is **Below Poverty Line (BPL)**.

**Benefit in Maharashtra:** Rs 1,500 per month total, made up of Rs 300 per month from the
Centre and Rs 1,200 per month topped up by the state through Sanjay Gandhi Niradhar Anudan
Yojana.

**Documents needed:**
Husband's death certificate, age proof, BPL ration card / BPL list entry, residence proof,
bank account, Aadhaar. **[VERIFY AT SOURCE]** the Maharashtra page did not print the list.

**Where the form lives:** Collector's Office, Tehsildar's Office, the Sanjay Gandhi Niradhar
Anudan Yojana branch, or the Talathi Office.

**RULE AMBIGUITY, FLAG THIS:**
The upper age bound is 79. At 80 a widow is supposed to move to a different pension track.
Also note the Centre-plus-state stacking: IGNWPS and SGNAY are not two independent payments,
the state top-up is *how* the Rs 1,500 is reached. If Haqdaar lists both as separate
Rs 1,500 benefits, it is wrong and a judge who knows Maharashtra will catch it. **The engine
must model scheme interaction, not just scheme membership.** Encode this as an explicit
`stacks_with` / `subsumed_by` relation in the corpus schema.

---

## 3. PM-KISAN (CENTRAL)

The cleanest rule set of the five, and the best one for the auto-fill demo because the
exclusion list is crisp and machine-checkable.

- **Administered by:** Ministry of Agriculture and Farmers Welfare.
- **Official FAQ (source of the rules below):** https://pmkisan.gov.in/Documents/RevisedFAQ.pdf
- **Portal:** https://pmkisan.gov.in/
- **Benefit:** Rs 6,000 per year, in three instalments of Rs 2,000.

**Eligibility rule:**
All **landholding farmers' families** which have **cultivable landholding in their names**.

**Exclusion categories (official, verbatim structure):**

1. Institutional landholders.
2. Former or present holders of constitutional posts; ministers; members of legislatures;
   mayors and district panchayat chairpersons.
3. All serving or retired officers and employees of Central or State Government ministries
   and offices, **except** Multi-Tasking Staff, Class IV, and Group D employees.
4. All superannuated or retired pensioners with a monthly pension of **Rs 10,000 or more**
   (same Class IV / Group D exception).
5. Anyone who **paid income tax** in the last assessment year.
6. Practising professionals: doctors, engineers, lawyers, chartered accountants, architects
   registered with professional bodies.

**Data / documents needed:**
Name, age, gender, category (SC/ST), **Aadhaar number**, **bank account number and IFSC**,
mobile number (recommended). Land record is the underlying proof of cultivable holding.

**Where the form lives:**
"New Farmer's Registration" on https://pmkisan.gov.in/, or submitted to the village
**Patwari / Talathi** or designated revenue officer, who forwards it up to the State Nodal
Officer.

**Why this is our auto-fill hero scheme:** the required fields are few, entirely derivable
from a land record plus a bank passbook, and the form is public. This is the A+ demo.

---

## 4. Ayushman Bharat PM-JAY (CENTRAL)

The scheme whose eligibility is *hardest* to self-assess, which is the point.

- **Administered by:** National Health Authority.
- **Official page:** https://nha.gov.in/PM-JAY
- **Benefit:** health cover of **Rs 5 lakh per family per year** for secondary and tertiary
  care hospitalisation.

**Rural eligibility, SECC 2011 deprivation criteria.** A family qualifies if it meets at
least one of (official wording):

- **D1:** "Only one room with kucha walls and kucha roof"
- **D2:** "No adult member between ages 16 to 59"
- **D3:** "Households with no adult male member between ages 16 to 59"
- **D4:** "Disabled member and no able-bodied adult member"
- **D5:** "SC/ST households"
- **D7:** "Landless households deriving a major part of their income from manual casual labour"

**Automatically included:** destitute / living on alms, manual scavenger households,
primitive tribal groups, legally released bonded labour.

**Urban:** eleven occupational categories, including ragpickers, domestic workers,
construction workers, sweepers, home-based workers, transport workers, shop workers,
electricians and mechanics.

**Documents needed:** Aadhaar and ration card for identification against the SECC / state
beneficiary database. There is no "application" in the usual sense, eligibility is looked
up, then a card is generated.

**RULE AMBIGUITY, FLAG THIS, AND IT IS THE BEST ONE IN THE CORPUS:**
Note that **D6 is missing** from the official list. The published criteria run D1 to D5 and
then D7. Also note the whole thing is keyed to **SECC 2011**, a fourteen year old dataset.
A citizen cannot look up their own SECC record. **This means Haqdaar structurally cannot
prove PM-JAY eligibility from documents alone.** That is not a bug in our demo, it is the
single best refusal case we have. See the Guard doc.

---

## 5. Ayushman Vay Vandana Card, 70+ extension (CENTRAL)

Included specifically because it is a **hard age boundary** and a **recent rule change**.
Both are things a static corpus gets wrong and a cited corpus gets right.

- **Administered by:** National Health Authority, under AB PM-JAY.
- **Source:** Press Information Bureau, Government of India.
  https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2222493&reg=3&lang=2
- **Launched:** October 2024.

**Eligibility rule:**
All senior citizens aged **70 years and above**, **"irrespective of their socio-economic
status."** No income test, no SECC test.

**Benefit:** Rs 5 lakh per family per year for secondary and tertiary care hospitalisation.
Intended to cover approximately 6 crore senior citizens across 4.5 crore families.

**Why it earns its place:** Sunita is 60. She is **not** eligible. Haqdaar saying "you are
not eligible for this, here is the exact clause, here is the year you become eligible" is
almost as strong on stage as a positive match. It proves the engine reads rules rather than
pattern-matching keywords like "senior citizen" and "widow."

**[VERIFY AT SOURCE]** how a 70+ person already covered under standard PM-JAY is treated.
The PIB release I read did not say. Do not guess on stage.

---

## 6. PMAY-G / Awaas Plus (CENTRAL) - OPTIONAL SIXTH, only if time allows

I could not open the official SOP PDF (rural.nic.in / akam-samaveshivikaas.nic.in both
blocked my request), so **everything here is [VERIFY AT SOURCE]** and must be confirmed
against `SOP_AwaasPlus2024.pdf` before it goes anywhere near the demo.

Reported revised automatic exclusion criteria, 2024 relaxation:

- **No longer excluding:** ownership of two-wheelers, motorised fishing boats,
  refrigerators, landline phones; and monthly household income up to **Rs 15,000**.
- **Still excluding:** motorised three or four wheelers; mechanised agricultural equipment;
  Kisan Credit Card limit above Rs 50,000; government employment; registered
  non-agricultural business; income tax paying households.

**Why it is tempting:** the 2024 relaxation means a household excluded in 2023 may be
eligible in 2026 and nobody told them. That is the Haqdaar thesis in one scheme.
**Why it is optional:** unverified rules are worse than no rules. Add it only if your corpus
teammate reads the SOP end to end.

---

## 7. How Sunita maps onto this corpus

Persona: 60, widow, small farmer, rural Maharashtra, land in her own name.

| Scheme | Verdict | The proof / the gap |
|---|---|---|
| Sanjay Gandhi Niradhar Anudan Yojana | **Eligible** if income test passes | Age 60 is inside 18-65; "destitute widow" is a listed category. Needs income certificate or BPL entry. |
| IGNWPS | **Eligible** if BPL | Age 60 is inside 40-79; widow. Needs death certificate + BPL proof. Note it stacks with SGNAY, not adds to it. |
| PM-KISAN | **Eligible** | Cultivable land in her name; she hits none of the six exclusions. Auto-fill target. |
| PM-JAY | **CANNOT VERIFY** | Plausibly D3 (no adult male 16-59). But D3 is keyed to SECC 2011, which she cannot produce. This is the refusal. |
| Ayushman Vay Vandana | **Not eligible** | Rule is 70+. She is 60. Engine states the clause and the year she qualifies. |
| PMAY-G | Optional | Only if the SOP is read. |

**The "one document away" beat:** if she lacks the BPL entry, IGNWPS and the SGNAY income
route both unlock from that single artefact. That is a real, defensible instance of the
"one document unlocks N more" claim in the brief, not a manufactured one.

---

## 8. Corpus schema requirements this exercise exposed

Tell the engine lane these are non-negotiable fields, they came out of real rules above:

- `clause_text` verbatim + `source_url` + `retrieved_on` date (rules change, see AVVC 2024)
- `rule_type`: hard numeric bound (age 40-79), enumerated category (widow), external
  dataset lookup (SECC 2011), or income threshold
- `verifiable_from`: which document proves this predicate. If a predicate maps to no
  citizen-obtainable document, the engine **must** refuse rather than infer. PM-JAY D3 is
  the canonical case.
- `stacks_with` / `subsumed_by`: IGNWPS + SGNAY proved we need this
- `last_amended`: PMAY-G 2024 and AVVC Oct 2024 proved we need this
