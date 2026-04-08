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

/**
 * Functional HTTP interceptor that attaches Bearer token to all outgoing requests.
 * Reads the token from a <meta name="api-token"> tag injected by the Bottle server.
 * When no token is configured (empty meta tag), requests pass through unchanged.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const token = getApiToken();
    if (token) {
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
