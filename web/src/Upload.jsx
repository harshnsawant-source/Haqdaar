import { useState } from 'react';

import { extract } from './api.js';
import { useLang } from './lang.jsx';


/*
 * Document upload.
 *
 * Two things this screen must never do: present a fixture value as something it read,
 * or present a failed read as a value. So every extracted field shows its confidence
 * and its origin, and the mode the caller chose is displayed rather than assumed.
 */

const DOCUMENT_TYPES = [
  { id: 'caste_certificate', label: 'Caste certificate' },
  { id: 'aadhaar', label: 'Aadhaar card' },
  { id: 'project_report', label: 'Project report' },
];

export function Upload({ personaId, onResult }) {
  const { s } = useLang();
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0].id);
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('FIXTURE_BACKED');
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  function submit(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    extract(personaId, mode, [{ file, documentType }])
      .then(({ data, detail }) => {
        if (!data) {
          setError(detail || s.extractUnavailable);
          return;
        }
        setReport(data);
        onResult(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }

  return (
    <section className="upload">
      <h2>{s.uploadHeading}</h2>

      <form onSubmit={submit} className="upload-form">
        <label>
          {s.documentType}
          <select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
            {DOCUMENT_TYPES.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          {s.chooseFile}
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>

        {/* The mode is an explicit, visible choice. A fixture fallback that happened
            silently would be the demo lying about what the machine did. */}
        <fieldset className="mode">
          <legend>{s.modeHeading}</legend>
          <label>
            <input
              type="radio"
              name="mode"
              value="LIVE"
              checked={mode === 'LIVE'}
              onChange={() => setMode('LIVE')}
            />
            {s.modeLive}
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              value="FIXTURE_BACKED"
              checked={mode === 'FIXTURE_BACKED'}
              onChange={() => setMode('FIXTURE_BACKED')}
            />
            {s.modeFixtureBacked}
          </label>
        </fieldset>

        <button type="submit" className="primary" disabled={!file || busy}>
          {busy ? s.reading : s.readDocument}
        </button>
      </form>

      {error && <div className="banner offline">{error}</div>}

      {report && <ExtractionReport report={report} />}
    </section>
  );
}

function ExtractionReport({ report }) {
  return (
    <div className="extraction">
      {report.ocr_available === false && (
        <div className="banner offline">{s.ocrUnavailable}</div>
      )}
      {report.fixture_backed && <div className="banner offline">{s.fixtureBacked}</div>}

      <table className="fields">
        <thead>
          <tr>
            <th scope="col">{s.field}</th>
            <th scope="col">{s.value}</th>
            <th scope="col">{s.confidence}</th>
          </tr>
        </thead>
        <tbody>
          {report.fields.map((f) => (
            <tr key={f.profile_field} className={f.origin.toLowerCase()}>
              <th scope="row">{f.label}</th>
              <td>{String(f.value)}</td>
              <td>
                <span className={`origin ${f.origin.toLowerCase()}`}>
                  {f.origin === 'EXTRACTED' ? s.originRead : s.originFixture}
                </span>
                {f.origin === 'EXTRACTED' && (
                  <span className="conf">{Math.round(f.confidence * 100)}%</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {report.reports.some((r) => r.unread.length > 0) && (
        <div className="unread">
          <p>{s.couldNotRead}</p>
          <ul>
            {report.reports.flatMap((r) =>
              r.unread_labels.map((u) => <li key={`${r.document_id}-${u}`}>{u}</li>),
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
