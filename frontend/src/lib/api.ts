let token = '';
export const setToken = (value: string) => { token = value; };

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api${path}`, { ...options, headers });
  const data = await response.json();
  if (!response.ok) {
    const message = typeof data.detail === 'string' ? data.detail : 'Please check the fields and try again.';
    throw new Error(message);
  }
  return data;
}

export type Workspace = { name: string; industry: string; currency: string; timezone: string; email: string };
export type SourceDocument = {
  id: string; filename: string; extension: string; size_bytes: number; status: string; error: string | null;
  extraction?: { verified: boolean; blocks: { location: Record<string, string | number>; text: string }[] } | null;
};
