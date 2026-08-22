import { t } from './strings.js';

/*
 * One verdict card.
 *
 * Every sentence rendered here arrives in `card.lines` / `approval_lines` / `banners`
 * from the engine. This component decides layout and colour; it never writes prose
 * about a verdict, and it never merges the approval refusal into the eligibility.
 */

const s = t('en');

export function Card({ card }) {
  const tone = card.status.toLowerCase();
  const proven = card.citations.filter((c) => c.evaluation === 'TRUE');
  const unsettled = card.citations.filter((c) => c.evaluation === 'UNKNOWN');
  // Show the clauses that carry the verdict: what was proven, or what could not be.
  const shown = proven.length ? proven : unsettled;

  return (
    <article className={`card ${tone}`}>
      <div className="head">
        <h2 className="scheme">{card.scheme_name || s.results}</h2>
        <span className="pill">{s.statusLabels[card.status] || card.status}</span>
      </div>

      <div className="lines">
        {card.lines.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>

      {shown.length > 0 && (
        <details className="proof">
          <summary>{s.proofHeading}</summary>
          {shown.map((c) => (
            <blockquote className="clause" key={c.clause_id}>
              {c.clause_text}
              <span className="meta">
                {c.document_id ? `Proven from: ${c.document_id.replace(/_/g, ' ')} · ` : ''}
                {c.decided_by ? `Decided by: ${c.decided_by} · ` : ''}
                <a href={c.source_url} target="_blank" rel="noreferrer">
                  {s.sourceLink}
                </a>
              </span>
            </blockquote>
          ))}
        </details>
      )}

      {/* The approval split: its own block, its own colour, never merged above. */}
      {card.approval_lines.length > 0 && (
        <section className="approval">
          <h3>{s.approvalHeading}</h3>
          {card.approval_lines.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </section>
      )}

      {card.banners.length > 0 && (
        <div className="notes">
          {card.banners.map((b, i) => (
            <div className="note" key={i}>
              {b}
            </div>
          ))}
        </div>
      )}

      {/* Day 5 lands the real filing flow here. Marked SIMULATED so nobody — judge or
          teammate — can mistake the placeholder for a working submission. */}
      {card.status === 'ELIGIBLE' && (
        <div className="action-slot">
          <div className="row">
            <button type="button" disabled>
              {s.simulatedAction}
            </button>
            <span className="badge-sim">{s.simulatedBadge}</span>
          </div>
          <p className="why">{s.simulatedNote}</p>
        </div>
      )}
    </article>
  );
}
