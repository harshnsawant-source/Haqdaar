/*
 * Where to take the application. SIH26092's third component.
 *
 * The problem statement is blunt about why this matters: direct loan applications are
 * not entertained, everything routes through more than a hundred Channel Partners, and
 * an applicant who cannot find the right one ends up misrouted or gives up.
 *
 * BY STATE, AND IT SAYS SO
 * -----------------------
 * Not by distance. The published partner lists carry postal addresses and no
 * coordinates, and geocoding them would mean an external service and an API key, which
 * would end the two claims this product actually rests on: no keys, and it works with
 * no network. A state is what she knows about herself anyway, and a State Channelising
 * Agency is a state-level body, so state is the right grain rather than a compromise.
 *
 * THE REFUSAL IS NOT AN ERROR STATE
 * ---------------------------------
 * `cannot_rank` arrives on every successful response and is rendered every time a
 * partner is. The problem statement asks for partners filtered so applications avoid
 * those with high NPAs or overdues; NSFDC publishes no such figures. So the order on
 * screen carries no meaning, and the panel says that rather than letting a list imply
 * a ranking. Hiding it would turn an ordering into a recommendation.
 */

import { useEffect, useState } from 'react';

import { fetchPartners } from './api.js';
import { useLang } from './lang.jsx';

function PartnerRow({ partner }) {
  return (
    <li>
      <span className="partner-name">{partner.name}</span>
      {partner.address && <span className="partner-address">{partner.address}</span>}
      <span className="partner-kind">{partner.category_label}</span>
    </li>
  );
}

export function Partners({ vertical, schemeId }) {
  const { s } = useLang();
  const [state, setState] = useState('');
  const [data, setData] = useState(null);
  const [refused, setRefused] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  // The state list comes from the same endpoint, so the picker cannot offer a state
  // the corpus has no partner for. Fetched once the panel is actually opened, because
  // a closed panel on every card should cost nothing.
  useEffect(() => {
    if (!open || data || refused) return;
    fetchPartners(vertical, schemeId, null)
      .then(({ data: body, refused: why }) => {
        setData(body);
        setRefused(why);
      })
      .catch((e) => setError(e.message));
  }, [open, data, refused, vertical, schemeId]);

  function pick(next) {
    setState(next);
    setError(null);
    fetchPartners(vertical, schemeId, next || null)
      .then(({ data: body, refused: why }) => {
        setData(body);
        setRefused(why);
      })
      .catch((e) => setError(e.message));
  }

  const chosen = Boolean(state) && data;
  const nothingHere = chosen && data.primary.length === 0 && data.also.length === 0;

  return (
    <details className="partners" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>{s.partnersTitle}</summary>

      {error && <p className="why">{error}</p>}
      {refused && <p className="emi-refused">{refused}</p>}

      {data && !refused && (
        <>
          <div className="partners-pick">
            <label htmlFor={`st-${schemeId}`}>{s.partnersStateLabel}</label>
            <select
              id={`st-${schemeId}`}
              value={state}
              onChange={(e) => pick(e.target.value)}
            >
              <option value="">{s.partnersStatePrompt}</option>
              {data.states.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {chosen && (
            <div className="partners-result">
              {nothingHere ? (
                <p className="emi-refused">{s.partnersNone}</p>
              ) : (
                <>
                  {data.primary.length > 0 && (
                    <>
                      <h4>{s.partnersPrimary}</h4>
                      <ul className="partner-list">
                        {data.primary.map((p) => (
                          <PartnerRow key={p.name} partner={p} />
                        ))}
                      </ul>
                    </>
                  )}

                  {data.also.length > 0 && (
                    <>
                      <h4>{s.partnersAlso}</h4>
                      <ul className="partner-list">
                        {data.also.map((p) => (
                          <PartnerRow key={p.name} partner={p} />
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )}

              {/* Always, whenever a partner is on screen. */}
              <p className="partners-cannot">{data.cannot_rank}</p>

              {data.unplaced > 0 && (
                <p className="partners-unplaced">{s.partnersUnplaced(data.unplaced)}</p>
              )}

              <p className="emi-source">
                {s.partnersFrom}{' '}
                <a href={data.source_url} target="_blank" rel="noreferrer noopener">
                  {s.partnersSource}
                </a>
              </p>
            </div>
          )}
        </>
      )}
    </details>
  );
}
