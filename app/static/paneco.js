/* "Build bucket list in Paneco".

   The backend picks the search term for each bottle; all this does is present
   the links. Opening happens in the user's own browser, in a new tab — we never
   navigate away from a recipe they haven't saved. */

import { button, el, show, showToast } from "./ui.js";

function externalLink(href, text, className) {
  const link = el("a", className, text);
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

export function panecoSection(buyList) {
  const items = buyList.groups.flatMap((g) => g.items).filter((i) => i.paneco_url);
  if (!items.length) return null;

  const wrap = el("div", "paneco");
  const panel = el("div", "paneco-panel hidden");

  const cta = button("paneco-cta", `🛒 Build bucket list in Paneco (${items.length})`, () => {
    const opening = panel.classList.contains("hidden");
    show(panel, opening);
    cta.classList.toggle("open", opening);
  });

  const discounted = items.filter((i) => i.sale).length;
  panel.append(
    el(
      "p",
      "paneco-note",
      discounted
        ? `${discounted} of these are on sale right now. Each link opens that bottle's Paneco search, cheapest first.`
        : "Each link opens a Paneco search for that bottle, cheapest first — sale prices show up right in the results."
    )
  );

  const shekels = (n) => `₪${Number.isInteger(n) ? n : n.toFixed(2)}`;

  items.forEach((item) => {
    const row = el("div", "paneco-row");
    const text = el("div", "paneco-text");
    text.append(el("span", "paneco-name", item.ingredient_name));

    if (item.sale) {
      const { product_name: name, price, sale_price: salePrice, also_on_sale: more } = item.sale;
      const off = Math.round((1 - salePrice / price) * 100);
      const line = el("span", "paneco-sale-line");
      line.append(el("span", "sale-badge", `${off}% off`));
      line.append(el("span", "sale-product", name));
      line.append(el("span", "sale-price", shekels(salePrice)));
      line.append(el("span", "sale-was", shekels(price)));
      if (more > 0) line.append(el("span", "sale-more", `+${more} more on sale`));
      text.append(line);
    } else {
      text.append(el("span", "paneco-query", `searches “${item.paneco_query}”`));
    }

    row.append(text, externalLink(item.paneco_url, "Find ↗", "paneco-link"));
    panel.append(row);
  });

  const actions = el("div", "paneco-actions");
  actions.append(
    button("paneco-open-all", "Open all in tabs", () => {
      // The first window.open is a direct result of the click; browsers often
      // hold back the rest, so say so instead of failing silently.
      items.forEach((item) => window.open(item.paneco_url, "_blank", "noopener"));
      if (items.length > 1) showToast("Allow pop-ups if only the first tab opened.", "ok");
    })
  );
  if (buyList.paneco_sale_url) {
    actions.append(externalLink(buyList.paneco_sale_url, "See what's on sale ↗", "paneco-sale"));
  }
  panel.append(actions);

  wrap.append(cta, panel);
  return wrap;
}
