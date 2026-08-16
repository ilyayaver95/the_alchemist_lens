/* Screen 4: saved drinks. */

import { api } from "../api.js";
import { renderRecipe } from "../render.js";
import { refreshFavorites, state } from "../state.js";
import { $, button, el, emptyState, showToast, startLoading } from "../ui.js";

let openAuth = () => {};

export function initFavorites({ onAuthRequired }) {
  openAuth = onAuthRequired;
}

const SOURCE_LABELS = { analyze: "from a photo", classic: "classic", invention: "invented" };

export async function showFavorites() {
  const container = $("favorites-body");

  if (!state.user) {
    const prompt = el("div", "card signin-prompt");
    prompt.append(el("h2", null, "Sign in to keep your drinks"));
    prompt.append(
      el("p", null, "Favorites follow your account, so the same list is there on your phone and your laptop.")
    );
    prompt.append(button("transmute-btn", "Sign in or create an account", openAuth));
    container.replaceChildren(prompt);
    return;
  }

  const stop = startLoading(container);
  try {
    await refreshFavorites();
    stop();
  } catch (err) {
    stop();
    showToast(err.message);
    return;
  }

  if (!state.favorites.length) {
    container.replaceChildren(
      emptyState("No favorites yet — tap the ♡ on any recipe to keep it here.")
    );
    return;
  }

  const list = el("div", "fav-list");
  list.append(
    ...state.favorites.map((fav) => {
      const row = el("div", "fav-row");
      const open = el("button", "fav-open");
      open.type = "button";
      open.append(el("span", "fav-name", fav.drink_name));
      open.append(el("span", "fav-source", SOURCE_LABELS[fav.source] || fav.source));
      open.addEventListener("click", () => openFavorite(container, fav));
      row.append(open);
      row.append(
        button("fav-delete", "🗑", async () => {
          try {
            await api.deleteFavorite(fav.id);
            await refreshFavorites();
            showToast(`Removed ${fav.drink_name}.`, "ok");
            showFavorites();
          } catch (err) {
            showToast(err.message);
          }
        })
      );
      return row;
    })
  );
  container.replaceChildren(list);
}

async function openFavorite(container, fav) {
  const stop = startLoading(container);
  try {
    const data = await api.favorite(fav.id);
    stop();
    container.replaceChildren(
      renderRecipe(data, { slug: fav.slug, source: fav.source, onAuthRequired: openAuth }),
      button("again-btn", "↩ Back to favorites", showFavorites)
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    stop();
    showToast(err.message);
    showFavorites();
  }
}
