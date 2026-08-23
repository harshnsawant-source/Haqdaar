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
  chooseHint: 'Pick a demo profile, or upload a document once you have chosen one.',
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
  verticalEntrepreneur: 'Entrepreneur schemes',
  verticalWelfare: 'Welfare schemes',
  verticalHint: 'Same engine. Different folder of rules.',
  stackedWith: 'Paid together',
  stackedNote:
    'These are two parts of one payment, not two separate benefits. The engine groups them so the totals are never counted twice.',
  finishSession: 'Finish and clear',
  finishHint: 'Clears this person’s results from this device before the next visitor.',
  purged: 'Cleared. Nothing from that session is left on this device.',
  uploadHeading: 'Upload a document',
  documentType: 'Which document is this?',
  chooseFile: 'Choose an image',
  modeHeading: 'How should unreadable fields be handled?',
  modeLive: 'Live only — leave unreadable fields unknown',
  modeFixtureBacked: 'Fall back to the demo profile (each borrowed value is labelled)',
  readDocument: 'Read this document',
  reading: 'Reading…',
  field: 'Field',
  value: 'Value',
  confidence: 'Where from',
  originRead: 'Read',
  originFixture: 'Demo profile',
  couldNotRead: 'Could not read from this document:',
  ocrUnavailable:
    'No OCR engine is installed on this device, so nothing could be read from the image.',
  fixtureBacked:
    'Some values below come from the checked-in demo profile, not from your document. Each one is labelled.',
  extractUnavailable: 'The reader is not reachable right now.',
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
