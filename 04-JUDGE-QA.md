# Judge Q&A

**How to use this:** I ask you these one at a time in chat. You answer out loud, I tell you
whether it survives and how to tighten it. **Do not read the traps first** — that defeats
the exercise. Read only the fact sheet at the bottom, which you must have exact.

**Rehearsal rule: an answer over 30 seconds is a losing answer.** Judges read length as
uncertainty. Claim, one piece of evidence, stop. Then offer the screen.

**Revised 2026-08-30.** Re-pointed from welfare-first to SIH26092, and every scheme count
corrected: this said "six schemes" throughout and it is ten.

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

**What must be in your answer:** a number, a source, an offer. **Ten schemes across three
verticals**, every clause transcribed verbatim, every one carrying a live link on screen —
nsfdc.nic.in, standupmitra.in, ifciltd.com, pmkisan.gov.in, nha.gov.in, nsap.nic.in,
scholarships.gov.in, sjsa.maharashtra.gov.in. Then let them click one.

**Say the provisional one before they find it.** Nine are VERIFIED against the source.
Sanjay Gandhi Niradhar Anudan Yojana is marked PROVISIONAL in the corpus and the UI says so
on every clause. Volunteering that is worth more than the scheme is.

---

## Q4. Ten schemes out of thousands. Isn't this a toy?

**Trap:** promising to scale to thousands. Everyone promises that; nobody is believed.

**What must be in your answer:** invert it. Ten schemes at clause-level depth surfaced
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

**What must be in your answer:** "Pick any of our ten and I'll show you the proof chain or
the refusal for that one." Then actually do it. **Which means rehearse all ten, both
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

## The demo beat that wins the room

**Stand-Up India.** Its own guidelines say the scheme runs "upto 31.03.2025". It is now past
that. The engine reports the scheme as closed instead of cheerfully matching an entrepreneur
to something that no longer exists — which is what a similarity-search system does, because
nothing in an embedding knows what a date means.

**VCF-SC is the second one**, valid to 31.03.2026, also now past.

Land it in one line: *every scheme-matching demo you will see today would have recommended
these two.*

---

## Fact sheet — have these exact

| | |
|---|---|
| Problem statement | SIH26092, AI-Driven Scheme Matching for Marginalized Entrepreneurs, MoSJ&E |
| Schemes | **10**: entrepreneur 3, welfare 5, student 2 |
| Entrepreneur | NSFDC Term Loan, Stand-Up India, Venture Capital Fund for SC |
| Welfare | PM-KISAN, IGNWPS, PM-JAY, Ayushman Vay Vandana Card, SGNAY |
| Student | Pre-Matric SC, Top Class SC |
| Verification | 9 VERIFIED, 1 PROVISIONAL (SGNAY) |
| Lapsed | Stand-Up India (31.03.2025), VCF-SC (31.03.2026) |
| Guard triggers | T1–T6; T6 is the lapsed-scheme catch |
| Tests | 378 passing, 1 skipped |
| Dependencies | FastAPI, pydantic, PyYAML, Pillow, python-multipart. **No model, no API key.** |
| Languages | English, Marathi, Hindi |

---

## Questions with no slide, one line each

- **Did a native speaker check the Marathi?** — *Not yet.* Drafted and under review, and the
  review sheet is in the repo. Do not claim otherwise; a Marathi-speaking judge will know
  inside one sentence.
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

Read `docs/SIH26092-PS.md`. The full text is now known and it changes three things:

1. Q1 is largely solved. The PS says "AI/rule-based engine" in its own words.
2. The PS names three loan products by ceiling and **the corpus holds one of them**.
   Micro Finance (Rs 1.40 lakh) and the Educational Loan Scheme are missing.
3. It asks for an EMI calculator and a geo-spatial Channel Partner locator. Neither
   exists. Expect to be asked, and answer with scope, not with a promise.
