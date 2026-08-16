/* The one place that talks to /api/v1.

   The backend writes its HTTPException details as user-facing copy, so the
   error message thrown here is safe to show in a toast verbatim. */

const BASE = "/api/v1";

function detailOf(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors arrive as a list of {loc, msg, type}.
  if (Array.isArray(detail)) return detail.map((d) => d.msg).filter(Boolean).join("; ");
  return `Request failed (${status})`;
}

// The service worker keeps serving the cached shell when the backend is down,
// so the app looks alive while every call fails. Left alone, fetch's own
// "Failed to fetch" surfaces in a toast and tells the user nothing.
const OFFLINE_MESSAGE =
  "Can't reach the server — it may be waking up or offline. Try again in a moment.";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { credentials: "same-origin", ...options });
  } catch (cause) {
    const error = new Error(OFFLINE_MESSAGE);
    error.status = 0;
    error.cause = cause;
    throw error;
  }
  if (res.status === 204) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(detailOf(body, res.status));
    error.status = res.status;
    throw error;
  }
  return body;
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  analyze: (formData) => request("/analyze", { method: "POST", body: formData }),

  classics: () => request("/classics"),
  classic: (slug) => request(`/classics/${encodeURIComponent(slug)}`),

  pantryScan: (formData) => request("/pantry/scan", { method: "POST", body: formData }),
  pantrySuggest: (items, invent) => request("/pantry/suggest", json({ items, invent })),

  me: () => request("/auth/me"),
  signup: (credentials) => request("/auth/signup", json(credentials)),
  login: (credentials) => request("/auth/login", json(credentials)),
  logout: () => request("/auth/logout", { method: "POST" }),

  favorites: () => request("/favorites"),
  saveFavorite: (body) => request("/favorites", json(body)),
  favorite: (id) => request(`/favorites/${id}`),
  deleteFavorite: (id) => request(`/favorites/${id}`, { method: "DELETE" }),
};
