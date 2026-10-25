export const SITE = {
  title: 'Analytics Project Catalog',
  description:
    'A data-driven catalog of open-source analytics projects: one page per repository, with metadata synced from the GitHub API.',
  author: 'Nikita Boyarkin',
  github: 'https://github.com/NikitaBoyarkin',
  repo: 'https://github.com/NikitaBoyarkin/oss-catalog',
} as const;

const rawBase = import.meta.env.BASE_URL;
const base = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase;

/** Prefix an absolute site path with the deployment base (`/oss-catalog`). */
export function withBase(path = '/'): string {
  if (!path.startsWith('/')) return `${base}/${path}`;
  return path === '/' ? `${base}/` : `${base}${path}`;
}

export function absoluteUrl(path = '/'): string {
  return new URL(withBase(path), import.meta.env.SITE).href;
}

export type NavKey = 'home' | 'projects' | 'notes' | 'topics' | 'tags' | 'languages';

export const NAV: ReadonlyArray<{ key: NavKey; label: string; href: string }> = [
  { key: 'projects', label: 'Projects', href: '/projects/' },
  { key: 'notes', label: 'Notes', href: '/notes/' },
  { key: 'topics', label: 'Topics', href: '/topics/' },
  { key: 'tags', label: 'Tags', href: '/tags/' },
  { key: 'languages', label: 'Languages', href: '/languages/' },
];
