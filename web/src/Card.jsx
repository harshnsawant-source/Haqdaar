import { useState } from 'react';

import { act } from './api.js';
import { t } from './strings.js';

/*
 * One verdict card.
 *
 * Every sentence rendered here arrives in `card.lines` / `approval_lines` / `banners`
 * from the engine. This component decides layout and colour; it never writes prose
 * about a verdict, and it never merges the approval refusal into the eligibility.
 */

const s = t('en');

export function Card({ card, personaId, stackedWith = [], canAct = true }) {
  const [action, setAction] = useState(null);
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState(null);

  const tone = card.status.toLowerCase();
  const proven = card.citations.filter((c) => c.evaluation === 'TRUE');
  const unsettled = card.citations.filter((c) => c.evaluation === 'UNKNOWN');
  // Show the clauses that carry the verdict: what was proven, or what could not be.
  const shown = proven.length ? proven : unsettled;

  const lapsed = card.window_state === 'LAPSED' || card.window_state === 'NOT_YET_OPEN';

  return (
    <article className={`card ${tone}${lapsed ? ' shut' : ''}`}>
      <div className="head">
        <h2 className="scheme">{card.scheme_name || s.results}</h2>
        <span className="pill">{s.statusLabels[card.status] || card.status}</span>
      </div>

      {/* T6. The scheme's own door, ahead of anything about this citizen. A closed
          scheme read after a proof of eligibility sends someone to a shut counter. */}
      {card.window_lines?.length > 0 && (
        <div className="window">
          {card.window_lines.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      )}

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
                {c.document_label ? `Proven from: ${c.document_label} · ` : ''}
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

      {/* Two halves of one payment must never read as two independent benefits
          (01-DEMO-CORPUS.md s2). The grouping is computed by the engine; this only
          displays it. */}
      {stackedWith.length > 0 && (
        <div className="stacked">
          <h3>{s.stackedWith}</h3>
          <p>{stackedWith.map((c) => c.scheme_name).join(', ')}</p>
          <p className="why">{s.stackedNote}</p>
        </div>
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

      {/* A+ — it acts. Every step of this is SIMULATED and says so; the banners come
          from the engine's template set, not from this component. */}
      {card.status === 'ELIGIBLE' && canAct && !lapsed && (
        <div className="action-slot">
          {!action && (
            <>
              <div className="row">
                <button
                  type="button"
                  disabled={acting}
                  onClick={() => {
                    setActing(true);
                    setActionError(null);
                    act(personaId, card.scheme_id)
                      .then(({ data, refused, detail }) => {
                        if (data) setAction(data);
                        else setActionError(refused ? detail : s.actionUnavailable);
                      })
                      .catch((e) => setActionError(e.message))
                      .finally(() => setActing(false));
                  }}
                >
                  {acting ? s.acting : s.simulatedAction}
                </button>
                <span className="badge-sim">{s.simulatedBadge}</span>
              </div>
              {actionError && <p className="why">{actionError}</p>}
            </>
          )}

          {action && <FilledApplication action={action} />}
        </div>
      )}
    </article>
  );
}

/*
 * The filled application. Banners first, always — a citizen reads SIMULATED before
 * they read a filled field. Every sentence here came from the engine.
 */
function FilledApplication({ action }) {
  return (
    <div className="application">
      {action.banners.map((b, i) => (
        <div className="sim-banner" key={i}>
          {b}
        </div>
      ))}

      {action.lines.map((line, i) => (
        <p key={i} className={i === 0 ? 'app-headline' : undefined}>
          {line}
        </p>
      ))}

      <table className="filled">
        <tbody>
          {action.filled.map((f) => (
            <tr key={f.field_id}>
              <th scope="row">{f.label}</th>
              <td>
                {String(f.value)}
                <span className="from">{f.source_document_label}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {action.gap_lines.length > 0 && (
        <div className="gaps">
          {action.gap_lines.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      )}
    </div>
  );
}
