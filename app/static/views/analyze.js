/* Screen 1: photo of a menu drink -> recipe + buy list. */

import { api } from "../api.js";
import { createPhotoPicker, toUploadableJpeg } from "../photo-picker.js";
import { renderRecipe } from "../render.js";
import { $, button, showToast, startLoading } from "../ui.js";

let lastResult = null;
let openAuth = () => {};

export function initAnalyze({ onAuthRequired }) {
  openAuth = onAuthRequired;

  const picker = createPhotoPicker({
    title: "Snap or add a photo",
    hint: "A shot of the drink itself, or of the menu",
    label: "Upload a photo of the drink or menu",
  });
  $("analyze-dropzone-slot").replaceChildren(picker.element);

  $("analyze-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("name-input").value.trim();
    if (!picker.getFile()) return showToast("Add a photo of the drink or menu first.");
    if (!name) return showToast("Give the drink a name — it's on the menu!");

    const body = new FormData();
    body.append("image", await toUploadableJpeg(picker.getFile()));
    body.append("name", name);
    body.append("description", $("description-input").value.trim());

    const submitBtn = $("analyze-submit");
    $("analyze-input-card").classList.add("hidden");
    submitBtn.disabled = true;
    const stop = startLoading($("analyze-output"));
    try {
      lastResult = await api.analyze(body);
      stop();
      paint(true);
    } catch (err) {
      stop();
      $("analyze-input-card").classList.remove("hidden");
      showToast(err.message);
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function paint(scroll) {
  const output = $("analyze-output");
  output.replaceChildren(
    renderRecipe(lastResult, { source: "analyze", onAuthRequired: openAuth }),
    button("again-btn", "↺ Analyze another drink", () => {
      lastResult = null;
      output.replaceChildren();
      $("analyze-input-card").classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "smooth" });
    })
  );
  if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
}

export function showAnalyze() {
  // Repaint rather than reset: the form and the last result survive tab
  // switches, and repainting is what refreshes the ♡ after signing in.
  if (lastResult) {
    $("analyze-input-card").classList.add("hidden");
    paint(false);
  } else {
    $("analyze-input-card").classList.remove("hidden");
  }
}
