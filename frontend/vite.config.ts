import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    // amazon-cognito-identity-js reaches for Node's `global`, which does not
    // exist in a browser. Without this the bundle throws "global is not
    // defined" before React ever mounts, leaving a blank page.
    global: 'globalThis',
  },
})
