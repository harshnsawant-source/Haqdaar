/*
 * The repayment illustration, SIH26092's second required component.
 *
 * It is a panel on a card and not a page of its own, because the question it answers
 * only makes sense about a particular scheme: "what would this cost me?" A standalone
 * calculator would have to ask her which scheme she meant, which is the confusion the
 * problem statement is about in the first place.
 *
 * WHAT IT IS CAREFUL ABOUT
 * ------------------------
 * It says INSTALMENT, not EMI. Every NSFDC product repays quarterly, and printing a
 * monthly figure as though it were the payment schedule would be wrong four times a
 * year. The monthly number is shown too, labelled as a working-out, because a citizen
 * budgets by the month even when the agency collects by the quarter.
 *
 * It prints the engine's `unknowns` and `assumptions` rather than hiding them. No
 * NSFDC page states whether interest runs during the moratorium, and that unknown
 * moves the total by real money, so it appears under the figures instead of being
 * quietly resolved. This is the calculator behaving like the rest of the product.
 *
 * A refusal is not an error. Asking for more than the scheme lends returns a sentence
 * written to be read, and it is shown as guidance, not as a failure.
 */

import { useState } from 'react';

import { fetchEmi } from './api.js';
import { useLang } from './lang.jsx';

/** Indian digit grouping. The engine sends a number; only the display is localised. */
function money(value, lang) {
  const locale = lang === 'en' ? 'en-IN' : lang === 'mr' ? 'mr-IN' : 'hi-IN';
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    // A browser without the locale data still gets a readable number.
    return `Rs ${Math.round(value)}`;
  }
}

export function Emi({ vertical, schemeId }) {
  const { s, lang } = useLang();
  const [amount, setAmount] = useState('');
  const [result, setResult] = useState(null);
  const [refused, setRefused] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function run(event) {
    event.preventDefault();
    const principal = Number(amount);
    if (!principal) return;
    setBusy(true);
    setError(null);
    fetchEmi(vertical, schemeId, principal)
      .then(({ data, refused: why }) => {
        setResult(data);
        setRefused(why);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }

  const frequencyLabel = result ? s.emiFrequency[result.frequency] || result.frequency : '';

  return (
    <details className="emi">
      <summary>{s.emiTitle}</summary>

      <form className="emi-form" onSubmit={run}>
        <label htmlFor={`emi-${schemeId}`}>{s.emiAmountLabel}</label>
        <div className="row">
          <input
            id={`emi-${schemeId}`}
            type="number"
            inputMode="numeric"
            min="1"
            /* step="any", and not a round 1000. With min="1" a step of 1000 makes the
               only valid amounts 1, 1001, 2001 and so on, so a browser silently
               refuses a round Rs 1,00,000 with "the two nearest valid values are
               99001 and 100001" and the form never submits. Found by typing the most
               obvious number a person would type. */
            step="any"
            value={amount}
            placeholder={s.emiPlaceholder}
            onChange={(e) => setAmount(e.target.value)}
          />
          <button type="submit" disabled={busy || !amount}>
            {busy ? s.emiWorking : s.emiGo}
          </button>
        </div>
      </form>

      {error && <p className="why">{error}</p>}

      {/* A refusal, in the calculator's own words. Not styled as an error, because it
          is the system working: she asked for more than this scheme lends. */}
      {refused && <p className="emi-refused">{refused}</p>}

      {result && !refused && (
        <div className="emi-result">
          <p className="emi-headline">
            <strong>{money(result.instalment_amount, lang)}</strong> {frequencyLabel}
          </p>
          <p className="emi-sub">
            {s.emiInstalments(result.instalment_count)} ·{' '}
            {s.emiMonthly(money(result.monthly_equivalent, lang))}
          </p>

          <dl className="emi-facts">
            <div>
              <dt>{s.emiRate}</dt>
              <dd>{result.annual_rate_pct}%</dd>
            </div>
            <div>
              <dt>{s.emiTotal}</dt>
              <dd>{money(result.total_repayable, lang)}</dd>
            </div>
            <div>
              <dt>{s.emiInterest}</dt>
              <dd>{money(result.total_interest, lang)}</dd>
            </div>
          </dl>

          {/* The honest half. These come from the engine, which got them from the
              corpus, which got them from the source page saying nothing. */}
          {(result.unknowns.length > 0 || result.assumptions.length > 0) && (
            <ul className="emi-caveats">
              {result.unknowns.map((line) => (
                <li key={line}>{line}</li>
              ))}
              {result.assumptions.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}

          <p className="emi-source">
            {s.emiIllustration}{' '}
            <a href={result.source_url} target="_blank" rel="noreferrer noopener">
              {s.emiSource}
            </a>
          </p>
        </div>
      )}
    </details>
  );
}
