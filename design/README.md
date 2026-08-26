# Website layout

Eight artboards covering the web app. Open **`haqdaar-website-layout.html`** in any
browser: it is self-contained, needs no account and no server, and you can pan, zoom and
export PNG/PDF from it. Everything else in this folder is the source it was built from.

| File | Screen |
|---|---|
| `Main.dc.html` | Landing, need-based front door |
| `Intake.dc.html` | Guided intake |
| `Results.dc.html` | Results list, **all five card states on one screen** |
| `Proof.dc.html` | One scheme opened up: proof chain + approval split |
| `Action.dc.html` | The simulated filing |
| `Compare.dc.html` | Compare, desktop |
| `Desktop.dc.html` | Results, desktop |
| `States.dc.html` | Build reference: tokens, states, the rules |
| `canvas.json` | How the artboards are laid out |

## Read this before building

The colours, radii and spacing are **lifted from `web/src/styles.css`**, not proposed.
Every sentence on every card is **real engine output**, not placeholder copy. So the
layout should match what you pull down rather than fight it.

Six rules are on the `States` artboard. The one that matters most:

> **The UI never writes a sentence about a verdict.** Every line arrives from the engine
> in `lines`, `approval_lines`, `banners`, `window_lines`. Render them in that order.

That is not a style preference. The engine runs zero generative calls and the Guard's T4
check proves no card can display a claim that is not bound to a clause. The moment the
frontend composes its own prose about a verdict, that guarantee is gone and nothing
downstream can detect it.

**Build `Results` first.** If the five states are not tellable apart at a glance, the
product reads as a scheme search app, which is the thing it exists not to be.

## Known gaps, so you do not go looking

- **No Marathi or Hindi screens.** We have placeholder strings, not translations. Mocking
  Devanagari nobody has verified would be worse than showing the switcher and stopping.
- **No "best match", no percentage, no ranking anywhere.** Deliberate, and it matches what
  `/api/compare` refuses to return. Do not add one.
- The API surface and every contract is in `../RUNNING.md`, table near the top.
