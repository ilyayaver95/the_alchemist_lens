/* "How it works" — a short walkthrough of the four screens.

   Opened from the header, and once by itself on a first visit. Each step can
   drop you straight onto the screen it describes, because reading about a
   feature is worse than standing in front of it. */

import { navigate } from "../router.js";
import { $, button, el, show } from "../ui.js";

const SEEN_KEY = "alchemist:tutorial-seen";

const STEPS = [
  {
    icon: "⚗️",
    title: "What this actually does",
    body:
      "Point it at a drink and it reconstructs the recipe — ingredients, proportions, method, " +
      "glassware, estimated ABV — then works out a shopping list of only the things you don't " +
      "already have.",
    detail:
      "The AI does one job: read the picture. Everything after that — which ingredients count " +
      "as pantry staples, what bottle size to buy, how many drinks you'll get out of it — is " +
      "plain arithmetic, so it comes out the same every time.",
  },
  {
    icon: "📷",
    title: "Analyze",
    route: "analyze",
    body:
      "Photograph the drink itself, or just the menu line describing it. Add the name, and the " +
      "description if the menu gives you one — it meaningfully improves the guess.",
    detail:
      "Menus in any language work; the recipe comes back in English with the drink's original " +
      "name kept. Photos are shrunk on your phone before upload, so it's quick on cellular.",
  },
  {
    icon: "📖",
    title: "Classics",
    route: "classics",
    body:
      "Twenty drinks worth knowing by heart, from the Old Fashioned to the Tom Collins, each " +
      "with real proportions and its own buy list.",
    detail: "These are written down, not generated — so they're instant, free, and identical every time.",
  },
  {
    icon: "🫙",
    title: "My Bar",
    route: "bar",
    body:
      "Tell it what you own — type the bottles, or photograph the shelf and let it read the " +
      "labels — and it'll show you what you can make right now, and what you're one or two " +
      "bottles short of.",
    detail:
      "The matching is plain logic, so it knows Cointreau covers a recipe asking for triple sec, " +
      "and that nobody counts ice as a missing ingredient. You can also ask it to invent " +
      "something using only what's on your shelf.",
  },
  {
    icon: "♡",
    title: "Favorites",
    route: "favorites",
    body: "Tap the heart on any recipe to keep it. Sign in and your drinks follow you to any device.",
    detail: "Saving the same drink twice won't clutter the list — it just stays saved.",
  },
  {
    icon: "🛒",
    title: "Buy it",
    body:
      "Every buy list ends with “Build bucket list in Paneco”. That opens a search for each " +
      "bottle, cheapest first, so you can order the round in a few taps.",
    detail:
      "Where a bottle is currently discounted, the price and the size of the discount are shown " +
      "on the row. No badge just means none was found — not that it's full price.",
  },
];

let index = 0;

export function initTutorial() {
  const modal = $("tutorial-modal");

  $("tutorial-open").addEventListener("click", () => openTutorial());
  $("tutorial-close").addEventListener("click", closeTutorial);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeTutorial();
  });
  document.addEventListener("keydown", (e) => {
    if (modal.classList.contains("hidden")) return;
    if (e.key === "Escape") closeTutorial();
    if (e.key === "ArrowRight") step(1);
    if (e.key === "ArrowLeft") step(-1);
  });

  $("tutorial-back").addEventListener("click", () => step(-1));
  $("tutorial-next").addEventListener("click", () => {
    if (index === STEPS.length - 1) closeTutorial();
    else step(1);
  });

  // First visit only. Anyone who has seen it never gets it again unless they
  // ask, and a browser that refuses storage simply never auto-opens.
  if (!remembersSeeing()) openTutorial();
}

function remembersSeeing() {
  try {
    return localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return true;
  }
}

function rememberSeeing() {
  try {
    localStorage.setItem(SEEN_KEY, "1");
  } catch {
    /* private browsing — the button is still there */
  }
}

export function openTutorial(at = 0) {
  index = at;
  paint();
  $("tutorial-modal").classList.remove("hidden");
  $("tutorial-next").focus();
}

function closeTutorial() {
  $("tutorial-modal").classList.add("hidden");
  rememberSeeing();
}

function step(delta) {
  index = Math.min(Math.max(index + delta, 0), STEPS.length - 1);
  paint();
}

function paint() {
  const current = STEPS[index];
  const last = index === STEPS.length - 1;

  $("tutorial-icon").textContent = current.icon;
  $("tutorial-title").textContent = current.title;
  $("tutorial-body").textContent = current.body;
  $("tutorial-detail").textContent = current.detail;

  const goto = $("tutorial-goto");
  goto.replaceChildren();
  show(goto, Boolean(current.route));
  if (current.route) {
    goto.append(
      button("again-btn", `Show me ${current.title}`, () => {
        closeTutorial();
        navigate(current.route);
      })
    );
  }

  $("tutorial-back").disabled = index === 0;
  $("tutorial-next").textContent = last ? "Start pouring" : "Next";
  $("tutorial-step").textContent = `${index + 1} of ${STEPS.length}`;

  const dots = $("tutorial-dots");
  dots.replaceChildren(
    ...STEPS.map((s, i) => {
      const dot = el("button", `tutorial-dot${i === index ? " active" : ""}`);
      dot.type = "button";
      dot.setAttribute("aria-label", `Go to ${s.title}`);
      dot.setAttribute("aria-current", String(i === index));
      dot.addEventListener("click", () => {
        index = i;
        paint();
      });
      return dot;
    })
  );
}
