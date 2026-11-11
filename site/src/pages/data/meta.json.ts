import type { APIRoute } from 'astro';
import raw from '../../../data/meta.json';

// Counts, weights, formulas, sources and disclaimers, served as-is.
export const GET: APIRoute = () =>
  new Response(JSON.stringify(raw, null, 1), { headers: { 'content-type': 'application/json; charset=utf-8' } });
