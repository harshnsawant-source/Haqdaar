/*
 * The Haqdaar mark: ह, the first letter of हक़दार.
 *
 * WHY A LETTER AND NOT A SYMBOL
 * -----------------------------
 * The first mark drawn for this product was a tick whose tail ran flat to the right.
 * It was meant to read as a tick joined to a shirorekha. It read as the radical sign,
 * because that is exactly what that shape is. A logo for a welfare-entitlement engine
 * must not look like a square root, so it was replaced.
 *
 * Three freehand attempts at a geometric ह were tried before this one. Every single
 * one rendered as a DIFFERENT letter -- टा, या, and finally ऽ. That is not a near
 * miss: on a product that ships in Hindi and Marathi, a mark that spells the wrong
 * thing is a defect. Hand-drawing a script letterform from memory does not work, and
 * anyone tempted to "clean up" the path below should know that is the ground it sits
 * on.
 *
 * WHERE THE OUTLINE COMES FROM
 * ----------------------------
 * It is the ह of Mukta, the typeface the wordmark is already set in, extracted from
 * the font outline and normalised into a 100 x 100 box. So the monogram is the name's
 * own first letter in the product's own type: correct by construction, and it can
 * never be the wrong letter. Mukta is under the SIL Open Font License, which permits
 * using glyph outlines in a logo.
 *
 * If the path is ever regenerated, the source is the ह glyph (U+0939) of Mukta 800,
 * fitted to a 6-unit margin. Do not nudge the curves by hand.
 *
 * `currentColor` throughout, so one CSS token themes it; see --brand in styles.css,
 * which is deliberately separate from --chakra. See [[Chakra]] for why the national
 * wheel is a different thing with different rules.
 */

// ह (U+0939), Mukta 800, normalised to a 100 x 100 box with a 6-unit margin.
export const MARK_PATH =
  'M61.73 94.00Q54.14 94.00 47.35 92.27Q40.57 90.55 35.45 87.04Q30.33 83.53 27.34 78.30' +
  'Q24.35 73.06 24.35 65.93Q24.35 61.10 26.36 57.42Q28.37 53.74 30.44 52.13Q29.64 51.32 28.60 50.12' +
  'Q27.57 48.91 26.59 47.24Q25.61 45.57 24.98 43.62Q24.35 41.66 24.35 39.24Q24.35 36.02 25.56 33.44' +
  'Q26.76 30.85 28.89 29.01Q31.02 27.17 33.84 26.19Q36.66 25.21 39.99 25.21H53.45V17.96H19.75V6.00' +
  'H80.25V17.96H69.21V37.17H46.20Q43.56 37.17 42.01 38.32Q40.45 39.47 40.45 41.78Q40.45 43.16 41.03 44.36' +
  'Q41.60 45.57 42.18 46.03Q44.36 45.34 46.55 45.00Q48.73 44.65 51.50 44.65Q62.42 44.65 68.87 49.83' +
  'Q75.31 55.00 75.31 64.44Q75.31 68.23 73.70 71.51Q72.09 74.79 70.71 75.94L58.05 70.42' +
  'Q58.97 69.50 59.66 68.00Q60.35 66.51 60.35 64.90Q60.35 61.22 57.94 59.09Q55.52 56.96 50.69 56.96' +
  'Q45.97 56.96 43.21 59.55Q40.45 62.14 40.45 66.51Q40.45 70.19 42.35 72.89Q44.25 75.59 47.53 77.44' +
  'Q50.81 79.28 55.29 80.31Q59.78 81.35 64.95 81.69Z';

export const MARK_VIEWBOX = '0 0 100 100';

/*
 * The mark on its own, for the masthead and the opening screen.
 *
 * Decorative by default: the wordmark beside it already says the name, so a screen
 * reader announcing it twice is noise. Pass `title` only where the mark stands alone
 * with no visible name next to it.
 */
export default function Logo({ className, title }) {
  return (
    <svg
      className={className}
      viewBox={MARK_VIEWBOX}
      role={title ? 'img' : 'presentation'}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : 'true'}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <path d={MARK_PATH} fill="currentColor" />
    </svg>
  );
}

/*
 * The badge: the letter held inside an open tricolour ring.
 *
 * WHERE THIS MAY AND MAY NOT GO
 * -----------------------------
 * The opening screen, the deck, and anywhere the mark is large and alone. NOT the
 * masthead, and NOT the favicon. styles.css states that the national colours appear
 * in exactly two places and never on or near a card, because saffron sits beside
 * --blocked and India green beside --eligible, and those four status colours are the
 * only signal a citizen who cannot read can use. A tricolour badge above a column of
 * verdict cards would compete with exactly that. Use `Logo` or `LogoTile` there.
 *
 * The ring is deliberately OPEN, with a gap at each side, rather than a closed
 * roundel. A closed ring around a mark reads as an official seal, and this product is
 * not a government service; the whole design brief has been to stay clear of that
 * claim. It also carries no chakra and no emblem, for the same reason.
 *
 * The arcs are stroked with CSS classes rather than fill attributes so they take the
 * themed tokens; a `var()` inside an SVG presentation attribute does not resolve.
 */

// Centre 50,50, radius 42. The top arc runs 195deg to 345deg and the bottom 15deg to
// 165deg, leaving a 30deg gap at each side. Endpoints are precomputed rather than
// derived at runtime so the path is readable and cannot drift.
const RING_TOP = 'M9.43 39.13A42 42 0 0 1 90.57 39.13';
const RING_BOTTOM = 'M90.57 60.87A42 42 0 0 1 9.43 60.87';

export function LogoBadge({ className, title }) {
  return (
    <svg
      className={className ? `logo-badge ${className}` : 'logo-badge'}
      viewBox="0 0 100 100"
      role={title ? 'img' : 'presentation'}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : 'true'}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <g fill="none" strokeWidth="6" strokeLinecap="round">
        <path className="badge-arc-saffron" d={RING_TOP} />
        <path className="badge-arc-green" d={RING_BOTTOM} />
      </g>
      {/* Scaled about the centre. The glyph box is already centred on 50,50, so the
          letter needs no offset of its own. */}
      <g transform="translate(50,50) scale(0.58) translate(-50,-50)">
        <path d={MARK_PATH} fill="currentColor" />
      </g>
    </svg>
  );
}

/*
 * The mark knocked out of a solid lozenge, for the favicon and the installed app.
 *
 * A mask rather than a second path painted in the background colour, so the counter
 * inside the bowl stays genuinely transparent and the icon works on any ground.
 */
export function LogoTile({ className, title, maskId = 'haqdaar-tile-knockout' }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      role={title ? 'img' : 'presentation'}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : 'true'}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <mask id={maskId}>
        <rect width="100" height="100" fill="#fff" />
        <g transform="translate(18,18) scale(0.64)">
          <path d={MARK_PATH} fill="#000" />
        </g>
      </mask>
      <rect
        x="2"
        y="2"
        width="96"
        height="96"
        rx="24"
        fill="currentColor"
        mask={`url(#${maskId})`}
      />
    </svg>
  );
}
