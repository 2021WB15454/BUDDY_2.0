// Simplified (insecure) placeholder encryption utilities; replace with platform secure modules.
export function deriveKey(passphrase: string): string {
  return btoa(unescape(encodeURIComponent(passphrase))).slice(0, 32).padEnd(32, '0');
}

export function encrypt(plaintext: string, key: string): { iv: string; ciphertext: string } {
  const iv = Math.random().toString(36).slice(2, 14);
  const ct = Array.from(plaintext).map((c, i) => String.fromCharCode(c.charCodeAt(0) ^ key.charCodeAt(i % key.length))).join('');
  return { iv, ciphertext: btoa(ct) };
}
