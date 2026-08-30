import { createHash } from 'node:crypto'
import { readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const TOKEN = '__HAQDAAR_SHELL_BUILD__'

/*
 * Stamp the service worker's cache version with a hash of what it caches.
 *
 * The worker's cache name is derived from VERSION, and `activate` deletes only caches
 * whose names no longer match. Leaving VERSION alone therefore keeps the old shell
 * cache alive, and a returning visitor can be served an index.html pointing at asset
 * filenames this build replaced. Those 404, no JavaScript runs, and the page is white.
 * It happened once, by hand, and hand-bumping only postpones the next time.
 *
 * A CONTENT HASH rather than a timestamp, so the version moves when the shell actually
 * moves. A timestamp would invalidate every visitor's cache on every deploy, including
 * deploys that changed nothing they hold.
 *
 * It THROWS if the token is missing. A silent no-op here would restore exactly the bug
 * this exists to prevent, and the build is the only place left to catch it.
 */
function stampServiceWorker() {
  let outDir

  return {
    name: 'haqdaar-stamp-service-worker',
    apply: 'build',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
    },
    closeBundle() {
      const swPath = join(outDir, 'sw.js')
      const source = readFileSync(swPath, 'utf8')

      if (!source.includes(TOKEN)) {
        throw new Error(
          `sw.js has no ${TOKEN}. The cache version must be stamped by the build, ` +
            'not written by hand: a literal that nobody remembers to change serves ' +
            'returning visitors a stale shell and a white page.',
        )
      }

      // Hash what the worker actually serves: the built assets, the HTML that points
      // at them, and the worker's own source, so a change to SHELL_ASSETS alone still
      // moves the version.
      const hash = createHash('sha256')
      hash.update(source)
      hash.update(readFileSync(join(outDir, 'index.html')))
      for (const name of readdirSync(join(outDir, 'assets')).sort()) {
        hash.update(name)
        hash.update(readFileSync(join(outDir, 'assets', name)))
      }
      const version = hash.digest('hex').slice(0, 12)

      writeFileSync(swPath, source.split(TOKEN).join(version), 'utf8')
      console.log(`  service worker cache version: ${version}`)
    },
  }
}

export default defineConfig({
  plugins: [react(), stampServiceWorker()],
  // The engine runs locally on 8000. Proxying keeps the PWA same-origin, so the
  // service worker sees API calls it is allowed to cache — a cross-origin fetch would
  // be opaque to it and the offline story would quietly not work.
  //
  // `preview` needs its own entry: vite does NOT apply `server.proxy` to the preview
  // server, and preview is what actually exercises the service worker, because the
  // worker only registers in production builds.
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  preview: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
