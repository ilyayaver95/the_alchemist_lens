/* Whether the backend is actually reachable.

   The service worker serves the cached shell whether or not the API is up, so
   a dead backend looks exactly like a healthy app until you tap something.
   Every request reports what it saw, and the banner reflects that.

   Deliberately free of imports: api.js depends on this, so this must not
   depend on api.js. */

const listeners = new Set();

/* Assume reachable until something proves otherwise — showing a scary banner
   for the split second before the first request lands would be worse. */
let reachable = true;

export function isReachable() {
  return reachable;
}

export function subscribeToConnection(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function set(next) {
  if (reachable === next) return;
  reachable = next;
  listeners.forEach((fn) => fn(reachable));
}

/* Any HTTP response means the server answered — a 401 or a 503 is still a
   conversation. Only a failed fetch means unreachable. */
export const reportReachable = () => set(true);
export const reportUnreachable = () => set(false);

export async function checkConnection() {
  try {
    await fetch("/api/v1/health", { cache: "no-store" });
    set(true);
  } catch {
    set(false);
  }
  return reachable;
}
