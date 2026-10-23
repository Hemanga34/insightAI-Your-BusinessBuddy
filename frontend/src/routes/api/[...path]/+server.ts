import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

// Same-origin API forwarding for the built Node server. Vite proxies during development.
const forward: RequestHandler = async ({ request, params, url, fetch }) => {
  const upstream = env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const headers = new Headers();
  for (const key of ['authorization', 'content-type']) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const response = await fetch(`${upstream}/api/${params.path}${url.search}`, {
      method: request.method, headers,
      body: request.method === 'GET' ? undefined : await request.arrayBuffer(),
      signal: AbortSignal.timeout(180_000)
    });
    return new Response(response.body, {
      status: response.status,
      headers: { 'content-type': response.headers.get('content-type') || 'application/json' }
    });
  } catch {
    return Response.json({ detail: 'The service is unavailable. Please try again.' }, { status: 503 });
  }
};

export const GET = forward;
export const POST = forward;
