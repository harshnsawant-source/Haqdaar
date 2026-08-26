# Stitch output

Visual reference only. **Do not build from the code in here.**

## What to put in this folder

- `*.png` — one export per screen (Home, Questions, Results, Scheme Detail,
  Filled Application). These are the shareable reference.
- `*.html` — the exported code, if you took it. Reference for values only.

## Why not build from it

The app is React against a live API, with a service worker and a stylesheet that
already carries the dark-mode tokens and the four status colours. Stitch emits
standalone HTML with its own Tailwind setup. Using it would mean discarding all
of that to gain markup that does not know what a verdict is.

Read the VALUES out and apply them to the components we have. The whole visual
delta is roughly twenty CSS declarations in `web/src/styles.css`:

- the 6px tricolour rule at the top edge (#FF9933 / #ffffff / #138808)
- warm paper page background instead of cool grey
- the low-opacity saffron-to-green page wash, outside the content column only
- Mukta or Hind for Devanagari and Latin together

## THE RULE THAT MATTERS

**Copy comes from `../../COPY-FOR-STITCH.txt`, never from these images.**

Every quoted rule on these screens is verbatim government text with a source URL
and a read-date behind it. The images are correct on the day they were exported
and cannot stay correct: that file is generated from the engine, so when a clause
changes the file changes and the picture silently does not.

Three separate rounds of generation invented rule text before it stuck. Assume
the next person to touch this will too, unless they are reading the file.
