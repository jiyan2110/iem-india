import type { APIRoute } from 'astro';
import { toCsv } from '../../lib/table';

export const GET: APIRoute = () =>
  new Response(toCsv(), { headers: { 'content-type': 'text/csv; charset=utf-8' } });
