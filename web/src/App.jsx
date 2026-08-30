import { useCallback, useEffect, useState } from 'react';

import { Card } from './Card.jsx';
import Chakra from './Chakra.jsx';
import Logo from './Logo.jsx';
import { Intake } from './Intake.jsx';
import Splash from './Splash.jsx';
import { Upload } from './Upload.jsx';
import { fetchEvaluation, fetchNeeds, fetchPersonas, purgeSession, understandText } from './api.js';
import { forget, recall, remember, savedAtLabel } from './remember.js';
import { LanguageProvider, useLang } from './lang.jsx';
import { LANGUAGES, LANGUAGE_NAMES } from './strings.js';


/*
 * Verticals are data, not code, in the engine. They are data here too: this file lists
 * which verticals EXIST and the order they appear in, never what they are called. The
 * set comes from the API, so a fourth corpus folder needs no change to this component.
 *
 * The NAMES live in strings.js, once per language. They were English constants in this
 * file until 2026-08-30, which meant the three front-door buttons and every demo
 * profile label stayed in English on a Marathi or Hindi page: the one part of the
 * screen a citizen reads first, in the one language she does not.
 *
 * ORDER is a pitch decision. Entrepreneur leads because it is the problem statement we
 * answer; the others follow as the "same engine, new corpus" reveal.
 */
const VERTICAL_ORDER = ['entrepreneur', 'welfare', 'student'];

function verticalsOf(personas) {
  const present = [...new Set(personas.map((p) => p.vertical))];
  const known = VERTICAL_ORDER.filter((v) => present.includes(v));
  // Anything the API serves that this file has not been told about still appears,
  // rather than silently vanishing from the UI.
  return [...known, ...present.filter((v) => !VERTICAL_ORDER.includes(v)).sort()];
}

function labelFor(vertical, s) {
  // A vertical the API serves that no language file names still renders, under its own
  // id, rather than vanishing from the front door.
  return (
    s.verticals?.[vertical] || {
      group: vertical,
      door: vertical,
    }
  );
}

/*
 * Order results by what the citizen can do with them: entitlements she has, then
 * papers that would unlock one, then things nobody can settle. NOT_ELIGIBLE is split
 * out and collapsed — shown, but not first.
 *
 * Ordering only. Nothing here filters a card away.
 */
const ACTIONABLE_ORDER = ['ELIGIBLE', 'BLOCKED_ON_DOCUMENT', 'UNVERIFIABLE'];

function orderCards(cards) {
  const all = cards || [];
  const actionable = all
    .filter((c) => c.status !== 'NOT_ELIGIBLE')
    .slice()
    .sort(
      (a, b) => ACTIONABLE_ORDER.indexOf(a.status) - ACTIONABLE_ORDER.indexOf(b.status),
    );
  return { actionable, ruledOut: all.filter((c) => c.status === 'NOT_ELIGIBLE') };
}

function AppInner() {
  const { lang, setLang, s } = useLang();
  const [personas, setPersonas] = useState([]);
  const [needs, setNeeds] = useState([]);
  const [selected, setSelected] = useState(null);
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [offline, setOffline] = useState(null);
  const [purged, setPurged] = useState(false);
  const [intakeVertical, setIntakeVertical] = useState(null);
  // What a chosen need already told us. Seeds the form so the machine does not
  // immediately ask her something she has just said.
  const [seed, setSeed] = useState(null);
  // Free-text reading. `reading` holds what her sentence was understood to say,
  // shown back to her BEFORE the form opens, because a pre-filled answer she
  // never saw arrive is indistinguishable from a guess.
  const [draft, setDraft] = useState('');
  const [reading, setReading] = useState(null);
  const [readingBusy, setReadingBusy] = useState(false);
  // Read once. `recall` is defensive — a private window throws on access and a
  // half-written record is treated as absent — so this is always either a usable
  // session or null, never a partial one.
  const [saved, setSaved] = useState(() => recall());

  /*
   * Theme. Three states: null follows the operating system, 'light' and 'dark' are
   * explicit and override it. The explicit case matters more than it sounds: a laptop
   * set to dark could not show the warm paper look at all, which is the one you would
   * want on a projector.
   *
   * Kept in localStorage rather than in the profile store, because it is a preference
   * about this device and not a fact about the person, so `forget()` must not clear it.
   */
  const [theme, setTheme] = useState(() => {
    try {
      return window.localStorage.getItem('haqdaar.theme');
    } catch {
      return null;
    }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.setAttribute('data-theme', theme);
    else root.removeAttribute('data-theme');
    try {
      if (theme) window.localStorage.setItem('haqdaar.theme', theme);
      else window.localStorage.removeItem('haqdaar.theme');
    } catch {
      /* private window: the toggle still works for this session */
    }
  }, [theme]);

  const systemDark =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const showingDark = theme ? theme === 'dark' : systemDark;
  const [declaredBanner, setDeclaredBanner] = useState(null);

  useEffect(() => {
    fetchPersonas()
      .then(({ data, stored, storedAt }) => {
        setPersonas(data || []);
    // `data` is the whole response envelope; the array is on `.needs`. Setting the
    // envelope here made `needs.length` undefined, so the front door silently fell
    // back to the domain buttons and nobody would have noticed without opening it.
    fetchNeeds(lang)
      .then(({ data }) => setNeeds(data?.needs || []))
      .catch(() => setNeeds([]));
        // If even the persona list is unavailable, say so. An empty screen with no
        // explanation is the worst of both worlds.
        if (!data) setOffline({ stored: false });
        else if (stored) setOffline({ stored: true, storedAt });
      })
      .catch((e) => setError(e.message));
  }, [lang]);

  const run = useCallback((personaId, q) => {
    setStatus('loading');
    setError(null);
    fetchEvaluation(personaId, q, lang)
      .then(({ data, stored, storedAt, detail }) => {
        if (!data) {
          setResult(null);
          setOffline({ stored: false, detail });
          setStatus('done');
          return;
        }
        setResult(data);
        setOffline(stored ? { stored: true, storedAt } : null);
        setStatus('done');
      })
      .catch((e) => {
        setError(e.message);
        setStatus('done');
      });
  }, []);

  /*
   * Ending a session, and switching between people, both purge.
   *
   * On a shared laptop the next citizen must not be able to reload and read the
   * previous one's schemes and documents. The app shell and the persona list survive
   * — they are not anyone's data — so the device still opens and works offline.
   */
  async function finish() {
    await purgeSession();
    // Her answers go with the cached verdicts. A remembered answer that survived
    // "Finish and clear" on a shared phone would be a privacy hole in the one
    // product that cannot afford one.
    forget();
    setSaved(null);
    setSelected(null);
    setResult(null);
    setOffline(null);
    setQuery('');
    setDraftQuery('');
    setIntakeVertical(null);
    setDeclaredBanner(null);
    setPurged(true);
  }

  function choose(personaId) {
    setPurged(false);
    setIntakeVertical(null);
    setDeclaredBanner(null);
    // Switching to a different person purges automatically, answers included, so
    // nobody has to remember to do it.
    forget();
    setSaved(null);
    // Clear the previous person before loading the next one.
    purgeSession().finally(() => {
      setSelected(personaId);
      setQuery('');
      setDraftQuery('');
      run(personaId, '');
    });
  }

  function ask(event) {
    event.preventDefault();
    setQuery(draftQuery);
    run(selected, draftQuery);
  }

  function clearQuery() {
    setDraftQuery('');
    setQuery('');
    run(selected, '');
  }

  return (
    <div className="app">
      {/* Fixed, behind everything, and outside the content column. It shows through the
          gaps between cards rather than under their text, so it never competes with the
          four status colours a citizen actually has to read. */}
      <Chakra className="chakra-watermark" />
      <header className="masthead">
        {/* The plain mark, NOT the tricolour badge. The badge belongs to the opening
            screen only: saffron sits beside --blocked and green beside --eligible, and
            nothing decorative may compete with the status colours above a column of
            verdict cards. See LogoBadge in Logo.jsx. */}
        <Logo className="brand-mark" />
        <h1>{s.appName}</h1>
        <span className="tagline">{s.tagline}</span>
        {/* Language sits before the theme control because it matters more: someone who
            cannot read the page cannot find the theme button either. Each option is
            written in its own script and never translated. */}
        <div className="lang-switch" role="group" aria-label="Language">
          {LANGUAGES.map((code) => (
            <button
              type="button"
              key={code}
              className={code === lang ? 'on' : undefined}
              aria-pressed={code === lang}
              lang={code}
              onClick={() => setLang(code)}
            >
              {LANGUAGE_NAMES[code]}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="theme-toggle"
          aria-label={showingDark ? s.themeToLight : s.themeToDark}
          onClick={() => setTheme(showingDark ? 'light' : 'dark')}
        >
          {showingDark ? s.themeToLight : s.themeToDark}
        </button>
      </header>

      {error && <div className="banner offline">{error}</div>}
      {offline?.stored && (
        <div className="banner offline">
          {s.offlineStored}
          {offline.storedAt ? ` (${new Date(offline.storedAt).toLocaleString()})` : ''}
        </div>
      )}
      {offline && !offline.stored && <div className="banner offline">{s.offlineNothing}</div>}
      {purged && <div className="banner purged">{s.purged}</div>}
      {declaredBanner && <div className="banner declared">{declaredBanner}</div>}

      {intakeVertical ? (
        <>
          <h2>{s.tellUs}</h2>
          <p className="tagline">{s.tellUsHint}</p>
          <Intake
            vertical={intakeVertical}
            onCancel={() => {
              setIntakeVertical(null);
              setSeed(null);
            }}
            seeded={seed}
            prefill={(() => {
              const remembered =
                saved && saved.vertical === intakeVertical ? saved : null;
              if (!seed) return remembered;
              // A remembered session wins on any field it already holds: her own
              // previous answer is better evidence than the door she came through.
              return {
                ...remembered,
                answers: { ...seed, ...(remembered?.answers || {}) },
                documents: remembered?.documents || [],
              };
            })()}
            onResult={(data, given) => {
              // Intake returns the same card shape as every other entry point, so the
              // results list below is unchanged — the profile changed, not the engine.
              setResult(data);
              setDeclaredBanner(data.declared_banner);
              setSelected(`intake:${intakeVertical}`);
              setIntakeVertical(null);
              setSeed(null);
              setStatus('done');
              // Keep the ANSWERS, never the verdict. A stored verdict goes stale the
              // day a scheme lapses or a threshold moves, and would quietly become a
              // wrong answer with nothing to flag it. Answers just get replayed.
              if (given && remember({ ...given, language: 'en' })) setSaved(recall());
            }}
          />
        </>
      ) : !selected ? (
        <>
          <p className="hero">{s.hero}</p>

          {/* The resume card. It says "on this device" out loud, because "saved"
              alone is exactly what makes people assume there is an account behind
              it, and there is not. Clearing is one tap and sits right beside it. */}
          {saved && (
            <div className="resume">
              <h2>{s.resumeTitle}</h2>
              <p className="why">
                {s.resumeHint}
                {savedAtLabel(saved.savedAt) ? ` ${savedAtLabel(saved.savedAt)}.` : '.'}
              </p>
              <div className="row">
                <button
                  type="button"
                  className="primary"
                  onClick={() => setIntakeVertical(saved.vertical)}
                >
                  {s.resumeGo}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    forget();
                    setSaved(null);
                  }}
                >
                  {s.resumeForget}
                </button>
              </div>
            </div>
          )}

          <h2>{s.tellUs}</h2>
          <p className="tagline">{s.tellUsHint}</p>
          <p className="tagline">{s.whichDomain}</p>

          {/* Need-based entry. The engine returns the vertical each need routes to, so
              this never has to know the taxonomy. Falls back to the domain buttons if
              /api/needs is unreachable, which is what happens offline on a cold cache. */}
          {/* HER OWN WORDS, read deterministically.
              No model and no key: this is pattern matching in the engine, so it works
              offline and cannot invent. It understands less than a model would, which
              is why everything it reads is shown back with the phrase that produced it
              and stays editable on the form. */}
          <div className="describe">
            <h3>{s.describeTitle}</h3>
            <textarea
              rows={3}
              value={draft}
              placeholder={s.describePlaceholder}
              onChange={(e) => {
                setDraft(e.target.value);
                setReading(null);
              }}
            />
            <button
              type="button"
              className="primary"
              disabled={readingBusy || !draft.trim()}
              onClick={() => {
                setReadingBusy(true);
                understandText(draft, lang)
                  .then(({ data }) => setReading(data || { answers: {}, understood: [] }))
                  .catch(() => setReading({ answers: {}, understood: [] }))
                  .finally(() => setReadingBusy(false));
              }}
            >
              {readingBusy ? s.describeReading : s.describeGo}
            </button>

            {reading && (
              <div className="understood">
                {reading.understood.length === 0 ? (
                  <p className="why">{s.understoodNothing}</p>
                ) : (
                  <>
                    <h4>{s.understoodTitle}</h4>
                    <ul>
                      {reading.understood.map((u) => (
                        <li key={u.question_id}>
                          <span className="q">{u.prompt}</span>
                          <span className="a">{u.display}</span>
                          <span className="src">
                            {s.understoodFrom} “{u.phrase}”
                          </span>
                        </li>
                      ))}
                    </ul>
                    {reading.vertical && (
                      <button
                        type="button"
                        className="primary"
                        onClick={() => {
                          setSeed(reading.answers);
                          setIntakeVertical(reading.vertical);
                        }}
                      >
                        {s.understoodGo}
                      </button>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* DOMAINS FIRST, then situations.
              Seven specific sentences as the only way in read as "these are the seven
              situations we handle", which is both untrue and discouraging. The domain
              is the honest unit: it is a whole corpus of rules, not a scenario. The
              sentences stay underneath as a shortcut, because picking one can pre-fill
              an answer and save her a question. */}
          <div className="front-door">
            {verticalsOf(personas).map((vertical) => (
              <button
                type="button"
                className="domain"
                key={vertical}
                onClick={() => {
                  setSeed(null);
                  setIntakeVertical(vertical);
                }}
              >
                <span className="door">{labelFor(vertical, s).door}</span>
                <span className="eg">{labelFor(vertical, s).eg}</span>
              </button>
            ))}
          </div>

          {needs.length > 0 && (
            <div className="shortcuts">
              <h3>{s.orDescribe}</h3>
              <div className="front-door">
                {needs.map((need) => (
                  <button
                    type="button"
                    className="need"
                    key={need.need_id}
                    onClick={() => {
                      setSeed(need.answers && Object.keys(need.answers).length
                        ? need.answers
                        : null);
                      setIntakeVertical(need.vertical);
                    }}
                  >
                    {need.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="secondary-block">
          <h2>{s.orPickDemo}</h2>
          <p className="tagline">{s.orPickDemoHint}</p>

          {/* Grouped by vertical because the flip between them IS the closing move:
              the same engine answering a different domain. */}
          {verticalsOf(personas).map((vertical) => (
            <section className="vertical-group" key={vertical}>
              <h3>
                {labelFor(vertical, s).group}
                <span className="vertical-hint">{s.verticalHint}</span>
              </h3>
              <div className="persona-list">
                {personas
                  .filter((p) => p.vertical === vertical)
                  .map((p) => (
                    <button
                      type="button"
                      className="persona"
                      key={p.persona_id}
                      onClick={() => choose(p.persona_id)}
                    >
                      <span className="who">{s.who?.[p.persona_id] || p.persona_id}</span>
                    </button>
                  ))}
              </div>
            </section>
          ))}
          </div>
        </>
      ) : (
        <>
          <div className="session-bar">
            <button type="button" onClick={finish}>← {s.back}</button>
            <button type="button" className="finish" onClick={finish}>
              {s.finishSession}
            </button>
          </div>
          <p className="tagline finish-hint">{s.finishHint}</p>

          {!selected.startsWith('intake:') && (
          <form className="ask" onSubmit={ask}>
            <input
              value={draftQuery}
              onChange={(e) => setDraftQuery(e.target.value)}
              placeholder={s.askPlaceholder}
              aria-label={s.askAnything}
            />
            <button type="submit">{s.ask}</button>
          </form>
          )}
          {query && (
            <button type="button" onClick={clearQuery}>
              {s.clearQuery}
            </button>
          )}

          {!selected.startsWith('intake:') && (
          <Upload
            personaId={selected}
            onResult={(data) => {
              // Extraction returns the same card shape, so the results list below is
              // unchanged — the profile changed, not the pipeline.
              setResult(data);
              setOffline(null);
              setStatus('done');
            }}
          />
          )}

          {status === 'loading' && <p className="empty">{s.loading}</p>}

          {declaredBanner && result?.ready_to_upload?.length > 0 && (
            <section className="unlock ready">
              <h2>{s.youAlreadyHave}</h2>
              <p>{result.ready_to_upload.map((d) => d.label).join(', ')}</p>
              <p className="why">{s.bringTheseHint}</p>
            </section>
          )}

          {result?.unlock && (
            <section className="unlock">
              <h2>{s.unlockHeading}</h2>
              {/* Both halves come from the engine: the count from the aggregator
                  (which only counts schemes the document alone would resolve) and the
                  name from render/labels.py. The UI never turns an id into prose —
                  that is how this chip once read "bpl ration card" above a card
                  saying "BPL ration card". */}
              <p>
                {result.unlock.document_label} → {result.unlock.count}
              </p>
            </section>
          )}

          {/* Ordered by what she can act on. A person who came for business capital
              does not want to read a wall of "not for you" first. The NOT_ELIGIBLE
              cards are COLLAPSED, never removed — the honesty is the product, and a
              judge has to be able to open them. */}
          {orderCards(result?.cards).actionable.map((card, i) => {
            const stackedWith = (result.cards || []).filter(
              (c) =>
                c.stack_group_id &&
                c.stack_group_id === card.stack_group_id &&
                c.scheme_id !== card.scheme_id,
            );
            return (
              <Card
                card={card}
                personaId={selected}
                vertical={result?.vertical}
                stackedWith={stackedWith}
                /* Filing from an intake profile would need /api/act to accept a
                   profile rather than a persona id. Out of scope here, so the
                   SIMULATED action slot is hidden rather than shown broken. */
                canAct={!selected.startsWith('intake:')}
                key={card.scheme_id || `card-${i}`}
              />
            );
          })}

          {orderCards(result?.cards).ruledOut.length > 0 && (
            <details className="ruled-out">
              <summary>
                {s.notForYou} ({orderCards(result.cards).ruledOut.length})
              </summary>
              <p className="tagline">{s.notForYouHint}</p>
              {orderCards(result.cards).ruledOut.map((card, i) => (
                <Card
                  card={card}
                  personaId={selected}
                  vertical={result?.vertical}
                  canAct={false}
                  key={card.scheme_id || `out-${i}`}
                />
              ))}
            </details>
          )}

          {status === 'done' && result && result.cards.length === 0 && (
            <p className="empty">{s.results}</p>
          )}
        </>
      )}

      {/* Last thing on the page, and deliberately not a dismissible banner: it should
          still be there on the hundredth visit. It sits outside the results block so
          it shows on the empty first screen too, which is where someone forms the
          impression this might be a government site. */}
      <footer className="disclaimer">{s.disclaimer}</footer>
    </div>
  );
}


/*
 * The provider sits OUTSIDE the component that reads the context, so App is split
 * rather than wrapped in place: a component cannot consume a context it renders.
 */
export default function App() {
  return (
    <LanguageProvider>
      {/* Inside the provider, so the opening screen says हक्कदार to someone whose phone
          is set to Marathi rather than showing English and then switching. It removes
          itself; see Splash.jsx for why it can never become a wall. */}
      <Splash />
      <AppInner />
    </LanguageProvider>
  );
}
