# Haqdaar pitch deck outline

**Format:** Google Slides, 16:9. **Runtime:** 3 minutes. **Slides:** 11.
**Design rule:** one idea per slide. If a slide needs to be read, it has already failed.
Target under 20 words of visible text per slide. The presenter carries the content, the
slide carries the image.

**Timing budget (rehearse against a timer):**

| Section | Slides | Time |
|---|---|---|
| Hook + problem | 1-3 | 0:35 |
| Live demo | 4-8 | 1:30 |
| Reveal + roadmap + ask | 9-11 | 0:55 |

The demo is half the runtime. Protect it. Every second you spend on architecture is a second
stolen from judges watching bureaucracy get completed.

---

## Slide 1 - Title

**Headline:** Haqdaar
**Sub:** Know what you're owed. Get it.

- Full-bleed photograph of a rural Indian woman, mid-60s, at a government office counter.
  Not a stock smiling farmer. Someone waiting.
- Logo bottom-left, team name bottom-right, tiny.
- No other text.

*Presenter (5s):* "Haqdaar means the rightful claimant. That is the whole idea."

---

## Slide 2 - The problem, as a number

**Headline:** India's own survey found fewer than 1 in 4 got the help they were owed

- The figure **21.8%** set enormous, filling most of the slide.
- Beneath it, small: "Persons with disabilities who received any government aid.
  NSS 76th Round, 2018, Ministry of Statistics and Programme Implementation."
- Nothing else.

*Presenter (12s):* "This is a Government of India survey, not our estimate. India runs
thousands of welfare schemes. The problem was never the schemes. It is that the people
entitled to them never reach them."

**Note for the deck lane:** cite it exactly as written above. Do not round it, do not
rephrase it as "78% are unaware." It measures receipt, not awareness. See the corpus doc.

---

## Slide 3 - Why they don't claim

**Headline:** Four walls between a citizen and their entitlement

- Four icons in a row, one line each, nothing more:
  - **Don't know** it exists
  - **Can't tell** if they qualify
  - **Wrong language**
  - **Paperwork** defeats them
- Consider greying out the first icon and annotating it: "myScheme solved this one."

*Presenter (18s):* "Government already built myScheme to solve the first wall. Three walls
are still standing. Haqdaar is built for those three."

**This slide is your myScheme defence, placed before the judge thinks to ask.** Do not skip it.

---

## Slide 4 - Meet Sunita

**Headline:** Sunita. 60. Widow. Half an acre in Maharashtra.

- One portrait, full height on the left. Three facts on the right, large type.
- Bottom line, in a different weight: "She has never claimed a single thing she is owed."

*Presenter (10s):* Say her name. Do not say "user" or "citizen" once for the next ninety
seconds. Say Sunita.

---

## Slide 5 - She hands over what she already has

**Headline:** No form. Just her papers.

- Photograph or scan of two real documents: an income certificate and a 7/12 land extract.
- An arrow into a clean profile card: name, age, widow, landholding, income.
- Marathi interface visible in the screenshot. This is where multilingual gets *shown*
  rather than claimed.

*Presenter (15s):* "She does not fill a form. She photographs the papers she already has,
in Marathi. Haqdaar reads them."

**Ideally slides 5 to 8 are live product, not screenshots.** If the live demo is risky, run
live and keep these slides as the fallback. Rehearse the switch.

---

## Slide 6 - THE PROOF BEAT

**Headline:** Not "you may qualify." Here is the rule that entitles you.

- One scheme card, magnified. Inside it:
  - Scheme name: Sanjay Gandhi Niradhar Anudan Yojana
  - Verdict: **Eligible**
  - The **verbatim clause** highlighted: destitute widows, age 18 to 65, family income
    under Rs 21,000 or on the BPL list
  - The live source link visible: sjsa.maharashtra.gov.in
- Behind it, blurred, the stack of her other results.

*Presenter (20s):* "Every single result carries the exact official clause that grants it,
linked to the government page it came from. This is the difference between an answer and a
proof."

**This is the most important slide in the deck. Give it room.**

---

## Slide 7 - THE REFUSAL BEAT

**Headline:** And when it can't prove it, it refuses.

- The PM-JAY card in the calm refusal state.
- The D3 clause quoted: "Households with no adult male member between ages 16 to 59."
- The refusal line in Marathi, with English beneath.
- The next step: which office, and the clause to carry there.

*Presenter (25s):* "Watch. Ayushman Bharat's rule depends on a 2011 government survey that
Sunita cannot look up and neither can we. So Haqdaar does not guess. It tells her which rule
it cannot prove, and where to go prove it. A welfare AI that guesses is not helpful.
It is dangerous."

**Pause after this line. This is the slide judges remember.**

---

## Slide 8 - THE ACTION BEAT

**Headline:** It doesn't advise her. It applies.

- Split screen. Left: her profile. Right: the PM-KISAN form filling itself, field by field.
- Below, the payoff strip: **Application ready. Tracking reference generated.**
- Small honest label somewhere on the slide: "Filing simulated. Portal integration is
  post-hackathon."

*Presenter (25s):* "One click. It fills the actual PM-KISAN form from her documents and
produces a ready-to-submit application with a tracking number. Nine months of not knowing
where to start, done in eleven seconds."

**Put the "simulated" label on the slide yourselves.** A judge who spots it uncredited
thinks you hid it. A judge who reads it from your own slide thinks you are rigorous. This
costs you nothing and buys the whole Q&A.

---

## Slide 9 - THE REVEAL

**Headline:** Same engine. New rules.

- Left: the welfare corpus and the Haqdaar result screen.
- A single arrow.
- Right: the legal-rights corpus and the same UI returning a cited legal answer.
- Under it, one line: "A vertical is a corpus plus a form set."

*Presenter (20s):* "We swapped the corpus. Same engine, same proof, same refusal, entirely
new domain of government. This is not a scheme app."

**Cut this slide entirely if the legal vertical is not demo-ready.** A half-working reveal
is worse than no reveal. The deck must survive its removal, so slide 10 must not depend on it.

---

## Slide 10 - What we're actually building

**Headline:** The trust layer for citizen-government AI

- Simple horizontal three-step, no boxes-and-arrows architecture diagram:
  **Welfare** (built) → **Legal rights** (built / next) → **Disaster response** (next)
- One line beneath disaster response: "Offline, when the network is down."
- Tiny footer, the three-word pitch: **Proof. Refusal. Action.**

*Presenter (20s):* "Every corner of governance needs the same thing: an AI that proves what
it says and refuses when it can't. We built that substrate. Welfare is just the first corpus.
It runs local-first, so it works at a Panchayat with no internet, which is exactly where the
un-served citizens are."

**The offline claim belongs here, not earlier.** It is a capability, not a feature demo, and
this is where it reads as vision rather than a claim you have to prove.

---

## Slide 11 - Close

**Headline:** Proof, not answers. It refuses. It acts.

- The three phrases, stacked, huge, nothing else.
- Team names and the QR to the demo in 8pt at the bottom.

*Presenter (8s):* Say the three lines. Stop talking. Do not add "thank you for your time"
or "any questions." Land it and stand still.

---

## Appendix slides (after slide 11, not presented, for Q&A only)

Build these. They are how you answer a hard question in ten seconds instead of ninety.

- **A1.** Architecture: the five agents and the Guard gate.
- **A2.** The corpus, all six schemes with source links on screen. Answers "is it real."
- **A3.** The Guard's five refusal triggers, and the golden test suite going green.
- **A4.** What we did not build, stated plainly: live portal filing, all schemes, voice,
  accounts. Owning your scope is a strength when *you* raise it.
- **A5.** The IGNWPS + Sanjay Gandhi stacking rule. Proof you understand the domain deeply
  enough to model scheme interaction, not just scheme lookup. This slide impresses anyone
  who actually knows welfare administration.

---

## Deck lane checklist

- [ ] Zero em-dashes anywhere in the deck
- [ ] Zero screenshots with lorem ipsum or placeholder names
- [ ] The stat on slide 2 cited exactly as in the corpus doc
- [ ] The "simulated" label present on slide 8
- [ ] Marathi visible in at least two demo screenshots
- [ ] Deck rehearsed once with slide 9 removed, to prove it survives
- [ ] Total visible word count under 200 across all 11 slides
