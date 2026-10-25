import { getCollection, type CollectionEntry } from 'astro:content';
import { termSlug } from './format';

export type Project = CollectionEntry<'projects'>;
export type Note = CollectionEntry<'notes'>;

export type TermKey = 'topics' | 'tags' | 'languages';

export interface TermBucket {
  term: string;
  slug: string;
  count: number;
}

/** `case-ab/index` → `case-ab`. Both collections are leaf bundles. */
export function slugOf(id: string): string {
  return id.split('/')[0];
}

export function byTitle(a: Project, b: Project): number {
  return a.data.title.localeCompare(b.data.title, 'en');
}

export async function getProjects(): Promise<Project[]> {
  return (await getCollection('projects')).sort(byTitle);
}

export async function getNotes(): Promise<Note[]> {
  return (await getCollection('notes')).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf(),
  );
}

export function projectSummary(project: Project): string {
  return project.data.description || project.data.external?.description || '';
}

export function githubUrl(project: Project): string {
  return `https://github.com/${project.data.github}`;
}

export function homepageUrl(project: Project): string | undefined {
  const value = project.data.external?.description;
  return value && value.startsWith('http') ? value : undefined;
}

export function starsOf(project: Project): number {
  return project.data.external?.stars ?? 0;
}

/** Languages from the sync record, falling back to the authored list. */
export function languagesOf(project: Project): string[] {
  const synced = project.data.external?.languages ?? [];
  return synced.length > 0 ? synced : project.data.languages;
}

/**
 * Taxonomies read the authored keys, except `languages`: the card badge shows
 * the synced `external.languages`, so the term pages must count the same list
 * or a language page would disagree with the badge that links to it.
 */
function termValues(entry: Project | Note, key: TermKey): string[] {
  if (key === 'languages' && 'external' in entry.data) {
    const synced = entry.data.external?.languages ?? [];
    if (synced.length > 0) return synced;
  }
  return (entry.data as Record<TermKey, string[] | undefined>)[key] ?? [];
}

/** Sorted, de-duplicated term buckets for a taxonomy key. */
export function termBuckets(
  entries: ReadonlyArray<Project | Note>,
  key: TermKey,
): TermBucket[] {
  const counts = new Map<string, number>();
  for (const entry of entries) {
    for (const value of termValues(entry, key)) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([term, count]) => ({ term, slug: termSlug(term), count }))
    .sort((a, b) => b.count - a.count || a.term.localeCompare(b.term, 'en'));
}

export function entriesWithTerm<T extends Project | Note>(
  entries: T[],
  key: TermKey,
  slug: string,
): T[] {
  return entries.filter((entry) =>
    termValues(entry, key).some((value) => termSlug(value) === slug),
  );
}

export function termFromSlug(buckets: TermBucket[], slug: string): TermBucket | undefined {
  return buckets.find((bucket) => bucket.slug === slug);
}
