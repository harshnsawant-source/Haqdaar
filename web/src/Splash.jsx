/*
 * The opening screen.
 *
 * The mark is written on left to right, the name arrives under it, and the whole panel
 * swipes left to hand over to the engine. That is the entire feature.
 *
 * The reveal is a wipe rather than a stroke being drawn, because the mark is a filled
 * letterform (ह) and not a single line. A left-to-right wipe is also the direction
 * Devanagari is written, so it reads as the letter being put down rather than as a
 * shape sliding in.
 *
 * WHY THE MARK AND NOT THE CHAKRA
 * -------------------------------
 * styles.css says of the chakra: "Deliberately never animated. A spinning national
 * symbol is a novelty, and this sits behind a page where someone is reading whether
 * she qualifies for a pension." That rule holds here. The tricolour rule and the
 * chakra watermark stay exactly as they are; the only thing that moves is the logo,
 * which is ours to move.
 *
 * IT MUST NEVER BE A WALL
 * -----------------------
 * A citizen on a slow phone did not come here for a title card. So:
 *   - any click, tap or key dismisses it at once, and the whole panel is a button;
 *   - it dismisses itself after HOLD_MS regardless;
 *   - `prefers-reduced-motion` collapses it to a short static hold and a fade;
 *   - it is `aria-hidden`, so a screen reader skips it and reads the app underneath
 *     immediately rather than waiting out an animation it cannot see.
 * It is a first-load thing only: it is mounted once, so moving around inside the app
 * never brings it back.
 *
 * The two timings below are the ONLY numbers shared with the stylesheet. The exit is
 * driven by `transitionend` rather than a third timer, so the unmount cannot drift
 * out of step with the CSS.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import Chakra from './Chakra.jsx';
import { LogoBadge } from './Logo.jsx';
import { useLang } from './lang.jsx';

// How long the finished screen sits there before it leaves on its own. Long enough to
// read the name, short enough that nobody reaches for the back button.
const HOLD_MS = 2200;
// Reduced motion gets no draw and no swipe, so it only needs long enough to register
// as a title card rather than a flash.
const HOLD_MS_REDUCED = 900;

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    // No matchMedia (old browser, odd webview): assume motion is fine, since the
    // animation is decorative and the screen dismisses itself either way.
    return false;
  }
}

export default function Splash() {
  const { s, lang } = useLang();
  const [leaving, setLeaving] = useState(false);
  const [done, setDone] = useState(false);
  const reduced = useRef(prefersReducedMotion());

  const dismiss = useCallback(() => setLeaving(true), []);

  // Leave on its own, even if nobody touches anything.
  useEffect(() => {
    const ms = reduced.current ? HOLD_MS_REDUCED : HOLD_MS;
    const timer = window.setTimeout(dismiss, ms);
    return () => window.clearTimeout(timer);
  }, [dismiss]);

  // Any key skips it. Pointer taps are handled by the panel itself, which is a button.
  useEffect(() => {
    window.addEventListener('keydown', dismiss);
    return () => window.removeEventListener('keydown', dismiss);
  }, [dismiss]);

  /*
   * The exit normally ends on `transitionend`, but that event does NOT fire if the tab
   * is backgrounded part-way through, and it never fires at all if a browser refuses
   * the transition. Either way the panel would stay up forever with the page scroll
   * still locked, which is the worst failure this component could have. So the exit
   * also has a deadline: comfortably past the 640ms transition, and past the 220ms
   * reduced-motion fade.
   */
  useEffect(() => {
    if (!leaving) return undefined;
    const timer = window.setTimeout(() => setDone(true), 900);
    return () => window.clearTimeout(timer);
  }, [leaving]);

  /*
   * Hold the page still while the panel is up, so a stray scroll during the animation
   * does not drop someone into the middle of the results.
   *
   * KEYED ON `done`, NOT ON MOUNT. This first shipped with an empty dependency array,
   * on the assumption that returning null unmounts the component. It does not: App
   * renders <Splash /> unconditionally, so this component stays mounted for the life
   * of the page and simply renders nothing once it is finished. The cleanup therefore
   * never ran, `overflow: hidden` stayed on <html>, and THE WHOLE APP COULD NOT BE
   * SCROLLED. Depending on `done` makes the cleanup fire the moment the panel is
   * finished with, which is the thing that actually needs to happen.
   */
  useEffect(() => {
    if (done) return undefined;
    document.documentElement.classList.add('splash-open');
    return () => document.documentElement.classList.remove('splash-open');
  }, [done]);

  /*
   * Unmount when the exit actually finishes rather than after a third timer. Under
   * reduced motion the exit is an opacity fade and there is no transform transition,
   * so both property names count.
   */
  function handleTransitionEnd(event) {
    if (event.target !== event.currentTarget) return;
    if (event.propertyName === 'transform' || event.propertyName === 'opacity') {
      setDone(true);
    }
  }

  if (done) return null;

  return (
    <button
      type="button"
      className={leaving ? 'splash is-leaving' : 'splash'}
      onClick={dismiss}
      onTransitionEnd={handleTransitionEnd}
      /* Decorative in full: everything it says is repeated in the masthead a moment
         later, so a screen reader should go straight to the app rather than announce
         a title card and a skip button it does not need. */
      aria-hidden="true"
      tabIndex={-1}
    >
      {/* Behind everything, filling the screen. The wheel from the flag, not the State
          Emblem, and the same decorative use it already has as the page watermark. */}
      <Chakra className="splash-chakra" />
      <span className="splash-inner">
        <LogoBadge className="splash-mark" />
        {/* Caps and wide letter-spacing are a LATIN treatment only. Devanagari has no
            case, and letter-spacing pulls the shirorekha apart between characters, so
            हक़दार would render as a row of disconnected pieces. English gets the
            spaced-caps wordmark; the other two keep their normal setting. */}
        <span className={lang === 'en' ? 'splash-word is-latin' : 'splash-word'}>
          {s.appName}
        </span>
        <span className="splash-rule" aria-hidden="true" />
        <span className="splash-tag">{s.tagline}</span>
      </span>
    </button>
  );
}
