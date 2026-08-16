/* Session and favorites, shared across views.

   Views subscribe rather than poll, so the header chip, the ♡ toggles, and the
   favorites list all move together when someone signs in or out. */

import { api } from "./api.js";

const listeners = new Set();

export const state = {
  user: null,
  /** FavoriteSummary[] — id, source, slug, drink_name, created_at. */
  favorites: [],
};

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function notify() {
  listeners.forEach((fn) => fn(state));
}

/* A drink counts as saved if we already have a favorite with the same slug, or
   failing that the same name. The server dedupes properly by ingredient hash;
   this is only for painting the heart before you tap it. */
export function findFavorite(data, slug) {
  const name = data?.recipe?.drink_name;
  return (
    (slug && state.favorites.find((f) => f.slug === slug)) ||
    state.favorites.find((f) => f.drink_name === name) ||
    null
  );
}

/* Deliberately silent: subscribers repaint the current view, and the favorites
   view itself calls this — notifying here would loop. Callers that change the
   list are already responsible for redrawing what they own. */
export async function refreshFavorites() {
  state.favorites = state.user ? await api.favorites() : [];
}

export async function loadSession() {
  try {
    state.user = await api.me();
    state.favorites = await api.favorites();
  } catch {
    state.user = null;
    state.favorites = [];
  }
  notify();
}

export async function setUser(user) {
  state.user = user;
  state.favorites = user ? await api.favorites() : [];
  notify();
}

export async function signOut() {
  await api.logout();
  state.user = null;
  state.favorites = [];
  notify();
}
