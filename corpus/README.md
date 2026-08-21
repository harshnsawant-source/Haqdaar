# Corpus

Data, not code. The engine is corpus-agnostic by design: a vertical is a folder of
scheme YAML plus a template set. Swapping the entrepreneur corpus for the welfare
corpus — the "same engine, new rules" reveal — must require **zero engine change**.

```
schemes/    one YAML per scheme, validated by engine/haqdaar/corpus/schema.py
personas/   checked-in fixture profiles (typed facts + provenance)
forms/      blank application PDFs + field maps (day 5)
```

---

## PROVISIONAL vs VERIFIED

Every scheme and every clause carries `verification_status` and `verify_note`.

- **`VERIFIED`** — a human has opened the official source and transcribed the rule
  verbatim. Only these may appear in a demo or on a slide.
- **`PROVISIONAL`** — placeholder. `clause_text` **must** contain the literal marker
  `[VERIFY AT SOURCE]`; the schema rejects the file otherwise.

`load_corpus(dir, strict=True)` returns VERIFIED schemes only. As of 2026-08-21 that
is an empty list, and `tests/unit/test_corpus_loader.py` asserts it. The assertion is
a tripwire, not decoration: it changes the day the content lane lands a real rule.

### Promoting a scheme to VERIFIED

1. Open the official source. Not a news article, not a summary, not an LLM.
2. Replace each `clause_text` with the verbatim official wording, marker removed.
3. Set `source_url` to the exact page, and `retrieved_on` to the date you opened it.
4. Set `last_amended` if the source states one (drives the T5 staleness banner).
5. Fill `verifiable_from` with the documents that actually evidence the clause.
6. Flip `verification_status` to `VERIFIED` on the clause and, once every clause is
   done, on the scheme.
7. Run `pytest engine/tests` — golden tests will fail because clause text changed.
   Read every diff before updating them. That failure is the system working.

### If you cannot source a figure, leave the clause out

Do not guess and do not "approximate." An absent clause makes the engine under-claim,
which is our accepted failure mode (judge Q&A Q3). An invented clause makes the demo a
lie. `nsfdc-term-loan.yaml` deliberately has **no income-ceiling clause** for exactly
this reason — the addendum says a ceiling exists but names no figure.

---

## Day 1 state

Two PROVISIONAL schemes exist purely to make the evaluator and the first golden tests
runnable. Neither is demo-usable.

| Scheme | Verdict for `entrepreneur-01` | What it exercises |
|---|---|---|
| `stand-up-india` | ELIGIBLE | ANY-group, enumerated category, numeric bound, full proof chain with evidence |
| `nsfdc-term-loan` | UNVERIFIABLE | the discretionary refusal — no document can ever settle it |

`income_threshold`, `exclusion` and `external_dataset` rule types are covered by
synthetic fixtures in `engine/tests/unit/test_evaluator_logic.py` rather than by
inventing corpus clauses to exercise them.

---

## Open decision: approval is not eligibility

Recorded 2026-08-21, to be resolved before the real entrepreneur corpus is written.

On day 1, `nsfdc-term-loan` resolves UNVERIFIABLE because its discretionary sanction
clause sits inside the eligibility ALL group. That is correct for the mechanism test
and **wrong for the real corpus**.

If discretionary clauses are buried inside eligibility groups, a genuinely eligible
entrepreneur renders UNVERIFIABLE and the eligibility we could have proven is hidden
behind a caveat about the bank. That is the opposite of the product: we would be
refusing the part we can prove.

**Rule for the real corpus:** keep eligibility determinable. A discretionary step
(bank appraisal, credit assessment, officer's discretion) is surfaced as a separate
caveat or refusal *alongside* a resolved eligibility verdict, never as a poison pill
inside it. The likely implementation is a group-level kind (`ELIGIBILITY` vs
`APPROVAL`) evaluated separately, but that design decision is open. See the module
docstring in `engine/haqdaar/eligibility/evaluate.py`.

---

## Repo location

This repo currently lives inside OneDrive. `.gitignore` keeps `.venv/`,
`__pycache__/` and `.pytest_cache/` out of sync, which removes the worst of the churn,
but OneDrive can still lock files mid-write and corrupt `.git/` objects.

**Ideally move the repo outside OneDrive** (e.g. `C:\dev\haqdaar`) before the crunch
week. Losing git history on 29 August is a failure mode with no recovery.
