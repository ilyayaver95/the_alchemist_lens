/* A reusable photo dropzone: tap, drag-and-drop, or paste.

   The analyze screen and the home-bar screen both need one, so the picker owns
   its own file state and hands back a plain element to place anywhere. */

import { el, showToast } from "./ui.js";

const MAX_CLIENT_BYTES = 60 * 1024 * 1024;

/* Downscale + re-encode as JPEG client-side: keeps uploads small on cellular
   and converts iPhone HEIC photos into something the backend accepts. */
export async function toUploadableJpeg(file, maxDim = 1600) {
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
  } catch {
    /* fall through to the original file */
  }
  return file;
}

export function createPhotoPicker({ title, hint, icon = "📷", label }) {
  let selectedFile = null;

  const zone = el("div", "dropzone");
  zone.tabIndex = 0;
  zone.role = "button";
  zone.setAttribute("aria-label", label);

  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.hidden = true;

  const idle = el("div", "dropzone-idle");
  idle.append(el("div", "dropzone-icon", icon));
  const titleLine = el("p");
  titleLine.append(el("strong", null, title));
  idle.append(titleLine, el("p", "hint", hint));

  const preview = el("div", "dropzone-preview hidden");
  const previewImg = document.createElement("img");
  previewImg.alt = label;
  const clearBtn = el("button", "clear-image", "✕");
  clearBtn.type = "button";
  clearBtn.setAttribute("aria-label", "Remove photo");
  preview.append(previewImg, clearBtn);

  zone.append(input, idle, preview);

  function setFile(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) return showToast("That doesn't look like an image.");
    if (file.size > MAX_CLIENT_BYTES) return showToast("Image is too large.");
    selectedFile = file;
    previewImg.src = URL.createObjectURL(file);
    idle.classList.add("hidden");
    preview.classList.remove("hidden");
  }

  function clear() {
    selectedFile = null;
    input.value = "";
    if (previewImg.src) URL.revokeObjectURL(previewImg.src);
    previewImg.removeAttribute("src");
    idle.classList.remove("hidden");
    preview.classList.add("hidden");
  }

  zone.addEventListener("click", (e) => {
    if (e.target !== clearBtn) input.click();
  });
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", () => setFile(input.files[0]));
  clearBtn.addEventListener("click", clear);

  ["dragover", "dragenter"].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    })
  );
  zone.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

  // Paste is a document-level event, so only the picker currently on screen
  // should claim it — otherwise both screens would swallow the same image.
  document.addEventListener("paste", (e) => {
    if (zone.offsetParent === null) return;
    const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
    if (item) setFile(item.getAsFile());
  });

  return { element: zone, getFile: () => selectedFile, clear };
}
