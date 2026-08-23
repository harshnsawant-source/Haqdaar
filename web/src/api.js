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

export function fetchIntakeForm() {
  return get('/api/intake');
}

export async function submitIntake(vertical, answers, documentsHeld) {
  const response = await fetch('/api/intake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ vertical, answers, documents_held: documentsHeld }),
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

export function fetchEvaluation(personaId, query) {
  const params = new URLSearchParams({ persona_id: personaId });
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
