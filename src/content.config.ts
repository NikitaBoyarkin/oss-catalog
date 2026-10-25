import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { glob } from 'astro/loaders';

/**
 * `external` is machine-owned: `scripts/update-project-frontmatter.py` writes it
 * from `data/github-repos.toml`. Never hand-edit it — fix the source repo or the
 * record in the TOML instead.
 */
const externalSchema = z.object({
  description: z.string().default(''),
  stars: z.number().default(0),
  forks: z.number().default(0),
  releases: z.number().default(0),
  latest_release: z.string().default(''),
  first_commit: z.string().default(''),
  last_updated: z.string().default(''),
  license: z.string().default(''),
  languages: z.array(z.string()).default([]),
  contributors: z.array(z.string()).default([]),
});

const projects = defineCollection({
  loader: glob({ base: './content/projects', pattern: '*/index.md' }),
  schema: z.object({
    title: z.string(),
    description: z.string().default(''),
    github: z.string(),
    topics: z.array(z.string()).default([]),
    tags: z.array(z.string()).default([]),
    languages: z.array(z.string()).default([]),
    external: externalSchema.optional(),
  }),
});

const notes = defineCollection({
  loader: glob({ base: './content/notes', pattern: '*/index.md' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    description: z.string().default(''),
    topics: z.array(z.string()).default([]),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { projects, notes };
