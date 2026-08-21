# SIH Project Brief — Team Alignment Doc
### Working name: **Haqdaar** ("the rightful claimant") · alt: *Adhikaar* ("rights")
### Tagline: **Know what you're owed. Get it.**
### Status: FOR TEAM REVIEW — read this, poke holes, then we lock and build. Deadline: **2 Sept** (college round).

> This is the decision doc, not the final spec. If you disagree with the scope, say so *now* — changing
> our minds costs nothing today and costs days next week.

---

## 1. In one sentence

**A local-first, multilingual AI that doesn't just *tell* a citizen which government benefits they qualify
for — it *proves* each one against the official rule, refuses to guess when it can't verify, and then
*acts*: auto-fills the actual application forms and tracks them to completion.**

Not a chatbot. An **entitlement engine**.

---

## 2. The problem (why judges will care)

India runs **thousands** of central + state welfare schemes. A large share of eligible citizens — the poor,
rural, elderly, less-literate — **never claim what they're legally owed**, because:
- they don't *know* the scheme exists,
- they can't tell if they're *eligible* (rules are dense and cross-referenced),
- it's in the wrong *language*,
- and the *paperwork* defeats them.

> **[TEAM TODO: source one hard, citable stat here** — e.g. unclaimed-benefit / scheme-awareness numbers
> from a govt or credible report. A real number in slide 2 is worth a lot. Do NOT invent one.]

The government already knows this — that's why `myScheme` exists. So our pitch is **not** "a scheme finder."
It's the thing myScheme *can't* do (see §4).

---

## 3. Why WE win this (our unfair advantage)

Most teams will build "an AI chatbot for schemes." We can build something they structurally cannot, because
of what we already know how to do:

| Our capability | Why it's rare | Why it matters here |
|---|---|---|
| **Grounded RAG that REFUSES** instead of hallucinating | Most student RAG bots confidently make things up | A welfare bot that gives a poor person *wrong* advice is dangerous. Ours says "I can't verify this." That's the trust story judges remember. |
| **Proof, not answers** — every claim cite-linked to the official clause | Nobody bothers | We don't say "you may qualify." We show *the exact rule that entitles you*. |
| **Local-first / offline** | Hard to do | Runs on a cheap device at a Panchayat / CSC with no internet — where the un-served citizens actually are. |
| **Multi-agent orchestration** (it *acts*) | Very rare at student level | It doesn't stop at advice — it fills and files the forms. |

---

## 4. What we're building — SCOPE (the important part)

### ✅ CORE — MUST be done and bulletproof by 2 Sept (this is the demo)

**A — The Eligibility Engine**
- Citizen gives their situation — by answering a few questions **or by uploading documents they already
  have** (income certificate, land record, ration/Aadhaar). The engine extracts a profile.
- Matches the profile against a curated welfare-scheme knowledge base.
- Returns a ranked result: **"You are eligible for these N. Likely eligible for these M. You are ONE
  document away from unlocking K more."**
- **Every recommendation shows the exact official clause** that grants it (the "proof").
- **Refuses / flags** anything it can't verify — shown live on stage.
- Works in **English + at least one Indian language** (Hindi and/or Marathi).

**A⁺ — The Agentic Action Layer** (this is what makes us *win*, not place)
- For a chosen eligible scheme, the agent **auto-fills the application form** from the citizen's profile.
- Tells them the exact missing document and how to get it.
- Produces a ready-to-submit / submitted application and a **tracking reference**.
- The demo moment: judges watch bureaucracy get *completed* on screen, not just discussed.

### 🟡 STRETCH — only if CORE is rock-solid first (do NOT start this until A/A⁺ is demo-ready)

**E — Legal-rights vertical (proof of generality).** Swap the welfare corpus for a legal-rights corpus on
the *same* engine → a 30–60s "look, same machine, new domain" moment. Cheap for us (we've built grounded
legal RAG before). **Its only job is to prove Haqdaar is a platform, not a one-off.** If A/A⁺ isn't
perfect, we cut E without hesitation.

### 🔮 ROADMAP ONLY — one slide, we do NOT build it now

**D — Disaster response.** The same offline engine, when the internet is dead (floods/quakes), coordinating
relief. Powerful vision, but coordination logic looks fake if under-built. It's our "where this goes"
slide — nothing more.

### ❌ Explicitly OUT (say no now, save days later)
- Real integration with live government portals / payment systems (we simulate the filing convincingly).
- Covering all thousands of schemes (we curate a **credible demo set** — see §10).
- Voice assistant, WhatsApp bot, accounts/login, admin dashboards — none of it for the round.

---

## 5. The three things that make it "crazy good" (memorize these — they're the pitch)

1. **Proof, not answers.** We quote the rule that entitles you. Cite-linked.
2. **It refuses.** Ask it something it can't verify → it says so, live. In a field of hallucinating gov
   bots, honesty *is* the wow.
3. **It acts.** It doesn't advise you about your pension — it *gets* it for you.

---

## 6. The demo script (the 3 minutes that win the room)

1. **The person, not the tech.** "Meet Sunita — 60, widow, small farmer in Maharashtra. She's legally owed
   benefits she's never claimed." (Real persona, relatable.)
2. She uploads her income certificate + land record (or answers 4 questions), **in Marathi**.
3. Haqdaar returns: **6 schemes she qualifies for, each with the exact rule shown as proof**, 3 "likely,"
   and **"one caste certificate away from 4 more."**
4. **The refusal beat:** we deliberately ask it something outside what the documents support → it *refuses*
   and tells her where to verify. (Judges lean in here.)
5. **The action beat:** pick one scheme → the agent **auto-fills the form** from her profile → out comes a
   submitted application + tracking number.
6. **The reveal:** "Same engine, different rules —" flip to the **legal-rights** vertical for 30s (if E is
   in). "This isn't a scheme app. It's the trust layer for citizen–government AI. Next: disaster response,
   offline, when the network is down."

---

## 7. Architecture (high level — so everyone knows their lane)

```
          ┌─────────────────────────────────────────────────────┐
          │                   HAQDAAR ENGINE                     │
          │  (local-first, multilingual, grounded + refusing)    │
          │                                                      │
 Citizen  │  1. Profile Agent   — extract facts from docs/Q&A    │
 input →  │  2. Retrieval + RAG — official corpus, cited chunks  │
 (docs /  │  3. Eligibility Agent — match rules → proof / refuse │
  voice / │  4. Action Agent    — fill forms, list gaps, track   │
  text)   │  5. Refusal/Guard   — no claim without a source      │
          └─────────────────────────────────────────────────────┘
                    │                         │
             Welfare corpus            Legal corpus (STRETCH)
        (scheme rules + forms)        (rights + sections)
```

- **The engine is domain-agnostic.** A vertical = a corpus + a form/action set. That's the whole platform bet.
- Every answer carries its **source citation**; the **Guard** blocks any output that isn't grounded → that's
  the refusal behavior.

---

## 8. Tech stack & tooling

- **AI build:** Claude Code + Antigravity CLI (agents/backend), Google AI Studio (model prototyping).
- **UI/design:** Google Stitch (fast, clean citizen-facing UI), then implemented in web (mobile-first).
- **Core:** grounded RAG (retrieval + citation + refusal), multi-agent orchestration, document parsing/OCR,
  local/edge-capable models where possible (the offline story).
- **Multilingual:** English + Hindi/Marathi.
- **Pitch:** Google Slides.
- *(Exact frameworks we finalize when we lock — kept flexible on purpose.)*

---

## 9. Timeline (19 Aug → 2 Sept)

| Dates | Focus | Owner(s) |
|---|---|---|
| **Aug 19–22** | Engine core: retrieval + citation + **refusal**; welfare corpus loaded; profile extraction | |
| **Aug 23–26** | A⁺ agentic layer: eligibility-with-proof, "one doc unlocks N," form auto-fill + tracking | |
| **Aug 27–29** | Polish UI (Stitch), multilingual, harden the refusal demo; **E only if core is solid** | |
| **Aug 30–Sept 2** | **BUILD FREEZE.** Deck, demo script, rehearse, prep judge Q&A | everyone |

**Non-negotiable rule:** no new features after Aug 30. SIH is won on stage; polish + rehearsal beats one
more half-working feature.

---

## 10. What we need from the team (roles — fill in names)

- **Engine / agents (lead: Harsh)** — RAG, refusal, multi-agent action layer.
- **Frontend / UX** — Stitch → working mobile-first app; the demo flow must feel effortless.
- **Corpus & content** — curate a **credible demo set of schemes** (pick ~1 state + a few high-impact
  central schemes), get their real eligibility rules + forms, build the personas. *This is critical and
  non-glamorous — a thin/fake corpus sinks the demo.*
- **Pitch & deck** — the story, the slides, the stat in §2, the roadmap slide.
- **Demo driver + Q&A** — who presents, who answers the hard judge questions.

---

## 11. Risks & how we de-risk

| Risk | De-risk |
|---|---|
| "This is just myScheme." | Lead with **proof + refusal + it acts** — the three things myScheme doesn't do. Never call it a finder. |
| Thin/fake corpus looks like a toy | Curate a *real* focused scheme set with actual rules + forms (§10). Depth on few > breadth on many. |
| Scope creep kills the demo | E is stretch, D is a slide, portal integration is OUT. Build freeze Aug 30. |
| Refusal/hallucination fails live | Rehearse the exact refusal query; the Guard must be deterministic on demo inputs. |
| Presentation weak | 4 days reserved purely for deck + rehearsal. |

---

## 12. Why it "goes all the way" (the SIH arc)

Whatever we build now carries through the rounds. Haqdaar is designed for that:
- **College round (2 Sept):** welfare engine + agentic action, proven and polished. (+ legal vertical if ready.)
- **Nationals:** add the legal vertical fully / a real second state's schemes / the disaster vertical.
- **The story:** we're not shipping an app, we're shipping **the trustworthy civic-AI substrate for Bharat** —
  and every round we plug in one more corner of governance.

---

## 13. Open decisions for the team (bring answers to the sync)

1. **Name:** Haqdaar? Adhikaar? something else?
2. **Language:** Hindi, Marathi, or both for the demo?
3. **Demo scope:** which state + which schemes are our credible set?
4. **E in or out** as a target (we can decide later, but flag appetite now).
5. **Roles:** who owns each lane in §10?

---

### The one-line ask to the team
*"We build ONE thing insanely well — an AI that proves what you're owed, refuses to lie, and gets it for
you — and we frame it as the platform for all of citizen–government AI. Everything else is a distraction
until 2 Sept. Are we in?"*
