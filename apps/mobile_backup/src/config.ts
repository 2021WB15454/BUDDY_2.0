// Dynamic base URL derived from optional environment-like globals.
// In React Native Metro bundler, process.env may not include custom vars unless using a plugin.
// Fallback remains localhost for dev if nothing injected.
const HOST = (typeof process !== 'undefined' && (process as any).env?.BUDDY_HOST) || 'localhost';
const PORT = (typeof process !== 'undefined' && (process as any).env?.BUDDY_PORT) || '8082';
export const API_BASE = `http://${HOST}:${PORT}`;
export const CLIENT_TOKEN = 'CHANGE_ME_TOKEN'; // Must match backend BUDDY_CLIENT_TOKEN
