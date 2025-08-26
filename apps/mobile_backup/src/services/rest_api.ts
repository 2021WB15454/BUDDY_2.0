import { CLIENT_TOKEN } from '../config';

export async function apiPost<T>(base: string, path: string, body: any): Promise<T> {
  const res = await fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Client-Token': CLIENT_TOKEN }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function sendChat(base: string, message: string) {
  return apiPost(base, '/chat', { message, context: {}, user_id: 'mobile_user', session_id: 'mobile_session' });
}
