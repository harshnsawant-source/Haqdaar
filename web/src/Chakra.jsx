/*
 * The Ashoka Chakra, drawn rather than fetched.
 *
 * Twenty-four spokes, generated. Hand-writing them would be 24 near-identical lines
 * that nobody would ever check, and getting the count wrong is the one mistake an
 * Indian judge notices instantly.
 *
 * WHAT THIS IS NOT
 * ----------------
 * It is NOT the State Emblem of India, the four-lion Sarnath capital. That one is
 * restricted by the State Emblem of India Act 2005 and must not appear on a product
 * that is not a government body, which is why it is absent from every surface here.
 * The chakra is the wheel from the national flag and carries no such restriction.
 *
 * Decorative only: `aria-hidden`, and no pointer events. A screen reader announcing
 * "wheel" between the app name and the tagline would be noise, and the watermark
 * behind the page is not content at all.
 *
 * `currentColor` throughout, so a single CSS token themes it and the two placements
 * (masthead mark, page watermark) can differ in colour without a second copy.
 */

const SPOKES = 24;

// Traditional proportions, in a 0..100 box measured from the centre:
const RIM = 46; // outer circle
const HUB = 5.5; // filled centre
const SPOKE_IN = 8; // spokes start clear of the hub
const SPOKE_OUT = 43.5; // and stop just short of the rim

export default function Chakra({ className }) {
  const spokes = Array.from({ length: SPOKES }, (_, i) => {
    // Start at twelve o'clock so the wheel looks upright rather than rotated by half
    // a spoke, which is visible at the small size.
    const angle = (i * 2 * Math.PI) / SPOKES - Math.PI / 2;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return (
      <line
        key={i}
        x1={50 + SPOKE_IN * cos}
        y1={50 + SPOKE_IN * sin}
        x2={50 + SPOKE_OUT * cos}
        y2={50 + SPOKE_OUT * sin}
      />
    );
  });

  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      aria-hidden="true"
      focusable="false"
      role="presentation"
    >
      <g
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        vectorEffect="non-scaling-stroke"
      >
        <circle cx="50" cy="50" r={RIM} strokeWidth="3" />
        {spokes}
      </g>
      <circle cx="50" cy="50" r={HUB} fill="currentColor" />
    </svg>
  );
}
