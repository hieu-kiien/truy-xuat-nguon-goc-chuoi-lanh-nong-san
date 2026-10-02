import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Public commit identity only; never inject environment secrets into HTML.
const candidate = process.env.RENDER_GIT_COMMIT ?? process.env.GITHUB_SHA ?? ''
const buildCommit = /^[a-f0-9]{40}$/i.test(candidate) ? candidate : 'local'

export default defineConfig({
  plugins: [react(), {
    name: 'agrochain-build-identity',
    transformIndexHtml() {
      return [{ tag: 'meta', attrs: { name: 'agrochain-build', content: buildCommit }, injectTo: 'head' }]
    },
  }],
})
