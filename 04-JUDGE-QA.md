# Judge Q&A: the 10 hardest questions

**How to use this:** I will ask you these one at a time in chat. You answer, I tell you
whether it survives a judge and how to tighten it. Do not read my model answers first, that
defeats the exercise. This file is the record of the questions and the traps in each.

Rehearsal rule: **an answer over 30 seconds is a losing answer.** Judges read length as
uncertainty. Lead with the claim, then one piece of evidence, then stop.

---

## Q1. How is this different from myScheme?
*The question you will definitely get. If you fumble this, nothing else matters.*

**Trap:** listing features. myScheme also has features.
**What must be in your answer:** myScheme tells you a scheme exists. It does not prove your
eligibility against the clause, it does not refuse when it cannot verify, and it does not
fill your form. Name all three in one breath, then offer to show the refusal.

---

## Q2. Is your corpus real, or did you write those rules yourselves?

**Trap:** saying "yes it's real" and moving on. Judges have seen fake corpora.
**What must be in your answer:** a number, a source, and an offer. Six schemes, every clause
transcribed verbatim from sjsa.maharashtra.gov.in, pmkisan.gov.in, nha.gov.in and PIB, every
one with a live link on screen. Then open appendix slide A2 and let them click one.

---

## Q3. What happens when it's wrong?

**Trap:** "it won't be wrong." Fatal.
**What must be in your answer:** the distinction between being wrong and being *confidently*
wrong. Our failure mode is refusing something we could have answered, not asserting something
false, because a predicate cannot resolve TRUE without a document-backed evidence pointer.
Name the cost of that trade honestly: we under-claim.

---

## Q4. Did you actually build the agentic layer, or is that a video?

**Trap:** defensiveness, or overclaiming that you file to the real portal.
**What must be in your answer:** what is real (extraction, matching, the Guard, form fill,
tracking reference) and what is simulated (the actual submission to a government portal),
stated in that order, without being asked twice. Then note that you labelled it on the slide
yourselves.

---

## Q5. Your income threshold is Rs 21,000 a year. That's nonsense in 2026. So is your engine
## giving people wrong advice?

**Trap:** apologising for the government's rule as if it were your bug.
**What must be in your answer:** we quote the rule as written and flag it as a stale
threshold rather than silently reinterpreting it. Then point out the corpus tracks
`last_amended` precisely because rules move (PMAY-G exclusions relaxed 2024, Vay Vandana
added Oct 2024). A system that silently modernises a statutory threshold is committing a
different and worse error.

---

## Q6. You claim it runs offline on a cheap device. Show me. What model, what hardware,
## what latency?

**Trap:** hand-waving. This is the claim in your brief most likely to be under-built.
**What must be in your answer:** be precise about what runs local today versus what is
architecture. If retrieval and the Guard run local and only generation needs a model, say
exactly that. **If you have not actually run it on constrained hardware by 2 Sept, do not
claim offline as done.** Downgrade it to slide 10 vision language. This is the question I
expect you to be weakest on right now.

---

## Q7. A citizen acts on your output, gets rejected at the office, and loses a day's wages.
## Who is accountable?

**Trap:** treating it as a legal question. It is an ethics-and-design question.
**What must be in your answer:** the design consequences. Every output carries the clause and
the office, so the citizen arrives with the rule in hand rather than our opinion. We produce
applications, not determinations. The refusal path exists specifically so we never send
someone on a trip we could not justify.

---

## Q8. Six schemes out of thousands. Isn't this a toy?

**Trap:** promising to scale to thousands. Everybody promises that.
**What must be in your answer:** invert it. Six schemes done to clause-level depth surfaced
real structure that a thousand shallow entries never would: scheme stacking (IGNWPS is
topped up by Sanjay Gandhi, they do not add), unverifiable predicates (SECC 2011), and rule
amendment tracking. Ingestion is the easy part. Getting the semantics right is not.

---

## Q9. Your refusal is impressive, but you chose the query. Let me pick one.

**Trap:** accepting an open text box, or refusing outright and looking scripted.
**What must be in your answer:** the redirect from the Guard doc. "Pick any of our six and
I'll show you either the proof chain or the refusal for that one." Then actually do it.
Which means: **rehearse all six, both directions.** This question is why.

---

## Q10. What's your actual contribution here? This is RAG plus a form filler. Where's the
## novelty?

**Trap:** claiming novel ML. You do not have novel ML and a judge will know.
**What must be in your answer:** the novelty is architectural and it is the refusal being a
deterministic gate on a typed verdict object rather than a prompt instruction. Most systems
in this space ask a model to be honest. Ours makes dishonesty structurally unrepresentable,
because a predicate cannot be TRUE without an evidence pointer. Then land the framing: the
contribution is a trust substrate, and welfare is the first corpus running on it.

---

## Questions that are not on this list but may come

Have a one-liner ready for each. Do not build slides.

- Which languages, and did you test the Marathi with a native speaker
- What is your data privacy story for uploaded income certificates and Aadhaar
- How does this reach a citizen who does not own a smartphone
- Who pays for it at scale
- Why should a state government trust your corpus over their own portal
- What happens when two schemes conflict

---

## The two things to never say

1. **"It never hallucinates."** Say "it cannot assert a claim without a source-backed
   predicate, and here is the test suite that proves it." Absolutes invite a judge to spend
   the rest of the session hunting for a counterexample, and they usually find one.
2. **"We'll add that later."** Say "that is deliberately out of scope, and here is why."
   Scope discipline reads as engineering maturity. Vague future promises read as the
   opposite.
