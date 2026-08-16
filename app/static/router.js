/* A hash router in twenty lines. No framework, no build step.

   Routes are keyed by their first segment: "#/classics/negroni" calls
   routes.classics("negroni"). */

export const DEFAULT_ROUTE = "analyze";

function parse() {
  const path = location.hash.replace(/^#\/?/, "");
  const [name, ...rest] = path.split("/").filter(Boolean);
  return { name: name || DEFAULT_ROUTE, params: rest.map(decodeURIComponent) };
}

export function navigate(path) {
  location.hash = `#/${path}`;
}

let rerun = () => {};

/** Re-run the current route — used when signing in or out changes what a view shows. */
export function refresh() {
  rerun();
}

export function startRouter(routes, onRoute) {
  rerun = () => {
    const { name, params } = parse();
    const handler = routes[name] || routes[DEFAULT_ROUTE];
    onRoute(routes[name] ? name : DEFAULT_ROUTE);
    handler(...params);
  };
  window.addEventListener("hashchange", rerun);
  rerun();
}
