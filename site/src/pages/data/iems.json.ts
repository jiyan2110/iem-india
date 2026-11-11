import type { APIRoute } from 'astro';
import raw from '../../../data/iems.json';

// The source file, served as-is.
export const GET: APIRoute = () =>
  new Response(JSON.stringify(raw), { headers: { 'content-type': 'application/json; charset=utf-8' } });
