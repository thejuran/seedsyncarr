import {TestBed} from "@angular/core/testing";
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {authInterceptor, _resetAuthInterceptorCache} from "../../../../services/utils/auth.interceptor";

describe("authInterceptor", () => {
    let httpClient: HttpClient;
    let httpMock: HttpTestingController;

    const GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/thejuran/seedsyncarr/releases/latest";

    function setupWithMeta(content: string | null): void {
        // Remove any existing meta tag
        const existing = document.querySelector("meta[name=\"api-token\"]");
        if (existing) {
            existing.remove();
        }

        // Add meta tag if content is not null
        if (content !== null) {
            const meta = document.createElement("meta");
            meta.setAttribute("name", "api-token");
            meta.setAttribute("content", content);
            document.head.appendChild(meta);
        }

        // Reset the interceptor cache so it re-reads the meta tag
        _resetAuthInterceptorCache();

        TestBed.configureTestingModule({
            providers: [
                provideHttpClient(withInterceptors([authInterceptor])),
                provideHttpClientTesting(),
            ]
        });

        httpClient = TestBed.inject(HttpClient);
        httpMock = TestBed.inject(HttpTestingController);
    }

    function expectNoAuth(url: string): void {
        httpClient.get(url, {responseType: "text"}).subscribe();
        const req = httpMock.expectOne(url);
        expect(req.request.headers.has("Authorization")).toBeFalse();
        req.flush("ok");
    }

    function expectBearer(url: string, token: string): void {
        httpClient.get(url, {responseType: "text"}).subscribe();
        const req = httpMock.expectOne(url);
        expect(req.request.headers.get("Authorization")).toBe(`Bearer ${token}`);
        req.flush("ok");
    }

    afterEach(() => {
        httpMock.verify();
        // Cleanup meta tag
        const meta = document.querySelector("meta[name=\"api-token\"]");
        if (meta) {
            meta.remove();
        }
        _resetAuthInterceptorCache();
    });

    it("should add Authorization header when token is present", () => {
        setupWithMeta("my-secret-token");

        httpClient.get("/server/config/get", {responseType: "text"}).subscribe();

        const req = httpMock.expectOne("/server/config/get");
        expect(req.request.headers.get("Authorization")).toBe("Bearer my-secret-token");
        req.flush("ok");
    });

    it("should not add Authorization header when token is empty", () => {
        setupWithMeta("");

        httpClient.get("/server/config/get", {responseType: "text"}).subscribe();

        const req = httpMock.expectOne("/server/config/get");
        expect(req.request.headers.has("Authorization")).toBeFalse();
        req.flush("ok");
    });

    it("should not add Authorization header when meta tag is missing", () => {
        setupWithMeta(null);

        httpClient.get("/server/config/get", {responseType: "text"}).subscribe();

        const req = httpMock.expectOne("/server/config/get");
        expect(req.request.headers.has("Authorization")).toBeFalse();
        req.flush("ok");
    });

    it("should preserve existing request headers", () => {
        setupWithMeta("tok");

        httpClient.get("/server/config/get", {
            responseType: "text",
            headers: {"X-Custom": "value"}
        }).subscribe();

        const req = httpMock.expectOne("/server/config/get");
        expect(req.request.headers.get("Authorization")).toBe("Bearer tok");
        expect(req.request.headers.get("X-Custom")).toBe("value");
        req.flush("ok");
    });

    it("should cache the token and not re-read meta tag on each request", () => {
        setupWithMeta("cached-token");

        // First request
        httpClient.get("/server/config/get", {responseType: "text"}).subscribe();
        const req1 = httpMock.expectOne("/server/config/get");
        expect(req1.request.headers.get("Authorization")).toBe("Bearer cached-token");
        req1.flush("ok");

        // Change the meta tag (simulating a change — shouldn't affect cached value)
        const meta = document.querySelector("meta[name=\"api-token\"]");
        if (meta) {
            meta.setAttribute("content", "new-token");
        }

        // Second request should still use cached token
        httpClient.get("/server/autoqueue/get", {responseType: "text"}).subscribe();
        const req2 = httpMock.expectOne("/server/autoqueue/get");
        expect(req2.request.headers.get("Authorization")).toBe("Bearer cached-token");
        req2.flush("ok");
    });

    it("should serve new token after _resetAuthInterceptorCache is called (token rotation)", () => {
        // Production coupling note:
        // _resetAuthInterceptorCache has no production caller in this codebase.
        // Token rotation is realized by a full page reload: the user navigates to /
        // or reloads, the browser re-fetches index.html, the Angular module re-instantiates,
        // and cachedToken / tokenRead reset to null / false. This test pins the mechanism
        // that a page reload relies on.
        setupWithMeta("token-v1");

        // First request — cache is fresh from setupWithMeta (which already called
        // _resetAuthInterceptorCache internally; no extra reset needed here)
        httpClient.get("/server/config/get", {responseType: "text"}).subscribe();
        const req1 = httpMock.expectOne("/server/config/get");
        expect(req1.request.headers.get("Authorization")).toBe("Bearer token-v1");
        req1.flush("ok");

        // Simulate token rotation: update the meta tag content and reset the cache.
        // This is the intentional mid-test reset — the single step that distinguishes
        // this test (rotation case) from the stale-cache test above (no reset case).
        const meta = document.querySelector("meta[name=\"api-token\"]");
        if (meta) {
            meta.setAttribute("content", "token-v2");
        }
        _resetAuthInterceptorCache();

        // Second request — should pick up the new token from the updated meta tag
        httpClient.get("/server/autoqueue/get", {responseType: "text"}).subscribe();
        const req2 = httpMock.expectOne("/server/autoqueue/get");
        expect(req2.request.headers.get("Authorization")).toBe("Bearer token-v2");
        req2.flush("ok");
    });

    it("should work with POST requests", () => {
        setupWithMeta("post-token");

        httpClient.post("/server/command/restart", null, {responseType: "text"}).subscribe();

        const req = httpMock.expectOne("/server/command/restart");
        expect(req.request.headers.get("Authorization")).toBe("Bearer post-token");
        req.flush("ok");
    });

    // D-10 destination case table (SEC-02): the app token must reach only this
    // origin's /server/ paths and never any other destination.

    it("should NOT send the token to the GitHub update-check URL (SEC-02, D-11)", () => {
        setupWithMeta("secret");
        expectNoAuth(GITHUB_LATEST_RELEASE_URL);
    });

    it("should send the token to an absolute same-origin /server/ URL", () => {
        setupWithMeta("secret");
        expectBearer(`${location.origin}/server/config/get`, "secret");
    });

    it("should NOT send the token to another external host", () => {
        setupWithMeta("secret");
        expectNoAuth("https://example.com/server/config/get");
    });

    it("should NOT send the token to a protocol-relative //host URL", () => {
        setupWithMeta("secret");
        expectNoAuth("//evil.example/server/config/get");
    });

    it("should NOT send the token to a backslash /\\host URL", () => {
        setupWithMeta("secret");
        expectNoAuth("/\\evil.example/server/config/get");
    });

    it("should NOT send the token to a look-alike host, without logging a warning", () => {
        setupWithMeta("secret");
        const warnSpy = spyOn(console, "warn");
        expectNoAuth(`${location.protocol}//${location.hostname}.evil.example/server/config/get`);
        expect(warnSpy).not.toHaveBeenCalled();
    });

    it("should NOT send the token to a userinfo host@evil URL, without logging a warning", () => {
        setupWithMeta("secret");
        const warnSpy = spyOn(console, "warn");
        expectNoAuth(`${location.protocol}//${location.host}@evil.example/server/config/get`);
        expect(warnSpy).not.toHaveBeenCalled();
    });

    it("should NOT send the token when the port does not match", () => {
        setupWithMeta("secret");
        expectNoAuth(`${location.protocol}//${location.hostname}:1/server/config/get`);
    });

    it("should NOT send the token when the scheme does not match", () => {
        setupWithMeta("secret");
        expectNoAuth(`https://${location.host}/server/config/get`);
    });

    it("should NOT send the token to a same-origin path outside /server/", () => {
        setupWithMeta("secret");
        expectNoAuth("/dashboard");
    });

    it("should NOT send the token to a /server/../ escape", () => {
        setupWithMeta("secret");
        expectNoAuth("/server/../dashboard");
    });

    it("should NOT send the token for an unparseable URL, and should log a generic warning", () => {
        setupWithMeta("secret");
        const warnSpy = spyOn(console, "warn");
        expectNoAuth("http://[");
        expect(warnSpy).toHaveBeenCalledTimes(1);
        const loggedArgs = JSON.stringify(warnSpy.calls.allArgs());
        expect(loggedArgs).not.toContain("secret");
        expect(loggedArgs).not.toContain("http://[");
    });

    it("should NOT send any Authorization header to the GitHub URL when no token is configured", () => {
        setupWithMeta("");
        expectNoAuth(GITHUB_LATEST_RELEASE_URL);
    });
});
