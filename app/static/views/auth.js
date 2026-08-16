/* Sign in / sign up, in a modal, plus the header chip that reflects the session. */

import { api } from "../api.js";
import { setUser, signOut, state, subscribe } from "../state.js";
import { $, button, el, show, showToast } from "../ui.js";

let mode = "login";

export function initAuth() {
  const modal = $("auth-modal");
  const form = $("auth-form");

  $("auth-close").addEventListener("click", closeAuth);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeAuth();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) closeAuth();
  });
  $("auth-switch").addEventListener("click", () => {
    mode = mode === "login" ? "signup" : "login";
    paintModal();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const credentials = {
      email: $("auth-email").value.trim(),
      password: $("auth-password").value,
    };
    if (credentials.password.length < 8) {
      return showToast("Passwords need at least 8 characters.");
    }
    const submit = $("auth-submit");
    submit.disabled = true;
    try {
      const user = mode === "login" ? await api.login(credentials) : await api.signup(credentials);
      await setUser(user);
      closeAuth();
      showToast(mode === "login" ? "Welcome back." : "Account created — your drinks will be saved.", "ok");
    } catch (err) {
      showToast(err.message);
    } finally {
      submit.disabled = false;
    }
  });

  subscribe(paintChip);
  paintChip();
  paintModal();
}

export function openAuth() {
  $("auth-modal").classList.remove("hidden");
  $("auth-email").focus();
}

function closeAuth() {
  $("auth-modal").classList.add("hidden");
  $("auth-form").reset();
}

function paintModal() {
  const signup = mode === "signup";
  $("auth-title").textContent = signup ? "Create an account" : "Sign in";
  $("auth-submit").textContent = signup ? "Create account" : "Sign in";
  $("auth-switch").textContent = signup ? "Already have an account? Sign in" : "New here? Create an account";
  show($("auth-password-hint"), signup);
}

function paintChip() {
  const chip = $("auth-chip");
  if (state.user) {
    const wrap = el("div", "auth-user");
    wrap.append(el("span", "auth-email-label", state.user.email));
    wrap.append(
      button("auth-link", "Sign out", async () => {
        await signOut();
        showToast("Signed out.", "ok");
      })
    );
    chip.replaceChildren(wrap);
  } else {
    chip.replaceChildren(button("auth-link", "Sign in", openAuth));
  }
}
