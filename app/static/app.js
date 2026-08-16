/* Entry point: wire the views to the router, load the session, register the SW. */

import { refresh, startRouter } from "./router.js";
import { loadSession, subscribe } from "./state.js";
import { $ } from "./ui.js";
import { initAnalyze, showAnalyze } from "./views/analyze.js";
import { initAuth, openAuth } from "./views/auth.js";
import { initBar, showBar } from "./views/bar.js";
import { initClassics, showClassics } from "./views/classics.js";
import { initFavorites, showFavorites } from "./views/favorites.js";

const VIEWS = ["analyze", "classics", "bar", "favorites"];

function activate(name) {
  VIEWS.forEach((view) => $(`view-${view}`).classList.toggle("hidden", view !== name));
  document.querySelectorAll(".nav-tabs a").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === name);
    tab.setAttribute("aria-current", tab.dataset.view === name ? "page" : "false");
  });
}

const options = { onAuthRequired: openAuth };

initAuth();
initAnalyze(options);
initClassics(options);
initBar(options);
initFavorites(options);

// The session decides what the ♡ and the favorites screen show, so settle it
// before the first route paints.
loadSession().finally(() => {
  startRouter(
    {
      analyze: showAnalyze,
      classics: showClassics,
      bar: showBar,
      favorites: showFavorites,
    },
    activate
  );
  // Signing in or out changes what every screen shows, so repaint the current
  // one. Subscribed after the first paint so it doesn't fire during startup.
  subscribe(refresh);
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
