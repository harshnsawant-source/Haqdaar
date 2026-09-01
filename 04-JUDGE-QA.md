# Judge Q&A

**How to use this:** I ask you these one at a time in chat. You answer out loud, I tell you
whether it survives and how to tighten it. **Do not read the traps first** — that defeats
the exercise. Read only the fact sheet at the bottom, which you must have exact.

**Rehearsal rule: an answer over 30 seconds is a losing answer.** Judges read length as
uncertainty. Claim, one piece of evidence, stop. Then offer the screen.

**Revised 2026-09-01, the night before the round.** Checked line by line against the
deployed build. Five things in the 30 Aug version were no longer true and would have been
said out loud: the scheme count (ten, now **twelve**), the test count (378, now **415**),
"the EMI calculator and the partner locator do not exist" (**both shipped**), the Marathi
review status, and what the screen actually does with a lapsed scheme. Fixed below.

---

## The frame you are answering from

The problem statement is **SIH26092, "AI-Driven Scheme Matching for Marginalized
Entrepreneurs"**, Ministry of Social Justice & Empowerment. So:

- **The entrepreneur corpus is the demo.** NSFDC, Stand-Up India, VCF-SC.
- **Welfare is the reveal**, not the pitch. Sunita comes in at the end as "same engine,
  new corpus", in thirty seconds, to show the thing generalises.
- If you open on the widow, you have answered a different problem statement than the one
  you registered for.

---

## Q1. It says AI-Driven Scheme Matching. Where is the AI?
*The question that decides your round. Everything else is secondary.*

**The answer is in the problem statement itself.** SIH26092 asks for a *"Smart Scheme
Recommender: An **AI/rule-based engine**"*. Rule-based is one of the two options the
ministry named. Quote that clause back and the question is over in one sentence.

**Trap:** apologising, or inventing a model you do not have. Both lose, and both are now
unnecessary. There is no model in this system: `requirements.txt` is FastAPI, pydantic,
PyYAML, Pillow, python-multipart. A judge who checks will find that in ten seconds.

**What must be in your answer:** lead with their own wording, then own the choice as a
decision rather than a gap. Eligibility is decided by
code against a transcribed clause, because a wrong answer here sends a real person to a
government office to be turned away. Then give the sharp version: *a model that is right
95% of the time is a system that lies to one woman in twenty, and she is the one who
cannot afford the bus fare.* The matching is intelligent; it is just not stochastic.

**Then immediately offer the refusal demo.** Do not wait to be asked. The strongest possible
answer to "where is the AI" is showing the machine decline to answer and explain why.

**If they push — "so it is just if-else":** three-valued logic where UNKNOWN propagates, a
typed verdict object, and a Guard with six triggers that can veto a verdict the evaluator
was willing to give. Then the honest close: the contribution is architectural, not
statistical, and it is that dishonesty is structurally unrepresentable rather than
discouraged by a prompt.

---

## Q2. How is this different from myScheme?

**Trap:** listing features. myScheme has features too.

**What must be in your answer:** myScheme tells you a scheme *exists*. It does not prove
your eligibility against the clause, it does not refuse when it cannot verify, and it does
not fill your form. Three things, one breath, then offer the screen.

---

## Q3. Is your corpus real, or did you write those rules yourselves?

**Trap:** "yes it's real" and moving on. Judges have seen invented corpora.

**What must be in your answer:** a number, a source, an offer. **Twelve schemes across
three verticals**, every clause transcribed verbatim, every one carrying a live link on
screen —
nsfdc.nic.in, standupmitra.in, ifciltd.com, pmkisan.gov.in, nha.gov.in, nsap.nic.in,
scholarships.gov.in, sjsa.maharashtra.gov.in. Then let them click one.

**Say the provisional one before they find it.** Eleven are VERIFIED against the source.
Sanjay Gandhi Niradhar Anudan Yojana is marked PROVISIONAL in the corpus and the UI says so
on every clause. Volunteering that is worth more than the scheme is.

---

## Q4. Twelve schemes out of thousands. Isn't this a toy?

**Trap:** promising to scale to thousands. Everyone promises that; nobody is believed.

**What must be in your answer:** invert it. Twelve schemes at clause-level depth surfaced
structure a thousand shallow entries never would — scheme stacking, unverifiable predicates,
rule amendment tracking, and two lapsed schemes we only found because we read the validity
text. Ingestion is the easy part. Semantics is not.

---

## Q5. Show me it being wrong.

**Trap:** "it won't be wrong." Fatal, and invites them to spend the session hunting.

**What must be in your answer:** the distinction between being wrong and being
*confidently* wrong. Our failure mode is refusing something we could have answered, never
asserting something false, because a predicate cannot resolve TRUE without a
document-backed evidence pointer. Name the cost honestly: **we under-claim.** A citizen may
have to fetch a paper we could arguably have inferred.

---

## Q6. A citizen acts on your output, gets rejected at the office, loses a day's wages. Who is accountable?

**Trap:** treating it as a legal question. It is a design question.

**What must be in your answer:** the design consequences. Every output carries the clause
and the office, so she arrives with the rule in hand rather than our opinion. **We produce
applications, not determinations** — the same sentence the UI itself uses: *whether it is
approved is not mine to promise.* The refusal path exists so we never send someone on a
trip we could not justify.

---

## Q7. Your UI has the tricolour and a chakra on it. Is this a government service?

*New. You now wear the national colours, so expect this.*

**Trap:** treating it as hostile. It is a softball if you have already said it.

**What must be in your answer:** point at your own footer, in whichever language is on
screen: not an official Government of India service, not affiliated with any ministry or
department, only the department concerned can approve an application. Then: the State
Emblem appears nowhere in the product, deliberately, because that is restricted to
government bodies under the 2005 Act. Knowing that unprompted reads as seriousness.

---

## Q8. Did you build the agentic layer, or is that a video?

**Trap:** defensiveness, or implying you file to a real portal.

**What must be in your answer:** what is real (extraction, matching, the Guard, form fill,
tracking reference) and what is simulated (submission to a government portal), in that
order, unprompted. Then note you labelled it SIMULATED on the screen yourselves.

**Do not claim live OCR on the deployed site.** There is no tesseract binary on Vercel;
`profile/ocr.py` checks `shutil.which` and reports itself unavailable rather than crashing.
If you want to show OCR, show it locally and say which it is.

---

## Q9. Your income threshold is Rs 21,000 a year. That's nonsense in 2026.

**Trap:** apologising for the government's rule as if it were your bug.

**What must be in your answer:** we quote the rule as written and flag it as stale rather
than silently reinterpreting it. The corpus tracks `last_amended` precisely because rules
move. A system that quietly modernises a statutory threshold commits a different and worse
error — it invents an entitlement the department will refuse.

---

## Q10. Your refusal is impressive, but you chose the query. Let me pick.

**Trap:** accepting an open text box, or refusing outright and looking scripted.

**What must be in your answer:** "Pick any of our twelve and I'll show you the proof chain
or the refusal for that one." Then actually do it. **Which means rehearse all twelve, both
directions.** This question is the entire reason to rehearse.

---

## Q11. You claim it runs offline. Show me. What hardware, what latency?

**Trap:** hand-waving. Historically your weakest answer.

**What must be in your answer:** be exact about what runs local *today* versus what is
architecture. The engine has no model and no network dependency, so "offline" is cheap for
us in a way it is not for an LLM system — say that, it is a genuine advantage. The PWA
service worker caches the shell and stamps cached API answers so a stored verdict can never
be passed off as live.

**If you have not run it on constrained hardware by 2 Sept, do not call offline done.**

---

## Q12. What is your actual contribution? This is RAG plus a form filler.

**Trap:** claiming novel ML. You have none and they will know.

**What must be in your answer:** the novelty is architectural — the refusal is a
deterministic gate on a typed verdict object, not a prompt instruction. Most systems in this
space ask a model to be honest. Ours makes dishonesty unrepresentable, because a predicate
cannot be TRUE without an evidence pointer. Land it: **the contribution is a trust
substrate, and marginalised-entrepreneur schemes are the first corpus running on it.**

---

## Q13. Your problem statement asks for three components. Show me all three.

*Ask yourself this one first every time you rehearse. It is the checklist a judge scores you
against, and you can now answer it completely.*

**What must be in your answer:** name them in the PS's own order and point at each on screen.

1. **Smart Scheme Recommender.** Twelve schemes, matched clause by clause, every verdict
   carrying the clause it came from.
2. **Financial Calculator.** Real numbers off the scheme's own credit terms, not a generic
   EMI formula: 8% to the beneficiary, a 6 month moratorium, quarterly instalments, a term
   the corpus holds. Let them type a principal.
3. **Geo-Spatial Partner Locator.** 91 Channel Partners from 8 published NSFDC lists, across
   31 states and UTs.

**Say the honest boundary on component 3 before they ask.** It matches by **state**, not by
GPS distance. The published lists carry postal addresses and no coordinates, and geocoding
them needs an external service and a key, which would end the claim that this runs with no
keys and no network. That is a trade we made on purpose and can defend; a fake map is not.

---

## Q14. Where did the partner list come from? How do I know you did not just type it?

*New, and worth inviting. It is the strongest provenance story in the project.*

**Trap:** "we got it from the NSFDC website." True, and it sounds exactly like an answer
someone gives when they typed it.

**What must be in your answer:** the chain, in four beats.

- The **eight source PDFs are committed to the repository**, with their SHA-256 checksums in
  a manifest beside them.
- A **script** extracts the YAML from those PDFs. Nobody transcribes a partner by hand.
- A **test re-hashes the PDFs on every run** and fails if a single byte moved. Delete the
  PDFs and the suite goes red.
- Where a PDF genuinely could not be parsed, the fix is a **correction keyed to that record
  with an `expect` guard**: if the underlying text ever stops matching what the correction
  was written against, the extractor halts instead of silently applying it to the wrong row.

Close it: *clone the repo, run one command with the network off, and you get the same corpus
back byte for byte.* Then offer to do exactly that.

---

## Q15. The PS asks you to route around partners with high NPAs. You do not. Why not?

*The one requirement you did not build. Rehearse this until it is thirty seconds and calm,
because handled well it is the best answer in the set.*

**Trap:** promising it for the next phase, or worse, implying the order on screen means
something. Both throw away the entire trust argument in one sentence.

**What must be in your answer:** **NSFDC does not publish NPA or fund-utilisation figures.**
There is no dataset. So there are two options: invent a ranking, or say so. Every partner
response the API returns carries a field that says so, and the screen prints it:

> *These are listed in a fixed order, not a recommended one. NSFDC does not publish which
> partners currently have funds or a clean repayment record, so this cannot tell you which to
> try first.*

Then land it: *the problem statement asked for a ranking, and the honest answer is that the
data to build it is not public. A system whose whole claim is that it will not assert what it
cannot prove does not get to make an exception because the exception was on the requirements
list.* If the figures are ever shared with us, the field is where they go.

**This is the same refusal that runs everywhere else in the product, applied to ourselves.**
Say that. It is the moment the architecture stops being a slide and starts being a position.

---

## The demo beat that wins the room

**Stand-Up India.** Its own guidelines say the scheme runs "upto 31.03.2025". **VCF-SC** runs
"01.04.2021 to 31.03.2026". Both dates are behind us. Nothing in an embedding knows what a
date means, so a similarity-search system recommends both without blinking.

**Describe what is actually on the screen, because the judge is reading it.** The card is
headed by a block that opens *"Stop. The period this scheme was sanctioned for has ended."*,
prints the end date, and quotes the guideline text it came from. The rule check still runs
underneath it, and **the status chip still says ELIGIBLE**, because under the published rules
she may well qualify. What the engine withholds is the action: the file-this button is not
offered on a lapsed scheme, and the card is greyed.

**Do not say "it refuses to recommend it."** The chip on screen says ELIGIBLE, and a judge
who reads it will mark you as overselling. Say this instead: *it stops you at the door,
shows you the date in the department's own words, and will not file for you until someone
confirms a successor scheme exists.* That is both true and stronger, because it is the
distinction between a system that hides a scheme and one that hands you the reason.

Land it in one line: *every scheme-matching demo you will see today would have recommended
these two.*

---

## Fact sheet — have these exact

| | |
|---|---|
| Problem statement | SIH26092, AI-Driven Scheme Matching for Marginalized Entrepreneurs, MoSJ&E |
| Schemes | **12**: entrepreneur 4, welfare 5, student 3 |
| Entrepreneur | NSFDC Term Loan, **NSFDC Micro Finance**, Stand-Up India, Venture Capital Fund for SC |
| Welfare | PM-KISAN, IGNWPS, PM-JAY, Ayushman Vay Vandana Card, SGNAY |
| Student | Pre-Matric SC, Top Class SC, **NSFDC Educational Loan** |
| Verification | **11 VERIFIED, 1 PROVISIONAL** (SGNAY, and only its age range) |
| Lapsed | Stand-Up India (31.03.2025), VCF-SC (31.03.2026) |
| Guard triggers | T1–T6; T6 is the lapsed-scheme catch |
| Channel Partners | **91**, from **8** published NSFDC lists, placed across **31** states and UTs; 2 unplaced and shown as such |
| EMI calculator | `/api/emi`. Real rate, moratorium and repayment term read off the scheme's own credit terms |
| Tests | **415 passing, 1 skipped** |
| Dependencies | FastAPI, pydantic, PyYAML, Pillow, python-multipart. **No model, no API key.** |
| Languages | English, Marathi, Hindi |

**All three products the PS names by ceiling are now in the corpus**: Micro Finance
(Rs 1.40 lakh), Term Loan (Rs 50.00 lakh), Educational Loan. On 30 Aug we held one of the
three. If you rehearsed the old answer, unlearn it.

---

## Questions with no slide, one line each

- **Did a native speaker check the Marathi?** — **Answer whatever is true on the morning.**
  Harsh has said the review is done; `docs/TRANSLATION-REVIEW.md` still says NOT YET
  REVIEWED with six unticked boxes. Settle that before you walk in, because a judge who
  opens the repo will read the file, not you. If it is genuinely reviewed, tick the sheet
  tonight. A Marathi-speaking judge will know inside one sentence either way.
- Privacy for uploaded certificates — nothing is stored; two tests assert it
- Reaching a citizen with no smartphone — the operator at a CSC or Panchayat is the user
- Who pays at scale
- Why a state would trust your corpus over their own portal
- What happens when two schemes conflict — stacking; IGNWPS is topped up by SGNAY, they do
  not add

---

## Never say these two things

1. **"It never hallucinates."** Say "it cannot assert a claim without a source-backed
   predicate, and here is the suite that proves it." Absolutes invite a hunt for the
   counterexample, and there usually is one.
2. **"We'll add that later."** Say "that is deliberately out of scope, and here is why."
   Scope discipline reads as maturity. Vague future promises read as the opposite.

---

## Before you walk in

Read `docs/SIH26092-PS.md` for the official text. Its "Where Haqdaar stands" table is now
out of date in your favour: four rows it lists as missing have since been built. What still
holds:

1. Q1 is solved by the PS itself. It says "AI/rule-based engine" in its own words.
2. **All three loan products it names are now in the corpus.** Micro Finance and the
   Educational Loan Scheme landed after that table was written.
3. **The EMI calculator and the Channel Partner locator both exist.** Do not apologise for
   them. Show them.
4. The one thing the PS asks for that you do **not** have is partner ranking by NPA and
   fund utilisation. That is Q15. It is a strength, not a gap, if you answer it right.
