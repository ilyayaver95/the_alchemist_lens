/* Entry point: wire the views to the router, load the session, register the SW. */

import { checkConnection, isReachable, subscribeToConnection } from "./connection.js";
import { refresh, startRouter } from "./router.js";
import { loadSession, subscribe } from "./state.js";
import { $, show, showToast } from "./ui.js";
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

/* Connection banner. Every API call reports what it saw, so this stays honest
   without polling; the explicit checks are only for the retry button and for
   the browser telling us the network came back. */
function initConnectionBanner() {
  const banner = $("offline-banner");
  const retry = $("offline-retry");

  subscribeToConnection((reachable) => show(banner, !reachable));

  retry.addEventListener("click", async () => {
    retry.disabled = true;
    retry.textContent = "Checking…";
    const reachable = await checkConnection();
    retry.disabled = false;
    retry.textContent = "Retry";
    if (reachable) {
      showToast("Back online.", "ok");
      // The session and whatever screen is open were both resolved against a
      // server that wasn't answering — redo them now that one is.
      await loadSession();
      refresh();
    }
  });

  window.addEventListener("online", checkConnection);
  show(banner, !isReachable());
}

const options = { onAuthRequired: openAuth };

initConnectionBanner();
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
