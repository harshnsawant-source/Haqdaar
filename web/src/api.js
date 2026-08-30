/*
 * API client. Reads the offline stamps the service worker sets so the UI can tell the
 * citizen when it is showing a stored answer rather than a live one.
 */

async function get(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  const offline = response.headers.get('x-haqdaar-offline') === '1';
  const storedAt = response.headers.get('x-haqdaar-stored-at');

  // 503 is the service worker saying "nothing cached and no network". Any other 5xx is
  // the engine being unreachable. Both are the same fact to the citizen — we have no
  // answer for you right now — and both must read as that, not as a raw error string.
  if (response.status >= 500) {
    const body = await response.json().catch(() => ({}));
    return { data: null, offline: true, stored: false, storedAt: null, detail: body.detail };
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `request failed (${response.status})`);
  }
  return { data: await response.json(), offline, stored: offline, storedAt };
}

export function fetchIntakeForm(vertical, language = 'en') {
  const params = new URLSearchParams({ language });
  if (vertical) params.set('vertical', vertical);
  return get(`/api/intake?${params.toString()}`);
}

export async function submitIntake(vertical, answers, documentsHeld, language = 'en') {
  const response = await fetch('/api/intake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ vertical, answers, documents_held: documentsHeld, language }),
  });
  const body = await response.json().catch(() => ({}));
  if (response.status >= 500) return { data: null, offline: true, detail: body.detail };
  if (!response.ok) throw new Error(body.detail || `request failed (${response.status})`);
  return { data: body };
}

export function fetchPersonas() {
  return get('/api/personas');
}

export async function act(personaId, schemeId) {
  const params = new URLSearchParams({ persona_id: personaId, scheme_id: schemeId });
  const response = await fetch(`/api/act?${params.toString()}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  const body = await response.json().catch(() => ({}));

  // 409 is the action layer refusing to file for someone the engine could not clear.
  // That is the product working, so surface the reason rather than a generic failure.
  if (response.status === 409) {
    return { data: null, refused: true, detail: body.detail };
  }
  if (response.status >= 500) {
    return { data: null, offline: true, detail: body.detail };
  }
  if (!response.ok) throw new Error(body.detail || `request failed (${response.status})`);
  return { data: body, refused: false };
}

export async function extract(personaId, mode, documents) {
  const form = new FormData();
  form.append('persona_id', personaId);
  form.append('mode', mode);
  for (const { file, documentType } of documents) {
    form.append('files', file);
    form.append('document_types', documentType);
  }

  const response = await fetch('/api/extract', { method: 'POST', body: form });
  const body = await response.json().catch(() => ({}));

  // Offline, the extractor is simply not reachable. Say so; do not fall back to a
  // fixture behind the user's back — the mode they chose is the mode they get.
  if (response.status >= 500) return { data: null, offline: true, detail: body.detail };
  if (!response.ok) throw new Error(body.detail || `request failed (${response.status})`);
  return { data: body };
}

export function fetchEvaluation(personaId, query, language = 'en') {
  const params = new URLSearchParams({ persona_id: personaId, language });
  if (query) params.set('query', query);
  return get(`/api/evaluate?${params.toString()}`);
}

/*
 * Clear everything about the citizen who just used this device.
 *
 * Belt and braces: ask the service worker to drop its data cache, and also delete the
 * caches directly in case no worker is controlling this page (dev server, first load,
 * a worker that failed to register). Resolves either way — a purge must never appear
 * to fail, because a failed purge that looks successful is the worst outcome.
 */
export async function purgeSession() {
  const results = { worker: false, direct: false };

  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    try {
      navigator.serviceWorker.controller.postMessage({ type: 'haqdaar:purge' });
      results.worker = true;
    } catch {
      /* fall through to the direct delete */
    }
  }

  if ('caches' in window) {
    try {
      const names = await caches.keys();
      await Promise.all(
        names.filter((n) => n.includes('data')).map((n) => caches.delete(n)),
      );
      results.direct = true;
    } catch {
      /* nothing more we can do from here */
    }
  }
  return results;
}

/*
 * The need-based front door. Each need already carries the vertical that can answer it,
 * so the UI routes on `need.vertical` and never has to know the taxonomy.
 *
 * Goes through `get` like everything else, so a cached answer carries its offline stamp.
 */
export function fetchNeeds(language = 'en') {
  const params = new URLSearchParams({ language });
  return get(`/api/needs?${params.toString()}`);
}

/*
 * Two to four schemes side by side. `personaId` is optional: with it each column carries
 * that person's real status, without it the table is plain facts. There is no best fit
 * and there will not be one — see engine/haqdaar/eligibility/compare.py.
 */
export function fetchComparison(vertical, schemeIds, personaId) {
  const params = new URLSearchParams({ vertical, scheme_ids: schemeIds.join(',') });
  if (personaId) params.set('persona_id', personaId);
  return get(`/api/compare?${params.toString()}`);
}

/*
 * Read her own words into answers. Deterministic, engine-side, no model and no key.
 * Returns what it understood plus the exact phrase behind each answer, so the form can
 * show its working rather than silently pre-filling.
 */
export async function understandText(text, language = 'en') {
  const response = await fetch('/api/understand', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) return { data: null, detail: body.detail };
  return { data: body };
}

/*
 * The repayment illustration for one scheme.
 *
 * A 422 here is not a failure, it is the calculator declining: the amount is above the
 * scheme's ceiling, or the scheme is not a loan at all. The reason is written for a
 * citizen to read, so it is returned rather than thrown, and the panel prints it.
 */
export async function fetchEmi(vertical, schemeId, principal) {
  const params = new URLSearchParams({
    vertical,
    scheme_id: schemeId,
    principal: String(principal),
  });
  const response = await fetch(`/api/emi?${params.toString()}`, {
    headers: { Accept: 'application/json' },
  });
  const body = await response.json().catch(() => ({}));
  if (response.status === 422) return { data: null, refused: body.detail };
  if (!response.ok) throw new Error(body.detail || `request failed (${response.status})`);
  return { data: body, refused: null };
}
