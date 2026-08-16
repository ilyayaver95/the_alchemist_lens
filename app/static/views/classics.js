/* Screen 2: browse the bundled classic cocktails. */

import { api } from "../api.js";
import { renderRecipe } from "../render.js";
import { navigate } from "../router.js";
import { $, button, el, emptyState, showToast, startLoading } from "../ui.js";

let cache = null;
let openAuth = () => {};

export function initClassics({ onAuthRequired }) {
  openAuth = onAuthRequired;
}

async function loadList() {
  if (!cache) cache = await api.classics();
  return cache;
}

export async function showClassics(slug) {
  const container = $("classics-body");
  if (slug) return showDetail(container, slug);

  const stop = startLoading(container);
  try {
    const classics = await loadList();
    stop();
    const grid = el("div", "classic-grid");
    grid.append(
      ...classics.map((c) => {
        const tile = el("button", "classic-tile");
        tile.type = "button";
        tile.append(el("h3", null, c.drink_name));
        tile.append(el("p", "classic-summary", c.summary));
        const tags = el("div", "classic-tags");
        tags.append(...c.tags.slice(0, 3).map((t) => el("span", "tag", t)));
        if (c.estimated_abv != null) tags.append(el("span", "tag tag-abv", `~${c.estimated_abv}%`));
        tile.append(tags);
        tile.addEventListener("click", () => navigate(`classics/${c.slug}`));
        return tile;
      })
    );
    container.replaceChildren(grid);
  } catch (err) {
    stop();
    container.replaceChildren(emptyState("Couldn't load the library."));
    showToast(err.message);
  }
}

async function showDetail(container, slug) {
  const stop = startLoading(container);
  try {
    const data = await api.classic(slug);
    stop();
    container.replaceChildren(
      renderRecipe(data, { slug, source: "classic", onAuthRequired: openAuth }),
      button("again-btn", "↩ Back to the library", () => navigate("classics"))
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    stop();
    container.replaceChildren(
      emptyState("That drink isn't in the library."),
      button("again-btn", "↩ Back to the library", () => navigate("classics"))
    );
    showToast(err.message);
  }
}
