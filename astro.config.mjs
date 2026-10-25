import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://nikitaboarkin.github.io',
  base: '/oss-catalog/',
  output: 'static',
  trailingSlash: 'ignore',
  prefetch: { prefetchAll: true, defaultStrategy: 'hover' },
  compressHTML: true,
  build: { format: 'directory' },
  markdown: {
    shikiConfig: { theme: 'github-dark' },
  },
  integrations: [sitemap({ filter: (page) => !page.includes('/404/') })],
});
