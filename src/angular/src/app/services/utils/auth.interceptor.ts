import {HttpInterceptorFn} from "@angular/common/http";

/**
 * Cached API token read from <meta name="api-token"> tag.
 * Read once from DOM on first interceptor invocation.
 */
let cachedToken: string | null = null;
let tokenRead = false;

function getApiToken(): string {
    if (!tokenRead) {
        const meta = document.querySelector("meta[name=\"api-token\"]");
        cachedToken = meta?.getAttribute("content") || "";
        tokenRead = true;
    }
    return cachedToken || "";
}

const OWN_API_PATH_PREFIX = "/server/";

/**
 * True only when `url` resolves to the origin the UI was loaded from AND its
 * path is under /server/. Fails closed: unparseable URLs return false.
 */
function isOwnApiRequest(url: string): boolean {
    const ownOrigin = window.location.origin;
    let parsed: URL;
    try {
        parsed = new URL(url, ownOrigin);
    } catch {
        console.warn("authInterceptor: request URL could not be parsed; sending without app token");
        return false;
    }
    return parsed.origin === ownOrigin && parsed.pathname.startsWith(OWN_API_PATH_PREFIX);
}

/**
 * Functional HTTP interceptor that attaches the Bearer token only to requests
 * whose URL resolves to the page's own origin with a path under /server/.
 * All other destinations (e.g. the GitHub update check) are sent without it.
 * Unparseable URLs are sent without it. An empty token passes everything
 * through unchanged.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const token = getApiToken();
    if (token && isOwnApiRequest(req.url)) {
        const authReq = req.clone({
            setHeaders: {Authorization: `Bearer ${token}`}
        });
        return next(authReq);
    }
    return next(req);
};

/**
 * Reset cached token — used by tests to ensure clean state.
 * @internal
 */
export function _resetAuthInterceptorCache(): void {
    cachedToken = null;
    tokenRead = false;
}
