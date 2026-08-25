# The Guard: refusal architecture

**Status:** design only. You implement in Claude Code on your PC.
**Goal:** the refusal is not a model behaviour we hope for. It is a **deterministic gate**
that sits between the eligibility reasoning and the citizen, and it is testable.

---

## 1. The core principle

> The model does not decide whether to refuse. The Guard decides, and a deterministic
> template renders the decision — no model phrases a verdict.

If refusal is a prompt instruction ("say you don't know if unsure"), it will fail on stage,
and it will fail in the worst possible way: confidently. The Guard must be code, not prose.

The engine's output is never free text. It is a **structured verdict object** that the Guard
validates before any renderer is allowed to show it. A verdict that fails validation cannot
be displayed as an answer. There is no path around this.

---

## 2. The verdict object

Every scheme evaluation produces one of these, and nothing else:

```
Verdict {
  scheme_id
  status            ELIGIBLE | NOT_ELIGIBLE | UNVERIFIABLE | BLOCKED_ON_DOCUMENT
  predicates[]      one entry per rule clause in the scheme
  unlocking_docs[]  documents that would flip UNKNOWN predicates
}

Predicate {
  clause_text       verbatim from the corpus, never paraphrased
  source_url        + retrieved_on
  evaluation        TRUE | FALSE | UNKNOWN
  evidence          { document_id, field, extracted_value } or null
}
```

The whole design collapses to one rule:

**A predicate may only be TRUE or FALSE if `evidence` is non-null and points at a real
extracted value from a real document the citizen supplied. Otherwise it is UNKNOWN.**

The model is never allowed to write `evaluation`. A deterministic evaluator does that by
comparing the extracted profile value against the rule's typed bound. The model's **only job
is to extract structured facts from documents** (one generative call, at the input boundary).
The verdict is turned into sentences by deterministic slot-fill over a fixed, human-translated
template set — the model never phrases a verdict. Nothing the citizen reads is model-written.
(This is why §4's templates are translated properly, not generated live.)

---

## 3. What triggers a refusal

Six triggers. All are checks on the verdict object, all are pure functions, all are unit
testable, and all are tested.

**T1. Unsupported predicate.**
Any predicate with `evaluation = UNKNOWN` and no document in the profile that could ever
supply it. Status becomes `UNVERIFIABLE`.
*Corpus instance:* PM-JAY criterion D3 is keyed to the SECC 2011 database. No document a
citizen carries proves their SECC record. This predicate is permanently UNKNOWN. **This is
our on-stage refusal.**

**T2. Missing but obtainable evidence.**
Predicate is UNKNOWN, but `verifiable_from` names a document the citizen could go get.
Status becomes `BLOCKED_ON_DOCUMENT`, and the doc goes into `unlocking_docs`.
*Corpus instance:* IGNWPS requires BPL status. No BPL entry in the profile means blocked,
not refused. This is the "one caste certificate away from 4 more" beat, and it is a
**different colour on screen** from a refusal. Do not conflate the two.

**T3. No retrieval support.**
The retriever returned nothing above the similarity floor, or the corpus has no scheme
matching the query domain. Status: `UNVERIFIABLE`, reason "outside corpus."
*This is the trigger for out-of-scope questions like "what is my tax liability."*

**T4. Citation integrity failure.**
Output is deterministic slot-fill over a fixed template set, so there is no free-text model
claim to police. The guarantee is two assertions: **(build time)** no template string carries
a factual claim that is not a bound slot; **(runtime)** every slot in the chosen template
resolves to a value carried by a predicate in the verdict, and that value's `clause_text` is
present verbatim. An unbound or orphan slot voids the whole response.
This is the anti-hallucination net, and because it is structural rather than a natural-language
parse, it is cheap and provable — not a model second-guessing the model.

**T5. Stale or amended rule.**
`last_amended` is newer than `retrieved_on`, or `retrieved_on` is older than a configured
window. Status: flagged, answer shown with a visible staleness banner.
*Corpus instance:* none live, and that is correct. Every scheme was read on 2026-08-26,
so no transcription is stale. AVVC's Oct 2024 expansion precedes our reading and
therefore does NOT fire T5: the trigger means "our copy may have drifted", and ours has
not. If a demo needs a live T5, point it at a source that has changed since we read it.
Do not manufacture one.

**T6. Lapsed scheme.** *(added 2026-08-26)*
`today` falls outside the scheme's own `valid_from` / `valid_until` window. Status:
flagged, and the closure LEADS the card, quoting the source sentence that states it.
Filing into a lapsed scheme is refused by the action layer with a 409, not merely hidden
in the UI.

T5 and T6 are independent and easy to confuse. **T5 asks whether our reading of a rule
has gone stale. T6 asks whether the scheme is still open.** A rule transcribed this
morning can belong to a scheme that closed last year, which is exactly what happened.

A lapse is reported BESIDE eligibility and never instead of it, for the same reason
approval is: a citizen can be provably eligible under the published rules of a scheme
that has shut, and collapsing those into NOT_ELIGIBLE would repeat the mistake the
approval split exists to prevent. She keeps the proof, because a successor scheme
normally carries the rules forward.

*Corpus instances, both found by reading official sources rather than by testing:*
Stand-Up India, whose DFS page states the scheme ran "upto 31.03.2025"; and VCF-SC,
whose operational guidelines are titled "(01.04.2021 to 31.03.2026)". Note the second is
NOT the fund closing, since the same document puts the fund's life at 2039. What lapsed
is the period the rules cover, which is why the rendered wording says the sanctioned
period has ended rather than claiming the scheme is gone.

---

## 4. What it says to the citizen

Refusal must never read as failure. It reads as **honesty plus a next step**. Three distinct
voices for three distinct states. Get these translated properly by a human, not by the
model live on stage.

*(The examples below use welfare-reveal phrasings. The primary entrepreneur equivalents swap
the nouns — discretionary bank appraisal instead of SECC 2011, caste certificate instead of
BPL card — but keep the same three moves. `decided_by` supplies the right noun as a slot.)*

**UNVERIFIABLE (T1 / T3):**
> "I cannot confirm this one, and I will not guess.
> This scheme's rule depends on [the SECC 2011 household survey], and nothing you have shown
> me can prove that. **Ask at [the Gram Panchayat / CSC] and quote this rule:** [clause text].
> If they confirm it, come back and I will complete your application."

Note the three moves: refuse, say *why* in terms of the rule, and hand over a concrete
place to go with the exact clause in hand. The citizen leaves better off than they arrived.

**BLOCKED_ON_DOCUMENT (T2):**
> "You are one document away. Bring your **BPL ration card** and this unlocks **2 more
> schemes** worth **Rs X per month**. You can get it from [office]."

**NOT_ELIGIBLE:**
> "Not this one, and here is exactly why: the rule says **70 years and above**. You are 60.
> **You become eligible in 2036.** I will remember."

Never say "you may qualify," "it is possible that," or "generally speaking." Those phrasings
are the disease we are curing. Ban them at the renderer level with a string blocklist if
you have to.

---

## 5. The on-stage refusal script

Do not improvise this. Pick one query, rehearse it fifty times, and make it a fixture in
your test suite so a Sept 1 refactor cannot break it.

### The primary refusal — entrepreneur (use this one)

**Setup:** the marginalized-entrepreneur persona has uploaded her documents. Haqdaar has
already returned her positive scheme matches with proof. The room is warm.

**Presenter says:** "Now watch what happens when we ask it something no document can settle.
Ask it whether the loan will be *approved*."

**Query:** "Will my Stand-Up India loan be approved?" (or the NSFDC sanction question).

**What fires:** T1 on a `rule_type: discretionary` clause. The eligibility predicates resolve
TRUE with proof, but final sanction is `decided_by` the lending bank's credit appraisal —
`verifiable_from: []`, permanently UNKNOWN. Status `UNVERIFIABLE` *on the approval question*,
while the eligibility she *does* have stays shown with proof.

**What the screen shows:**
- The eligibility she qualifies for, each clause cited (the proof she keeps).
- A calm refusal on *approval*: "Final sanction is the bank's appraisal. No document
  determines it, so I will not promise it — here is where to apply and what to carry."

**Presenter line:** "Every other system would have said 'you may get the loan, please apply.'
Ours proved what she's entitled to and refused to fake what only the bank decides. An AI that
guesses on someone's livelihood is not helpful. It is dangerous."

**Why this query is right:** the discretionary line is *structurally* unprovable (the bank
really does decide), so a challenging judge loses on the facts; and it refuses on a scheme
that is **in** the corpus, which is far stronger than refusing an out-of-corpus question.

### The reveal-vertical refusal — welfare (the SECC-2011 beat)

**Setup:** Sunita has uploaded her income certificate and her 7/12 land record. Haqdaar has
already returned her positive matches with proof. The room is warm.

**Presenter says:** "Now watch what happens when we ask it something it cannot prove.
Sunita, ask it about Ayushman Bharat."

**Query (in Marathi):** *"Mala Ayushman Bharat cha labh milel ka?"*
("Will I get the benefit of Ayushman Bharat?")

**What fires:** T1. The engine evaluates PM-JAY. The age and widow predicates resolve, but
D3 requires a SECC 2011 record. `verifiable_from` for that predicate is the SECC database,
which is not a citizen-obtainable document. Permanently UNKNOWN. Status `UNVERIFIABLE`.

**What the screen shows:**
- The scheme card in a **distinct refusal colour**, not red-as-error, something calm.
- The exact D3 clause, quoted verbatim, with the nha.gov.in link visible.
- The refusal line, in Marathi.
- The next step: which office, and the clause printed to carry there.

**Presenter line, immediately after:**
"Every other system in this space would have said 'you may be eligible, please check.'
Ours told her exactly which rule it could not prove and where to go prove it.
A welfare AI that guesses is not a helpful welfare AI. It is a dangerous one."

**Why this specific query is the right one:**
- It is a scheme every judge has heard of, so the refusal lands.
- The reason is *structural and true*, not staged. SECC 2011 really is unlookupable by a
  citizen. If a judge challenges the refusal, you win the challenge on the facts.
- It refuses on a scheme that is **in** the corpus. Refusing an out-of-corpus question is a
  much weaker demo, because it just looks like the corpus is small.

### The backup refusal (if a judge asks for one live)

**Query:** something adjacent but out of domain, e.g. "How much tax do I owe this year?"
**What fires:** T3, no retrieval support.
**Response:** "That is outside what I have rules for. I only answer where I can show you the
official clause. I have welfare scheme rules loaded, not tax law."

Keep this one in your pocket. It is the answer to "what if we ask it something random."

### The trap to avoid

Do not let a judge pick the refusal query cold on an unrehearsed scheme. If invited to,
redirect: "Pick any of these six, and I will show you the proof chain or the refusal for
whichever you choose." Six rehearsed schemes is a confident-looking offer. An open text box
is a coin flip.

---

## 6. Making it deterministic on demo inputs

Three layers of insurance, cheapest first:

1. **Fixture profiles.** Sunita's extracted profile is a checked-in JSON fixture. On demo
   day the document upload runs the real OCR path, but the verdict is computed from typed
   fields. OCR variance is the single most likely thing to break your demo, and it is not
   what you are being judged on.
2. **Temperature 0 and a pinned prompt** for the extraction model. Rendering runs no model
   (deterministic slot-fill), so its output is asserted exactly in tests, not snapshotted for fuzz.
3. **Golden verdict tests.** For each scheme in the corpus plus the two refusal queries, a
   test asserts the exact `status` and the exact set of `predicates`. Red test means no
   deploy. Run these as the last thing you do before walking on stage.

**Rehearse the failure too.** If the model call times out mid-demo, the Guard's correct
behaviour is to refuse, not to hang. Make the timeout path emit an UNVERIFIABLE verdict with
"I could not verify this in time." Then even a network failure on stage looks like the
product working as designed. That is worth building.

---

## 7. What to build first, given you are on Aug 21

The Guard is the smallest high-value thing in the whole project and it gates the pitch.

1. Verdict object + typed predicate evaluator (deterministic, no model). Half a day.
2. T1 and T2 triggers, with `verifiable_from` populated for every scheme. Half a day.
3. Golden tests for Sunita across all six. Half a day.
4. T4 slot-binding check. Half a day now that rendering is deterministic slot-fill: assert
   at build time that no template carries an unbound factual claim, and at runtime that every
   slot resolves from the verdict. It is the one that actually stops hallucination, so do not skip it.
5. T3 and T5. Cheap, do them last.

Everything else in the engine can be mediocre and you still have a demo. If the Guard is
mediocre, you have a chatbot.
