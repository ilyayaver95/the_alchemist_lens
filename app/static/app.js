"use strict";

const $ = (id) => document.getElementById(id);

const form = $("analyze-form");
const dropzone = $("dropzone");
const imageInput = $("image-input");
const previewImg = $("preview-img");
const submitBtn = $("submit-btn");

let selectedFile = null;

const LOADING_MESSAGES = [
  "Consulting the grimoire…",
  "Reading the color of the elixir…",
  "Inspecting the garnish under moonlight…",
  "Weighing spirits on brass scales…",
  "Deciphering the bartender's intent…",
  "Distilling proportions…",
];

/* ---------- Image selection ---------- */

function setFile(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    showToast("That doesn't look like an image.");
    return;
  }
  if (file.size > 60 * 1024 * 1024) {
    showToast("Image is too large.");
    return;
  }
  selectedFile = file;
  previewImg.src = URL.createObjectURL(file);
  $("dropzone-idle").classList.add("hidden");
  $("dropzone-preview").classList.remove("hidden");
}

function clearFile() {
  selectedFile = null;
  imageInput.value = "";
  if (previewImg.src) URL.revokeObjectURL(previewImg.src);
  previewImg.src = "";
  $("dropzone-idle").classList.remove("hidden");
  $("dropzone-preview").classList.add("hidden");
}

dropzone.addEventListener("click", (e) => {
  if (e.target.id !== "clear-image") imageInput.click();
});
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); imageInput.click(); }
});
imageInput.addEventListener("change", () => setFile(imageInput.files[0]));
$("clear-image").addEventListener("click", clearFile);

["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
);
dropzone.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

document.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) setFile(item.getAsFile());
});

/* ---------- Submit ---------- */

// Downscale + re-encode as JPEG client-side: keeps uploads small on cellular
// and converts iPhone HEIC photos into something the backend accepts.
async function toUploadableJpeg(file, maxDim = 1600) {
  try {
    const url = URL.createObjectURL(file);
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = url;
    });
    const scale = Math.min(1, maxDim / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    if (blob) return new File([blob], "photo.jpg", { type: "image/jpeg" });
  } catch { /* fall through to the original file */ }
  return file;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("name-input").value.trim();
  if (!selectedFile) return showToast("Add a photo of the drink or menu first.");
  if (!name) return showToast("Give the drink a name — it's on the menu!");

  const body = new FormData();
  body.append("image", await toUploadableJpeg(selectedFile));
  body.append("name", name);
  body.append("description", $("description-input").value.trim());

  setLoading(true);
  try {
    const res = await fetch("/api/v1/analyze", { method: "POST", body });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    renderResults(await res.json());
  } catch (err) {
    showToast(err.message || "Something went wrong — please try again.");
    setLoading(false);
  }
});

let loadingTimer = null;

function setLoading(on) {
  $("loading-card").classList.toggle("hidden", !on);
  $("input-card").classList.toggle("hidden", on);
  $("results").classList.add("hidden");
  $("again-btn").classList.add("hidden");
  submitBtn.disabled = on;
  clearInterval(loadingTimer);
  if (on) {
    let i = 0;
    $("loading-message").textContent = LOADING_MESSAGES[0];
    loadingTimer = setInterval(() => {
      i = (i + 1) % LOADING_MESSAGES.length;
      $("loading-message").textContent = LOADING_MESSAGES[i];
    }, 2600);
  }
}

/* ---------- Rendering ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatAmount(ing) {
  if (ing.amount == null) return "—";
  const nice = Number.isInteger(ing.amount) ? ing.amount : ing.amount.toFixed(2).replace(/\.?0+$/, "");
  return ing.unit ? `${nice} ${ing.unit}` : `${nice}`;
}

function renderResults(data) {
  const { recipe, buy_list: buyList } = data;

  $("r-name").textContent = recipe.drink_name;
  $("r-summary").textContent = recipe.summary;

  const badge = $("r-confidence");
  badge.textContent = `${recipe.confidence} confidence`;
  badge.className = `confidence-badge confidence-${recipe.confidence}`;

  const chips = $("r-chips");
  chips.replaceChildren();
  const addChip = (label, value) => {
    if (!value) return;
    const chip = el("span", "chip");
    chip.append(`${label} `);
    chip.append(el("strong", null, value));
    chips.append(chip);
  };
  addChip("Method:", recipe.method);
  addChip("Glass:", recipe.glassware);
  addChip("Garnish:", recipe.garnish);
  addChip("ABV:", recipe.is_alcoholic && recipe.estimated_abv != null
    ? `~${recipe.estimated_abv}%` : recipe.is_alcoholic ? null : "non-alcoholic");

  const ingList = $("r-ingredients");
  ingList.replaceChildren(...recipe.ingredients.map((ing) => {
    const li = el("li");
    li.append(el("span", "ing-amount", formatAmount(ing)));
    const name = el("span", "ing-name", ing.name);
    if (ing.notes) name.append(" ", el("span", "ing-note", `· ${ing.notes}`));
    li.append(name);
    if (ing.is_pantry_staple) li.append(el("span", "staple-tag", "pantry"));
    return li;
  }));

  $("r-steps").replaceChildren(...recipe.steps.map((s) => el("li", null, s)));

  const cuesBlock = $("r-cues-block");
  cuesBlock.classList.toggle("hidden", !recipe.visual_cues?.length);
  $("r-cues").replaceChildren(...(recipe.visual_cues || []).map((c) => el("li", null, c)));

  const groupsBox = $("b-groups");
  groupsBox.replaceChildren(...buyList.groups.map((group) => {
    const wrap = el("div", "buy-group");
    wrap.append(el("div", "buy-group-label", group.label));
    group.items.forEach((item, i) => {
      const row = el("div", "buy-item");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.id = `buy-${group.category}-${i}`;
      box.addEventListener("change", () => row.classList.toggle("checked", box.checked));
      const label = el("label");
      label.htmlFor = box.id;
      label.append(el("span", "buy-name", item.ingredient_name));
      label.append(el("span", "buy-detail", item.suggested_purchase));
      if (item.est_servings) label.append(el("span", "buy-servings", item.est_servings));
      row.append(box, label);
      wrap.append(row);
    });
    return wrap;
  }));

  const staples = $("b-staples");
  if (buyList.staples_assumed.length) {
    staples.textContent = `🏠 Assumed you have: ${buyList.staples_assumed.join(", ")}`;
    staples.classList.remove("hidden");
  } else {
    staples.classList.add("hidden");
  }

  $("provider-note").textContent =
    `${data.provider} · ${data.model}${data.cached ? " · from cache" : ""}`;

  setLoading(false);
  $("input-card").classList.add("hidden");
  $("results").classList.remove("hidden");
  $("again-btn").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$("again-btn").addEventListener("click", () => {
  $("results").classList.add("hidden");
  $("again-btn").classList.add("hidden");
  $("input-card").classList.remove("hidden");
  submitBtn.disabled = false;
});

/* ---------- Toast ---------- */

let toastTimer = null;

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 5000);
}

/* ---------- PWA ---------- */

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
