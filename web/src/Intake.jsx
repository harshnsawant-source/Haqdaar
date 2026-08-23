import { useEffect, useState } from 'react';

import { fetchIntakeForm, submitIntake } from './api.js';
import { t } from './strings.js';

const s = t('en');

/*
 * Guided intake — the front door.
 *
 * Structured questions, never a blank box. A free-text field asks a citizen to guess
 * what the machine wants; someone with limited literacy does far better with "are you
 * a widow? yes / no". It also keeps the zero-generative-call guarantee: nothing here
 * is interpreted, only recorded.
 *
 * Every question, option and document name comes from the engine (corpus/intake.yaml
 * plus render/labels.py). This component renders them and collects values; it does not
 * know what any of them mean.
 */

export function Intake({ vertical, onResult, onCancel }) {
  const [form, setForm] = useState(null);
  const [answers, setAnswers] = useState({});
  const [documents, setDocuments] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchIntakeForm()
      .then(({ data }) => setForm(data))
      .catch((e) => setError(e.message));
  }, []);

  function setAnswer(id, value) {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  }

  function toggleDocument(id) {
    setDocuments((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  }

  function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    submitIntake(vertical, answers, documents)
      .then(({ data, detail }) => {
        if (!data) setError(detail || s.intakeUnavailable);
        else onResult(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }

  if (error) return <div className="banner offline">{error}</div>;
  if (!form) return <p className="empty">{s.loading}</p>;

  return (
    <form className="intake" onSubmit={submit}>
      {form.sections.map((section) => (
        <fieldset className="intake-section" key={section.section_id}>
          <legend>{section.title}</legend>

          {section.questions.map((q) => (
            <div className="question" key={q.question_id}>
              <p className="prompt" id={`q-${q.question_id}`}>
                {q.prompt}
              </p>

              {q.type === 'number' && (
                <input
                  type="number"
                  inputMode="numeric"
                  min={q.min ?? undefined}
                  max={q.max ?? undefined}
                  aria-labelledby={`q-${q.question_id}`}
                  value={answers[q.question_id] ?? ''}
                  onChange={(e) =>
                    setAnswer(
                      q.question_id,
                      e.target.value === '' ? null : Number(e.target.value),
                    )
                  }
                />
              )}

              {q.type === 'boolean' && (
                <div className="choices" role="group" aria-labelledby={`q-${q.question_id}`}>
                  {[
                    { value: true, label: s.yes },
                    { value: false, label: s.no },
                  ].map((opt) => (
                    <button
                      type="button"
                      key={String(opt.value)}
                      className="choice"
                      aria-pressed={answers[q.question_id] === opt.value}
                      onClick={() => setAnswer(q.question_id, opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}

              {q.type === 'choice' && (
                <div className="choices" role="group" aria-labelledby={`q-${q.question_id}`}>
                  {q.options.map((opt) => (
                    <button
                      type="button"
                      key={opt.value}
                      className="choice"
                      aria-pressed={answers[q.question_id] === opt.value}
                      onClick={() => setAnswer(q.question_id, opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}

              {q.type === 'documents' && (
                <div className="choices" role="group" aria-labelledby={`q-${q.question_id}`}>
                  {q.documents.map((doc) => (
                    <button
                      type="button"
                      key={doc.value}
                      className="choice"
                      aria-pressed={documents.includes(doc.value)}
                      onClick={() => toggleDocument(doc.value)}
                    >
                      {doc.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </fieldset>
      ))}

      <div className="intake-actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy ? s.checking : s.showMyEntitlements}
        </button>
        <button type="button" onClick={onCancel}>
          {s.cancel}
        </button>
      </div>
    </form>
  );
}
