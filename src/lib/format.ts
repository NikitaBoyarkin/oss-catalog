const DATE_FMT = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

export function formatDate(value: Date | string | undefined): string {
  if (!value) return '';
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.valueOf())) return '';
  return DATE_FMT.format(date);
}

export function formatNumber(value: number | undefined): string {
  return new Intl.NumberFormat('en-US').format(value ?? 0);
}

/** "1 star" / "12 stars" / "—" for zero. */
export function formatStars(value: number | undefined): string {
  const n = value ?? 0;
  if (n === 0) return '—';
  return `${formatNumber(n)} ${n === 1 ? 'star' : 'stars'}`;
}

export function pluralize(count: number, one: string, many = `${one}s`): string {
  return `${formatNumber(count)} ${count === 1 ? one : many}`;
}

/** URL-safe term slug: `A/B Testing` → `a-b-testing`, `LLM and RAG` → `llm-and-rag`. */
export function termSlug(term: string): string {
  return term
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
