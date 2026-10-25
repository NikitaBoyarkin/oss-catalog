import type { APIContext } from 'astro';
import {
  getNotes,
  getProjects,
  languagesOf,
  projectSummary,
  slugOf,
  starsOf,
} from '../lib/collections';
import { pluralize } from '../lib/format';
import { SITE, withBase } from '../lib/site';

function oneLine(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

export async function GET(context: APIContext): Promise<Response> {
  const site = context.site ?? new URL(import.meta.env.SITE);
  const [projects, notes] = await Promise.all([getProjects(), getNotes()]);

  const lines: string[] = [`# ${SITE.title}`, '', `> ${SITE.description}`, '', '## Projects', ''];

  for (const project of projects) {
    const summary = oneLine(projectSummary(project));
    const stars = starsOf(project);
    const language = languagesOf(project)[0];
    const meta: string[] = [];
    if (stars > 0) meta.push(pluralize(stars, 'star'));
    if (language) meta.push(language);
    const suffix = meta.length > 0 ? ` — ${meta.join(', ')}` : '';
    const url = new URL(withBase(`projects/${slugOf(project.id)}/`), site).href;
    const title = oneLine(project.data.title);
    const description = summary ? `: ${summary}` : '';
    lines.push(`- [${title}](${url})${description}${suffix}`);
  }

  if (notes.length > 0) {
    lines.push('', '## Notes', '');
    for (const note of notes) {
      const summary = oneLine(note.data.description);
      const url = new URL(withBase(`notes/${slugOf(note.id)}/`), site).href;
      const title = oneLine(note.data.title);
      const description = summary ? `: ${summary}` : '';
      lines.push(`- [${title}](${url})${description}`);
    }
  }

  return new Response(`${lines.join('\n')}\n`, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}
