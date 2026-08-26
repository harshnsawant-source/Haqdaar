/*
 * Remembering her answers, on her own device, with no account.
 *
 * WHY THIS IS NOT A LOGIN
 * -----------------------
 * The obvious way to let someone come back to their results is an account. For this
 * product that is the wrong trade twice over.
 *
 * The user is someone who does not claim what she is owed. A signup form is one more
 * wall between her and an entitlement, and the people it turns away are exactly the
 * ones the scheme was written for. And the data is caste, income, widowhood,
 * landholding, BPL status — attaching that to a login means running a server that
 * holds the most sensitive facts about the most vulnerable people in the country, as
 * a permanent breach target.
 *
 * So: her answers live in this browser, on this device. Nothing is sent anywhere,
 * there is no account, and it works with no network. The engine still stores nothing
 * (`test_no_engine_module_retains_uploaded_bytes`, `test_an_upload_leaves_nothing_on_disk`).
 *
 * WHAT IS STORED, AND WHAT IS DELIBERATELY NOT
 * --------------------------------------------
 * Stored: the answers she typed, which papers she said she holds, her language.
 * NOT stored: any verdict, any rendered card, any extracted document value.
 *
 * That split matters. Verdicts go stale — a scheme lapses, a rule is amended, a
 * threshold moves — and a remembered verdict would quietly become a wrong answer with
 * no way to tell. Answers do not go stale; they are just what she said. So we replay
 * the answers through the engine and let it decide again, every time.
 *
 * SHARED DEVICES
 * --------------
 * This runs on borrowed and shared phones, which is why `forget()` is wired into the
 * same two gestures that already purge cached verdicts: "Finish and clear", and
 * switching to a different person. A saved answer that survives those would be a
 * privacy hole in the one product that cannot afford one.
 *
 * Every call is wrapped: a private window, cleared site data, or a browser set to
 * block storage all throw on access rather than returning empty, and none of that is
 * a reason to break the page. Storage is a convenience here, never a dependency.
 */

const KEY = 'haqdaar.answers.v1';

/** Persist what she told us. Silently does nothing if storage is unavailable. */
export function remember({ vertical, answers, documents, language }) {
  // Nothing worth keeping, and an empty record would show a misleading "saved" line.
  if (!vertical || !answers || Object.keys(answers).length === 0) return false;
  try {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({
        vertical,
        answers,
        documents: documents || [],
        language: language || 'en',
        savedAt: new Date().toISOString(),
      })
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Read back what she told us, or null.
 *
 * Anything malformed is treated as absent and cleared: a half-written record from an
 * interrupted write must not be replayed into the engine as if it were her answers.
 */
export function recall() {
  let raw;
  try {
    raw = window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  try {
    const saved = JSON.parse(raw);
    if (
      !saved ||
      typeof saved.vertical !== 'string' ||
      typeof saved.answers !== 'object' ||
      saved.answers === null ||
      Array.isArray(saved.answers)
    ) {
      forget();
      return null;
    }
    return {
      vertical: saved.vertical,
      answers: saved.answers,
      documents: Array.isArray(saved.documents) ? saved.documents : [],
      language: typeof saved.language === 'string' ? saved.language : 'en',
      savedAt: typeof saved.savedAt === 'string' ? saved.savedAt : null,
    };
  } catch {
    forget();
    return null;
  }
}

/** Remove her answers from this device. Wired into every purge gesture. */
export function forget() {
  try {
    window.localStorage.removeItem(KEY);
    return true;
  } catch {
    return false;
  }
}

/**
 * "26 Aug, 09:14" — when she last answered, for the line that tells her this device
 * is holding something. Falls back to null rather than inventing a time.
 */
export function savedAtLabel(iso) {
  if (!iso) return null;
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return null;
  return when.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}
