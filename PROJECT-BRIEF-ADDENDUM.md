# Brief Addendum — Targeting Official PS SIH26092 (the fused version)

**Date:** 2026-08-21
**Status:** FOR TEAM REVIEW. Read alongside `PROJECT-BRIEF.md`. This does not replace the brief — it re-aims it.
**Reason:** SIH 2026 now ships pre-set problem statements, and the college round expects one. We found a direct match.

---

## 1. The decision in one line

We badge Haqdaar as our answer to **SIH26092 — "AI-Driven Scheme Matching for Marginalized Entrepreneurs"** (Ministry of Social Justice & Empowerment, Software), using a **marginalized-entrepreneur scheme corpus as the primary demo**, and we keep the **welfare / Sunita story as the "same engine, new corpus" reveal**.

We do not need the teacher's permission for a self-chosen topic anymore. We are answering an official PS, and we over-deliver on it.

---

## 2. Why this, honestly

- **SIH26092 is a direct hit.** "Scheme matching for a marginalized population" is Haqdaar's exact core. "Matching" is table stakes; we add **proof + refusal + agentic filing** on top.
- **The field will be crowded.** Many teams will pick 26092 and build a RAG chatbot for schemes. That is precisely the field our three differentiators are built to win.
- **We lose nothing.** The welfare work is not thrown away — it becomes the platform-proof reveal (the strongest emotional beat and our cleanest refusal live there).

Trade-off we are accepting with eyes open: entrepreneur-credit rules are messier than welfare rules (some depend on discretionary bank appraisal). We turn that into a feature — see §5.

---

## 3. What CHANGES (all in the corpus/content lane — NOT the engine)

- **Primary corpus:** welfare-for-a-widow-farmer → **entrepreneurship / credit-subsidy schemes for marginalized groups.** Candidate clean-rule schemes: Stand-Up India (SC/ST-or-woman, greenfield, Rs 10L–1Cr), NSFDC / NSKFDC term loans (income ceiling + caste certificate), Venture Capital Fund for SC, relevant PM-AJAY components. Final set: whichever have the clearest documented eligibility (`01-DEMO-CORPUS.md` selection rules still apply).
- **Primary persona:** Sunita the widow farmer → e.g. an SC woman starting a small enterprise, navigating credit/subsidy schemes she is owed access to.
- **Primary demo domain:** welfare eligibility → entrepreneur scheme matching + application.
- **Pitch framing:** "the poorest never claim what they're owed" → "the marginalized entrepreneur can't navigate the schemes built to fund them" (primary), with the welfare line kept for the reveal.
- **Form for the A+ action beat:** PM-KISAN form → a real application form for one chosen entrepreneur scheme (e.g. Stand-Up India). Still labelled SIMULATED.

---

## 4. What does NOT change (the entire point)

**Zero engine change.** This is the platform bet from `PROJECT-BRIEF.md` §3 and the design doc §3/§5, made real:

- The **engine** — profile extraction, retrieval routing, deterministic evaluator, verdict object.
- The **Guard** and all five triggers (T1–T5), the refusal behaviour, the deterministic-template rendering.
- The **A+ agentic action layer** — form-map → filled PDF → gap list → tracking reference.
- The **architecture, folder structure, data contracts, test strategy, build order** in `docs/superpowers/specs/2026-08-21-haqdaar-core-design.md`.
- The three hooks: **Proof, not answers · It refuses · It acts.**

A vertical is a corpus folder plus a template set. We are swapping the corpus folder. That is the whole change.

---

## 5. The fused demo (this is what wins the room)

1. **Primary act — the entrepreneur.** A marginalized entrepreneur gives their situation / uploads documents. Haqdaar returns the schemes they qualify for, **each with the exact rule as proof**, plus "one document away from N more."
2. **The refusal beat, re-homed.** Ask it whether a loan will be *approved*. It refuses: **"Final approval is the bank's discretionary appraisal. No document you have shown me determines that, so I will not promise it. Here is the eligibility I *can* prove, and where to apply."** The domain's messiness becomes our signature honesty moment.
3. **The action beat.** Pick a scheme → the agent auto-fills the real application form → submitted-and-tracked (SIMULATED).
4. **The reveal — same engine, new corpus.** Flip to the **welfare / Sunita** vertical for 30 seconds. "Same machine. We changed a folder of rules, not a line of engine. This is the trust layer for citizen–government AI — whether you're an entrepreneur seeking capital or a widow seeking her pension." The welfare case carries the emotional gut-punch and the cleanest refusal (SECC-2011), now serving as living proof that Haqdaar is a platform.

Net effect: we fit the official PS, keep the strongest emotional beat, and *demonstrate* the platform claim instead of asserting it — all in one arc.

---

## 6. Verify before we lock (owned outside the engine lane)

- **Read the full SIH26092 description behind SIH Login.** The title is a clear match, but confirm it means matching entrepreneurs to *government schemes* (credit/subsidy), not B2B market matching, and note the exact expected deliverable. Do this first — everything else depends on it.
- **Pick entrepreneur schemes with clean, documented eligibility** so the deterministic evaluator stays clean; keep discretionary steps (bank appraisal, credit assessment) as the *refusal*, never as a computed TRUE.
- **Do not invent any scheme rule or eligibility number** — same rule as the brief. `[VERIFY AT SOURCE]` until a teammate has read the official rule.
- Confirm a real blank application form PDF exists for the chosen A+ scheme (the PM-KISAN dependency, re-pointed).

---

## 7. Impact on timeline

Minimal. The engine build order (design doc §8) is unchanged — day 1 still builds schema + evaluator + verdict with no model. Only the **corpus/content lane re-points its target** from welfare schemes to entrepreneur schemes, and the welfare corpus becomes the reveal vertical instead of the main act. Build freeze stays **30 Aug**.

---

### The one-line ask to the team

*"We're answering official PS SIH26092. We swap the corpus to marginalized-entrepreneur schemes for the main demo, keep Sunita/welfare as the 30-second 'same engine' reveal, and we change nothing in the engine. Same product, official badge, both stories. Are we in?"*
