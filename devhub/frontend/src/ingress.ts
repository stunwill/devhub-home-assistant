const API_PREFIX = '/api/';
const INGRESS_RE = /^(.*?\/api\/hassio_ingress\/[^/]+\/)/;

export function resolveDevHubPath(path: string, pathname = window.location.pathname): string {
  if (!path.startsWith(API_PREFIX)) return path;
  const match = pathname.match(INGRESS_RE);
  if (!match) return path;
  return `${match[1]}${path.slice(1)}`;
}

function rewriteRequest(input: RequestInfo | URL): RequestInfo | URL {
  if (typeof input === 'string') return resolveDevHubPath(input);
  if (input instanceof URL) {
    if (input.origin === window.location.origin && input.pathname.startsWith(API_PREFIX)) {
      const resolved = resolveDevHubPath(input.pathname + input.search + input.hash);
      return new URL(resolved, window.location.origin);
    }
    return input;
  }
  if (input instanceof Request) {
    const url = new URL(input.url);
    if (url.origin === window.location.origin && url.pathname.startsWith(API_PREFIX)) {
      const resolved = new URL(resolveDevHubPath(url.pathname + url.search + url.hash), window.location.origin);
      return new Request(resolved, input);
    }
  }
  return input;
}

function rewriteApiImages(root: ParentNode = document): void {
  root.querySelectorAll<HTMLImageElement>('img[src^="/api/"]').forEach((img) => {
    const current = img.getAttribute('src');
    if (!current) return;
    const resolved = resolveDevHubPath(current);
    if (resolved !== current) img.setAttribute('src', resolved);
  });
}

export function installIngressRouting(): MutationObserver | null {
  if (typeof window === 'undefined' || typeof document === 'undefined') return null;

  const originalFetch = window.fetch.bind(window);
  window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => originalFetch(rewriteRequest(input), init)) as typeof window.fetch;

  rewriteApiImages();
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.matches('img[src^="/api/"]')) rewriteApiImages(node.parentNode || document);
        else rewriteApiImages(node);
      });
      if (mutation.type === 'attributes' && mutation.target instanceof HTMLImageElement) {
        rewriteApiImages(mutation.target.parentNode || document);
      }
    }
  });
  observer.observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['src']});
  return observer;
}
