/*
 * UI chrome strings only — labels, headings, buttons.
 *
 * NOTHING ABOUT A VERDICT LIVES HERE. Every sentence a citizen reads about their
 * eligibility comes from the API, which got it from the engine's deterministic
 * slot-fill over the human-translated template set. The UI displays those strings and
 * never composes, summarises, or rewords them.
 *
 * If you find yourself wanting to add a verdict sentence to this file, that sentence
 * belongs in engine/haqdaar/render/templates/<lang>.yaml instead, where T4 can check
 * it. This split is what keeps "it cannot hallucinate" true all the way to the screen.
 *
 * Marathi (mr) lands with the engine's mr.yaml on day 7.
 */

export const LANGUAGES = ['en'];

const en = {
  appName: 'Haqdaar',
  tagline: 'Proof, not answers.',
  choosePersona: 'Whose situation are we checking?',
  chooseHint: 'Demo profiles. Document upload arrives on day 6.',
  check: 'Check entitlements',
  back: 'Choose someone else',
  results: 'What the rules say',
  askAnything: 'Ask about a specific scheme',
  askPlaceholder: 'e.g. Stand-Up India',
  ask: 'Ask',
  clearQuery: 'Show everything',
  proofHeading: 'The rule, quoted',
  sourceLink: 'Open the official source',
  approvalHeading: 'Separate question: approval',
  unlockHeading: 'One document away',
  provisional: 'Provisional corpus',
  stale: 'Check the date',
  offlineStored: 'Showing a stored answer — you are offline.',
  offlineNothing: 'You are offline and nothing is stored for this yet.',
  loading: 'Checking the rules…',
  simulatedAction: 'Apply with this profile',
  simulatedBadge: 'SIMULATED',
  simulatedNote: 'Nothing is submitted anywhere. The reference is generated on this device.',
  acting: 'Filling the form…',
  actionUnavailable: 'No application form is loaded for this scheme yet.',
  statusLabels: {
    ELIGIBLE: 'Eligible',
    NOT_ELIGIBLE: 'Not eligible',
    BLOCKED_ON_DOCUMENT: 'One document away',
    UNVERIFIABLE: 'Cannot verify',
  },
};

const bundles = { en };

export function t(lang = 'en') {
  return bundles[lang] || bundles.en;
}
