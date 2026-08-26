/*
 * The language a citizen is reading in.
 *
 * One piece of state, shared, because four components need it and prop-drilling a
 * language through Card and Upload would guarantee one of them gets missed and
 * quietly renders English inside a Marathi page.
 *
 * WHAT THIS DOES NOT TOUCH
 * ------------------------
 * Verdict sentences. Those are chosen by the ENGINE from its own template set, and
 * arrive already rendered in `lines`, `approval_lines`, `banners`, `window_lines`.
 * This context only supplies UI chrome: button labels, headings, status pills.
 *
 * That split is the whole reason "it cannot hallucinate" survives translation. The
 * frontend never picks words for a verdict in any language; it passes `language` to
 * the API and displays whatever comes back. So a translation bug here can make a
 * BUTTON wrong, and can never make a CLAIM ABOUT SOMEONE'S ELIGIBILITY wrong.
 *
 * The choice is remembered per device, under its own key, so `forget()` and
 * "Finish and clear" do not reset it between citizens. Which language you read is a
 * fact about the person at the counter, not about the applicant being checked.
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { LANGUAGES, t } from './strings.js';

const KEY = 'haqdaar.lang';
const LanguageContext = createContext(null);

function initialLanguage() {
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved && LANGUAGES.includes(saved)) return saved;
  } catch {
    /* private window: fall through to the browser's own preference */
  }
  // `navigator.language` is 'mr-IN' or 'hi-IN' on a phone set to those, so match the
  // prefix rather than the full tag.
  try {
    const tag = (navigator.language || '').slice(0, 2).toLowerCase();
    if (LANGUAGES.includes(tag)) return tag;
  } catch {
    /* no navigator: English */
  }
  return 'en';
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(initialLanguage);

  useEffect(() => {
    // Screen readers and hyphenation both need this to match what is on screen.
    document.documentElement.lang = lang;
    try {
      window.localStorage.setItem(KEY, lang);
    } catch {
      /* the switch still works for this session */
    }
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, s: t(lang) }), [lang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLang() {
  const ctx = useContext(LanguageContext);
  // Falling back to English rather than throwing keeps a component usable in isolation
  // (a test, a storybook) without making the provider optional in the real tree.
  return ctx || { lang: 'en', setLang: () => {}, s: t('en') };
}
