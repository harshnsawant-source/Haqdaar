import { useCallback, useEffect, useState } from 'react';

import { Card } from './Card.jsx';
import { fetchEvaluation, fetchPersonas } from './api.js';
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

export default function App() {
  const [personas, setPersonas] = useState([]);
  const [selected, setSelected] = useState(null);
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [offline, setOffline] = useState(null);

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

  function choose(personaId) {
    setSelected(personaId);
    setQuery('');
    setDraftQuery('');
    run(personaId, '');
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

      {!selected ? (
        <>
          <h2>{s.choosePersona}</h2>
          <p className="tagline">{s.chooseHint}</p>
          <div className="persona-list">
            {personas.map((p) => (
              <button
                type="button"
                className="persona"
                key={p.persona_id}
                aria-pressed={selected === p.persona_id}
                onClick={() => choose(p.persona_id)}
              >
                <span className="vertical">{p.vertical}</span>
                <span className="who">{WHO[p.persona_id] || p.persona_id}</span>
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <button type="button" onClick={() => { setSelected(null); setResult(null); }}>
            ← {s.back}
          </button>

          <form className="ask" onSubmit={ask}>
            <input
              value={draftQuery}
              onChange={(e) => setDraftQuery(e.target.value)}
              placeholder={s.askPlaceholder}
              aria-label={s.askAnything}
            />
            <button type="submit">{s.ask}</button>
          </form>
          {query && (
            <button type="button" onClick={clearQuery}>
              {s.clearQuery}
            </button>
          )}

          {status === 'loading' && <p className="empty">{s.loading}</p>}

          {result?.unlock && (
            <section className="unlock">
              <h2>{s.unlockHeading}</h2>
              {/* The count comes from the aggregator, which only counts schemes the
                  document alone would resolve. The UI does not compute it. */}
              <p>
                {result.unlock.document_id.replace(/_/g, ' ')} → {result.unlock.count}
              </p>
            </section>
          )}

          {result?.cards?.map((card, i) => (
            <Card card={card} key={card.scheme_id || `card-${i}`} />
          ))}

          {status === 'done' && result && result.cards.length === 0 && (
            <p className="empty">{s.results}</p>
          )}
        </>
      )}
    </div>
  );
}
