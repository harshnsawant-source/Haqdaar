import { useCallback, useEffect, useState } from 'react';

import { Card } from './Card.jsx';
import { Intake } from './Intake.jsx';
import { Upload } from './Upload.jsx';
import { fetchEvaluation, fetchPersonas, purgeSession } from './api.js';
import { t } from './strings.js';

const s = t('en');

/*
 * Citizen-facing labels for the demo fixtures.
 *
 * The persona JSON's `description` field is developer documentation — it talks about
 * PROVISIONAL corpora and which lane owns what — so it does NOT belong on screen. It
 * stays in the API for debugging; the UI shows these instead.
 */
const WHO = {
  'entrepreneur-01': 'First-time SC woman entrepreneur',
  'entrepreneur-02': 'First-time entrepreneur, no caste certificate',
  sunita: 'Sunita — 60, widow, small farmer',
};

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

export default function App() {
  const [personas, setPersonas] = useState([]);
  const [selected, setSelected] = useState(null);
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [offline, setOffline] = useState(null);
  const [purged, setPurged] = useState(false);
  const [intakeVertical, setIntakeVertical] = useState(null);
  const [declaredBanner, setDeclaredBanner] = useState(null);

  useEffect(() => {
    fetchPersonas()
      .then(({ data, stored, storedAt }) => {
        setPersonas(data || []);
        // If even the persona list is unavailable, say so. An empty screen with no
        // explanation is the worst of both worlds.
        if (!data) setOffline({ stored: false });
        else if (stored) setOffline({ stored: true, storedAt });
      })
      .catch((e) => setError(e.message));
  }, []);

  const run = useCallback((personaId, q) => {
    setStatus('loading');
    setError(null);
    fetchEvaluation(personaId, q)
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
      <header className="masthead">
        <h1>{s.appName}</h1>
        <span className="tagline">{s.tagline}</span>
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
            onCancel={() => setIntakeVertical(null)}
            onResult={(data) => {
              // Intake returns the same card shape as every other entry point, so the
              // results list below is unchanged — the profile changed, not the engine.
              setResult(data);
              setDeclaredBanner(data.declared_banner);
              setSelected(`intake:${intakeVertical}`);
              setIntakeVertical(null);
              setStatus('done');
            }}
          />
        </>
      ) : !selected ? (
        <>
          <h2>{s.tellUs}</h2>
          <p className="tagline">{s.tellUsHint}</p>
          <p className="tagline">{s.whichDomain}</p>
          <div className="front-door">
            <button
              type="button"
              className="primary"
              onClick={() => setIntakeVertical('welfare')}
            >
              {s.domainWelfare}
            </button>
            <button
              type="button"
              className="primary"
              onClick={() => setIntakeVertical('entrepreneur')}
            >
              {s.domainEntrepreneur}
            </button>
          </div>

          <div className="secondary-block">
          <h2>{s.orPickDemo}</h2>
          <p className="tagline">{s.orPickDemoHint}</p>

          {/* Grouped by vertical because the flip between them IS the closing move:
              the same engine answering a different domain. */}
          {['entrepreneur', 'welfare'].map((vertical) => (
            <section className="vertical-group" key={vertical}>
              <h3>
                {vertical === 'welfare' ? s.verticalWelfare : s.verticalEntrepreneur}
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
                      <span className="who">{WHO[p.persona_id] || p.persona_id}</span>
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
    </div>
  );
}
