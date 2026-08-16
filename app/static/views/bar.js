/* Screen 3: what can I make with what I already own?

   Two ways in — type the bottles, or photograph the shelf. The scan only fills
   the chip list; nothing is suggested until you've had a chance to fix what the
   camera misread. */

import { api } from "../api.js";
import { createPhotoPicker, toUploadableJpeg } from "../photo-picker.js";
import { renderRecipe } from "../render.js";
import { navigate } from "../router.js";
import { $, button, el, emptyState, show, showToast, startLoading } from "../ui.js";

const inventory = [];
let openAuth = () => {};
let picker = null;

export function initBar({ onAuthRequired }) {
  openAuth = onAuthRequired;

  picker = createPhotoPicker({
    title: "Photograph your shelf",
    hint: "One picture with all the bottles in it",
    icon: "🫙",
    label: "Upload a photo of your bottles",
  });
  $("bar-dropzone-slot").replaceChildren(picker.element);

  $("bar-add-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("bar-input");
    addItems(input.value);
    input.value = "";
    input.focus();
  });

  $("bar-scan-btn").addEventListener("click", scanShelf);
  $("bar-clear-btn").addEventListener("click", clearBar);
  $("bar-suggest-btn").addEventListener("click", () => suggest(false));
  $("bar-invent-btn").addEventListener("click", () => suggest(true));

  renderChips();
}

function addItems(raw) {
  // Commas let people paste a whole shelf at once.
  const added = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s && !inventory.some((i) => i.toLowerCase() === s.toLowerCase()));
  inventory.push(...added);
  renderChips();
}

function renderChips() {
  const box = $("bar-chips");
  if (!inventory.length) {
    box.replaceChildren(emptyState("Nothing on the shelf yet — add a bottle or scan a photo."));
  } else {
    box.replaceChildren(
      ...inventory.map((name) => {
        const chip = el("span", "pantry-chip");
        chip.append(el("span", null, name));
        chip.append(
          button("pantry-chip-x", "✕", () => {
            inventory.splice(inventory.indexOf(name), 1);
            renderChips();
          })
        );
        return chip;
      })
    );
  }
  const ready = inventory.length > 0;
  $("bar-suggest-btn").disabled = !ready;
  $("bar-invent-btn").disabled = !ready;
  show($("bar-clear-btn"), ready);
}

async function scanShelf() {
  const file = picker.getFile();
  if (!file) return showToast("Add a photo of your bottles first.");

  const body = new FormData();
  body.append("image", await toUploadableJpeg(file));
  body.append("hint", $("bar-input").value.trim());

  const output = $("bar-output");
  const stop = startLoading(output);
  try {
    const scan = await api.pantryScan(body);
    stop();
    output.replaceChildren();
    addItems(scan.items.map((i) => i.name).join(","));
    if (!scan.items.length) showToast("Couldn't read any bottles — try a closer photo.");
    else showToast(`Found ${scan.items.length} bottles — edit the list, then ask for drinks.`, "ok");
    if (scan.notes) output.replaceChildren(el("p", "scan-note", `👁 ${scan.notes}`));
  } catch (err) {
    stop();
    showToast(err.message);
  }
}

function matchList(title, matches, hint) {
  const wrap = el("div", "match-block");
  wrap.append(el("h3", null, title));
  if (hint) wrap.append(el("p", "match-hint", hint));
  const list = el("div", "match-list");
  list.append(
    ...matches.map((m) => {
      const row = el("button", "match-row");
      row.type = "button";
      const head = el("div", "match-head");
      head.append(el("span", "match-name", m.drink_name));
      if (m.missing.length) {
        head.append(el("span", "match-missing", `needs ${m.missing.join(" + ")}`));
      }
      row.append(head, el("p", "match-summary", m.summary));
      row.addEventListener("click", () => navigate(`classics/${m.slug}`));
      return row;
    })
  );
  wrap.append(list);
  return wrap;
}

async function suggest(invent) {
  const output = $("bar-output");
  const stop = startLoading(output);
  try {
    const result = await api.pantrySuggest(inventory, invent);
    stop();
    const parts = [];
    if (result.makeable.length) {
      parts.push(matchList(`✅ You can make ${result.makeable.length} of these now`, result.makeable));
    }
    if (result.nearly.length) {
      parts.push(
        matchList("🛒 One or two bottles away", result.nearly, "Tap a drink to see its full buy list.")
      );
    }
    if (result.invention) {
      parts.push(el("h3", "invention-heading", "✨ Invented for your shelf"));
      parts.push(
        renderRecipe(result.invention, { source: "invention", onAuthRequired: openAuth })
      );
    }
    if (!parts.length) {
      parts.push(
        emptyState(
          "Nothing in the library matches that shelf yet. Add a base spirit — gin, whiskey, rum, vodka, or tequila — and try again."
        )
      );
    }
    output.replaceChildren(...parts);
  } catch (err) {
    stop();
    showToast(err.message);
  }
}

export function showBar() {
  renderChips();
}

export function clearBar() {
  inventory.length = 0;
  $("bar-output").replaceChildren();
  picker?.clear();
  renderChips();
}
