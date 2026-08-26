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
  // The hero line. Says the problem before it says the product, which is why it lands:
  // nobody has ever felt bad about not knowing a scheme's name until it is put like this.
  hero: "You shouldn't need to know the name of a government scheme to benefit from it.",
  tellUs: 'Tell us about your situation',
  tellUsHint:
    'A few questions. Answer what you can — anything you skip simply stays unknown.',
  startIntake: 'Answer a few questions',
  whichDomain: 'What are you looking for?',
  // Per-vertical labels moved to VERTICAL_LABELS in App.jsx on 2026-08-26,
  // keyed by vertical id, so adding a corpus folder does not need a string here.
  showMyEntitlements: 'Show what I am entitled to',
  checking: 'Checking the rules…',
  cancel: 'Back',
  yes: 'Yes',
  no: 'No',
  intakeUnavailable: 'The engine is not reachable right now.',
  notForYou: 'Not for you, and why',
  notForYouHint: 'Open these to see the exact rule that rules each one out.',
  bringThese: 'Bring these papers',
  bringTheseHint:
    'Each one you can show turns a "needs proof" into an entitlement you can act on.',
  youAlreadyHave: 'You said you already have these — upload them now',
  uploadNow: 'Upload',
  orPickDemo: 'Or use a demo profile',
  orPickDemoHint: 'Prepared profiles, for rehearsal and testing.',
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
  verticalHint: 'Same engine. Different folder of rules.',
  stackedWith: 'Paid together',
  stackedNote:
    'These are two parts of one payment, not two separate benefits. The engine groups them so the totals are never counted twice.',
  // Remembered answers. Deliberately says WHERE they are, not just that they exist:
  // "saved" without "on this device" is exactly what makes people assume an account.
  resumeTitle: 'You answered some of this before',
  resumeHint: 'Kept on this device only, never sent anywhere. Last answered',
  resumeGo: 'Carry on from there',
  resumeForget: 'Start fresh instead',
  finishSession: 'Finish and clear',
  finishHint: 'Clears this person’s answers and results from this device before the next visitor.',
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
