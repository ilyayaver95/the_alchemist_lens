/* Small DOM helpers shared by every view. */

export const $ = (id) => document.getElementById(id);

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function button(className, text, onClick) {
  const node = el("button", className, text);
  node.type = "button";
  node.addEventListener("click", onClick);
  return node;
}

export function show(node, visible) {
  node.classList.toggle("hidden", !visible);
}

let toastTimer = null;

export function showToast(message, kind = "error") {
  const toast = $("toast");
  toast.textContent = message;
  toast.className = kind === "ok" ? "toast toast-ok" : "toast";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 5000);
}

const LOADING_MESSAGES = [
  "Consulting the grimoire…",
  "Reading the color of the elixir…",
  "Inspecting the garnish under moonlight…",
  "Weighing spirits on brass scales…",
  "Deciphering the bartender's intent…",
  "Distilling proportions…",
];

/* Drops an animated loading card into `container` and returns a stop() that
   removes it. Callers must always call stop(), including on failure. */
export function startLoading(container) {
  const card = el("section", "card loading-card");
  card.setAttribute("aria-live", "polite");
  card.append(el("div", "alembic", "⚗️"));
  const message = el("p", "loading-message", LOADING_MESSAGES[0]);
  card.append(message);
  container.replaceChildren(card);

  let i = 0;
  const timer = setInterval(() => {
    i = (i + 1) % LOADING_MESSAGES.length;
    message.textContent = LOADING_MESSAGES[i];
  }, 2600);

  return () => {
    clearInterval(timer);
    card.remove();
  };
}

export function emptyState(text) {
  return el("p", "empty-state", text);
}
