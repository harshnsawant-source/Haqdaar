import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Register the service worker in production builds. In dev it would cache the module
// graph and make edits confusing; the offline story is verified against `npm run
// build` + `npm run preview`, which is what a phone would install anyway.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      // A failed registration must not break the app; it only loses offline.
      console.warn('[haqdaar] service worker registration failed', err);
    });
  });
}
