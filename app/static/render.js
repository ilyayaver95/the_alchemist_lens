/* Renders an AnalyzeResponse.

   Analyzed photos, library classics, saved favorites, and AI inventions all
   come back in the same shape, so they all render through here. */

import { panecoSection } from "./paneco.js";
import { api } from "./api.js";
import { findFavorite, refreshFavorites, state } from "./state.js";
import { el, showToast } from "./ui.js";

function formatAmount(ing) {
  if (ing.amount == null) return "—";
  const nice = Number.isInteger(ing.amount) ? ing.amount : ing.amount.toFixed(2).replace(/\.?0+$/, "");
  return ing.unit ? `${nice} ${ing.unit}` : `${nice}`;
}

function chips(recipe) {
  const box = el("div", "meta-chips");
  const add = (label, value) => {
    if (!value) return;
    const chip = el("span", "chip");
    chip.append(`${label} `, el("strong", null, value));
    box.append(chip);
  };
  add("Method:", recipe.method);
  add("Glass:", recipe.glassware);
  add("Garnish:", recipe.garnish);
  add(
    "ABV:",
    recipe.is_alcoholic && recipe.estimated_abv != null
      ? `~${recipe.estimated_abv}%`
      : recipe.is_alcoholic
        ? null
        : "non-alcoholic"
  );
  return box;
}

function favoriteButton(data, slug, source, onAuthRequired) {
  const existing = findFavorite(data, slug);
  const btn = el("button", "fav-btn", existing ? "♥" : "♡");
  btn.type = "button";
  btn.classList.toggle("saved", Boolean(existing));
  btn.title = existing ? "Remove from favorites" : "Save to favorites";
  btn.setAttribute("aria-label", btn.title);

  btn.addEventListener("click", async () => {
    if (!state.user) return onAuthRequired();
    btn.disabled = true;
    try {
      const saved = findFavorite(data, slug);
      if (saved) {
        await api.deleteFavorite(saved.id);
        showToast(`Removed ${data.recipe.drink_name} from favorites.`, "ok");
      } else {
        await api.saveFavorite({ source, slug: slug || null, payload: data });
        showToast(`Saved ${data.recipe.drink_name} to favorites.`, "ok");
      }
      await refreshFavorites();
      const now = findFavorite(data, slug);
      btn.textContent = now ? "♥" : "♡";
      btn.classList.toggle("saved", Boolean(now));
    } catch (err) {
      showToast(err.message);
    } finally {
      btn.disabled = false;
    }
  });
  return btn;
}

function recipeCard(data, { slug, source, onAuthRequired }) {
  const { recipe } = data;
  const card = el("div", "card recipe-card");

  const header = el("div", "recipe-header");
  header.append(el("h2", null, recipe.drink_name));
  const badges = el("div", "header-badges");
  const badge = el("span", `confidence-badge confidence-${recipe.confidence}`, `${recipe.confidence} confidence`);
  badges.append(badge);
  if (onAuthRequired) badges.append(favoriteButton(data, slug, source, onAuthRequired));
  header.append(badges);
  card.append(header);

  card.append(el("p", "recipe-summary", recipe.summary), chips(recipe));

  card.append(el("h3", null, "Ingredients"));
  const ingredients = el("ul", "ingredients");
  ingredients.append(
    ...recipe.ingredients.map((ing) => {
      const li = el("li");
      li.append(el("span", "ing-amount", formatAmount(ing)));
      const name = el("span", "ing-name", ing.name);
      if (ing.notes) name.append(" ", el("span", "ing-note", `· ${ing.notes}`));
      li.append(name);
      if (ing.is_pantry_staple) li.append(el("span", "staple-tag", "pantry"));
      return li;
    })
  );
  card.append(ingredients);

  card.append(el("h3", null, "Method"));
  const steps = el("ol", "steps");
  steps.append(...recipe.steps.map((s) => el("li", null, s)));
  card.append(steps);

  if (recipe.visual_cues?.length) {
    card.append(el("h3", null, "What the photo revealed"));
    const cues = el("ul", "cues");
    cues.append(...recipe.visual_cues.map((c) => el("li", null, c)));
    card.append(cues);
  }
  return card;
}

// Checkbox ids must be unique across the page: the home-bar screen can show an
// invented recipe alongside other content, each with its own buy list.
let checkboxSeq = 0;

function buyListCard(data) {
  const buyList = data.buy_list;
  const card = el("div", "card buylist-card");
  card.append(el("h2", null, "🛒 Buy list"));

  const groups = el("div");
  buyList.groups.forEach((group) => {
    const wrap = el("div", "buy-group");
    wrap.append(el("div", "buy-group-label", group.label));
    group.items.forEach((item, i) => {
      const row = el("div", "buy-item");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.id = `buy-${group.category}-${i}-${checkboxSeq++}`;
      box.addEventListener("change", () => row.classList.toggle("checked", box.checked));
      const label = el("label");
      label.htmlFor = box.id;
      label.append(el("span", "buy-name", item.ingredient_name));
      label.append(el("span", "buy-detail", item.suggested_purchase));
      if (item.est_servings) label.append(el("span", "buy-servings", item.est_servings));
      row.append(box, label);
      wrap.append(row);
    });
    groups.append(wrap);
  });
  card.append(groups);

  if (buyList.staples_assumed.length) {
    card.append(el("p", "staples", `🏠 Assumed you have: ${buyList.staples_assumed.join(", ")}`));
  }

  const paneco = panecoSection(buyList);
  if (paneco) card.append(paneco);

  card.append(
    el("p", "provider-note", `${data.provider} · ${data.model}${data.cached ? " · from cache" : ""}`)
  );
  return card;
}

/**
 * @param data      an AnalyzeResponse
 * @param options   {slug, source, onAuthRequired} — omit onAuthRequired to hide the ♡
 */
export function renderRecipe(data, options = {}) {
  const results = el("div", "results");
  results.append(recipeCard(data, options), buyListCard(data));
  return results;
}
