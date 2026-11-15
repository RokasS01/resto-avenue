import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';

const logo = readFileSync(new URL('./src/logo.svg', import.meta.url), 'utf8');

export default defineConfig({
  plugins: [
    {
      name: 'inline-logo',
      transformIndexHtml: (html) => html.replaceAll('<!--LOGO-->', logo),
    },
  ],
  build: {
    target: 'es2020',
    chunkSizeWarningLimit: 800,
  },
});
