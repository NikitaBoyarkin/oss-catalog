import type { APIContext } from 'astro';
import { withBase } from '../lib/site';

export async function GET(context: APIContext): Promise<Response> {
  const site = context.site ?? new URL(import.meta.env.SITE);
  const sitemap = new URL(withBase('/sitemap-index.xml'), site).href;

  const body = ['User-agent: *', 'Allow: /', '', `Sitemap: ${sitemap}`, ''].join('\n');

  return new Response(body, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}
