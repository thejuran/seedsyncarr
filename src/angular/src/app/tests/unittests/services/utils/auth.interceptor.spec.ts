import {TestBed} from "@angular/core/testing";
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {authInterceptor, _resetAuthInterceptorCache} from "../../../../services/utils/auth.interceptor";

describe("authInterceptor", () => {
    let httpClient: HttpClient;
    let httpMock: HttpTestingController;

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
        httpClient.get("/api/first", {responseType: "text"}).subscribe();
        const req1 = httpMock.expectOne("/api/first");
        expect(req1.request.headers.get("Authorization")).toBe("Bearer cached-token");
        req1.flush("ok");

        // Change the meta tag (simulating a change — shouldn't affect cached value)
        const meta = document.querySelector("meta[name=\"api-token\"]");
        if (meta) {
            meta.setAttribute("content", "new-token");
        }

        // Second request should still use cached token
        httpClient.get("/api/second", {responseType: "text"}).subscribe();
        const req2 = httpMock.expectOne("/api/second");
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
        httpClient.get("/api/first", {responseType: "text"}).subscribe();
        const req1 = httpMock.expectOne("/api/first");
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
        httpClient.get("/api/second", {responseType: "text"}).subscribe();
        const req2 = httpMock.expectOne("/api/second");
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
});
