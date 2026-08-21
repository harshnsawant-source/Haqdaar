# Haqdaar — SIH Project

Local-first, multilingual AI entitlement engine for Indian govt welfare schemes.
Tells a citizen what they qualify for, PROVES it against the official rule, REFUSES
when it can't verify, and ACTS (auto-fills + tracks the application form).
Pitch: "Proof, not answers. It refuses. It acts."

## Deadline
College round: 2 Sept 2026. Build freeze: 30 Aug.

## Scope (locked — do not scope-creep)
- CORE (must be bulletproof): A = Eligibility Engine (proof + refusal),
  A+ = Agentic action layer (fills forms, tracks).
- STRETCH (only if core is solid): legal-rights vertical, same engine + new corpus.
- ROADMAP only (one slide, don't build): disaster response.
- OUT: live portal/payment integration, all schemes, voice/WhatsApp/login/admin.

## Non-negotiable rules
- Grounded RAG only. Every answer carries its source citation. The Guard blocks any
  output that isn't grounded — that refusal behavior IS the product, keep it deterministic.
- Rendering is DETERMINISTIC TEMPLATE SLOT-FILL. The model's ONLY generative job is
  document extraction (docs -> CitizenProfile) at the input boundary. No model ever
  phrases a verdict or writes a sentence the citizen reads. Output sentences come from a
  fixed, human-translated template set filled from the verdict. This makes "it can't
  hallucinate" true by construction (T4 is a slot-binding check, not an NLI check).
- Eligibility is decided by CODE, not by the model and not by vector search. The evaluator
  writes TRUE/FALSE/UNKNOWN; a predicate is TRUE/FALSE only if it has real document evidence.
- NEVER invent statistics, scheme rules, or eligibility criteria. If a rule isn't in
  our corpus, the engine says so. Fabricated govt rules = the demo is a lie.
- Curate a small REAL scheme corpus (1 state + a few central schemes). Depth over breadth.
- We SIMULATE form filing convincingly (labelled SIMULATED on screen); no real govt
  portal integration for the round.
- Multilingual: English + Marathi (matches the Sunita persona / Maharashtra corpus).

## Stack
Claude Code (build), Antigravity CLI, Google AI Studio (model prototyping),
Google Stitch (UI), Google Slides (pitch). Mobile-first web UI. Local/edge models
where possible (the offline story).

## Full spec
- Scope: PROJECT-BRIEF.md §4.
- Architecture (A + A+): docs/superpowers/specs/2026-08-21-haqdaar-core-design.md — the
  authoritative how. Follow its build order (§8) and structural guarantees (§5).
- Guard behaviour: 02-GUARD-DESIGN.md. Corpus + schema: 01-DEMO-CORPUS.md.