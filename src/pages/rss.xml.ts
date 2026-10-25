import type { APIContext } from 'astro';
import rss from '@astrojs/rss';
import { getNotes, slugOf } from '../lib/collections';
import { SITE, withBase } from '../lib/site';

export async function GET(context: APIContext): Promise<Response> {
  const notes = await getNotes();
  const site = context.site ?? new URL(import.meta.env.SITE);

  return rss({
    title: SITE.title,
    description: SITE.description,
    site,
    items: notes.map((note) => ({
      title: note.data.title,
      pubDate: note.data.date,
      description: note.data.description,
      link: withBase(`notes/${slugOf(note.id)}/`),
    })),
    customData: '<language>en-us</language>',
  });
}
