import {fakeAsync, TestBed, tick} from "@angular/core/testing";

import {ConfirmModalService, ConfirmModalOptions} from "../../../../services/utils/confirm-modal.service";

describe("Testing confirm modal service", () => {
    let service: ConfirmModalService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                ConfirmModalService
            ]
        });

        service = TestBed.inject(ConfirmModalService);
    });

    afterEach(() => {
        // Clean up any modals left in the DOM
        document.querySelectorAll(".modal").forEach(el => el.remove());
        document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
        document.body.classList.remove("modal-open");
    });

    it("should create an instance", () => {
        expect(service).toBeDefined();
    });

    it("should create modal with title and body", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test Title",
            body: "Test Body"
        };

        service.confirm(options);
        tick();

        const modal = document.querySelector(".modal");
        expect(modal).toBeTruthy();
        expect(modal!.querySelector(".modal-title")!.textContent).toBe("Test Title");
        expect(modal!.querySelector(".modal-body p")!.textContent).toBe("Test Body");
    }));

    it("should create backdrop", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const backdrop = document.querySelector(".modal-backdrop");
        expect(backdrop).toBeTruthy();
        expect(backdrop!.classList.contains("show")).toBe(true);
    }));

    it("should add modal-open class to body", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        expect(document.body.classList.contains("modal-open")).toBe(true);
    }));

    it("should resolve true when OK button is clicked", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        let result: boolean | undefined;
        service.confirm(options).then((r: boolean) => result = r);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLButtonElement;
        okButton!.click();
        tick();

        expect(result).toBe(true);
    }));

    it("should resolve false when Cancel button is clicked", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        let result: boolean | undefined;
        service.confirm(options).then((r: boolean) => result = r);
        tick();

        const cancelButton = document.querySelector("[data-action=\"cancel\"]") as HTMLButtonElement;
        cancelButton!.click();
        tick();

        expect(result).toBe(false);
    }));

    it("should resolve false when backdrop is clicked", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        let result: boolean | undefined;
        service.confirm(options).then((r: boolean) => result = r);
        tick();

        const modal = document.querySelector(".modal") as HTMLElement;
        modal!.click();
        tick();

        expect(result).toBe(false);
    }));

    it("should not resolve when modal content is clicked", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        let result: boolean | undefined;
        service.confirm(options).then((r: boolean) => result = r);
        tick();

        const modalContent = document.querySelector(".modal-content") as HTMLElement;
        modalContent!.click();
        tick();

        expect(result).toBeUndefined();
    }));

    it("should remove modal and backdrop after closing", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLButtonElement;
        okButton!.click();
        tick();

        expect(document.querySelector(".modal")).toBeNull();
        expect(document.querySelector(".modal-backdrop")).toBeNull();
        expect(document.body.classList.contains("modal-open")).toBe(false);
    }));

    it("should use default button text", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]");
        const cancelButton = document.querySelector("[data-action=\"cancel\"]");

        expect(okButton!.textContent).toBe("OK");
        expect(cancelButton!.textContent).toBe("Cancel");
    }));

    it("should use custom button text", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            okBtn: "Delete",
            cancelBtn: "Keep"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]");
        const cancelButton = document.querySelector("[data-action=\"cancel\"]");

        expect(okButton!.textContent).toBe("Delete");
        expect(cancelButton!.textContent).toBe("Keep");
    }));

    it("should use default button classes", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]");
        const cancelButton = document.querySelector("[data-action=\"cancel\"]");

        expect(okButton!.classList.contains("btn")).toBe(true);
        expect(okButton!.classList.contains("btn-primary")).toBe(true);
        expect(cancelButton!.classList.contains("btn")).toBe(true);
        expect(cancelButton!.classList.contains("btn-secondary")).toBe(true);
    }));

    it("should use custom button classes", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            okBtnClass: "btn btn-danger",
            cancelBtnClass: "btn btn-outline-secondary"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]");
        const cancelButton = document.querySelector("[data-action=\"cancel\"]");

        expect(okButton!.classList.contains("btn-danger")).toBe(true);
        expect(cancelButton!.classList.contains("btn-outline-secondary")).toBe(true);
    }));

    it("should not show skip message when skipCount is not provided", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const modalBody = document.querySelector(".modal-body");
        expect(modalBody!.querySelectorAll("p").length).toBe(1);
    }));

    it("should not show skip message when skipCount is 0", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            skipCount: 0
        };

        service.confirm(options);
        tick();

        const modalBody = document.querySelector(".modal-body");
        expect(modalBody!.querySelectorAll("p").length).toBe(1);
    }));

    it("should show skip message for single file", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            skipCount: 1
        };

        service.confirm(options);
        tick();

        const modalBody = document.querySelector(".modal-body");
        const paragraphs = modalBody!.querySelectorAll("p");
        expect(paragraphs.length).toBe(2);
        expect(paragraphs[1].textContent).toContain("1 file will be skipped");
    }));

    it("should show skip message for multiple files", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            skipCount: 5
        };

        service.confirm(options);
        tick();

        const modalBody = document.querySelector(".modal-body");
        const paragraphs = modalBody!.querySelectorAll("p");
        expect(paragraphs.length).toBe(2);
        expect(paragraphs[1].textContent).toContain("5 files will be skipped");
    }));

    it("should style skip message with muted text", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test",
            skipCount: 3
        };

        service.confirm(options);
        tick();

        const skipMessage = document.querySelectorAll(".modal-body p")[1];
        expect(skipMessage!.classList.contains("text-muted")).toBe(true);
        expect(skipMessage!.classList.contains("small")).toBe(true);
    }));


    it("should focus cancel button when modal opens", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const cancelButton = document.querySelector("[data-action=\"cancel\"]") as HTMLElement;
        expect(document.activeElement).toBe(cancelButton);
    }));

    it("should close modal on Escape key", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        let result: boolean | undefined;
        service.confirm(options).then((r: boolean) => result = r);
        tick();

        const modal = document.querySelector(".modal") as HTMLElement;
        modal!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        tick();

        expect(result).toBe(false);
        expect(document.querySelector(".modal")).toBeNull();
    }));

    it("should trap Tab focus within modal", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLElement;
        const cancelButton = document.querySelector("[data-action=\"cancel\"]") as HTMLElement;
        const modal = document.querySelector(".modal") as HTMLElement;

        // Move focus to ok button, then Tab should wrap to cancel button
        okButton!.focus();
        modal!.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));

        expect(document.activeElement).toBe(cancelButton);
    }));

    it("should trap Shift+Tab focus within modal", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLElement;
        const cancelButton = document.querySelector("[data-action=\"cancel\"]") as HTMLElement;
        const modal = document.querySelector(".modal") as HTMLElement;

        // Cancel button is focused by default; Shift+Tab should wrap to ok button
        cancelButton!.focus();
        modal!.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }));

        expect(document.activeElement).toBe(okButton);
    }));

    it("should restore focus to previously focused element on close", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        // Create a temporary button, append to body, and focus it
        const triggerButton = document.createElement("button");
        document.body.appendChild(triggerButton);
        triggerButton.focus();
        expect(document.activeElement).toBe(triggerButton);

        service.confirm(options).then(() => undefined);
        tick();

        // Focus has moved to modal cancel button
        const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLButtonElement;
        okButton!.click();
        tick();

        expect(document.activeElement).toBe(triggerButton);

        // Clean up
        document.body.removeChild(triggerButton);
    }));

    it("should set aria-modal attribute on modal element", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const modal = document.querySelector(".modal");
        expect(modal!.getAttribute("aria-modal")).toBe("true");
    }));

    it("should set aria-labelledby on modal element", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Test",
            body: "Test"
        };

        service.confirm(options);
        tick();

        const modal = document.querySelector(".modal");
        expect(modal!.getAttribute("aria-labelledby")).toBe("confirm-modal-title");
        expect(modal!.querySelector("#confirm-modal-title")).toBeTruthy();
    }));

    describe("XSS / escapeHtml coverage", () => {
        // Helper: access ConfirmModalService.escapeHtml (private static) via type cast to any.
        // Casting the class constructor to any is the idiomatic TypeScript test pattern for
        // private static helpers (PATTERNS.md section F). The cast is on the class, not on a
        // nullable value, so no runtime null-guard is needed — calling a class method cannot
        // null-fault (see 98-RESEARCH.md Area 1).
        function escape(s: string): string {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (ConfirmModalService as any).escapeHtml(s);
        }

        // Helper: walk the entire subtree rooted at `root` and return true if any element
        // carries an attribute whose name starts with "on". CSS has no attribute-name-prefix
        // selector ([on*=...] matches attribute VALUES), so walking element.attributes is the
        // only correct approach (RESEARCH.md Pattern 4, Area 4). Used in D-03/D-05 tests below.
        function hasOnAttribute(root: Element): boolean {
            const allElements = Array.from(root.querySelectorAll("*"));
            allElements.push(root);
            for (const el of allElements) {
                for (let i = 0; i < el.attributes.length; i++) {
                    if (el.attributes[i].name.startsWith("on")) {
                        return true;
                    }
                }
            }
            return false;
        }

        // Scans the modal subtree for any href/src attribute carrying a javascript: URL.
        // Extracted to a describe-scope helper (mirrors hasOnAttribute) so the four D-03
        // end-to-end tests share one javascript:-URL check instead of duplicating it.
        function hasJavascriptUrl(root: Element): boolean {
            return Array.from(root.querySelectorAll("[href],[src]")).some(el =>
                (el.getAttribute("href") || "").toLowerCase().startsWith("javascript:") ||
                (el.getAttribute("src") || "").toLowerCase().startsWith("javascript:")
            );
        }

        // D-04: Direct escapeHtml unit tests (synchronous — escapeHtml is a pure function,
        // no fakeAsync needed).

        it("should escape each metacharacter to its HTML entity", () => {
            expect(escape("&")).toBe("&amp;");
            expect(escape("<")).toBe("&lt;");
            expect(escape(">")).toBe("&gt;");
            expect(escape("\"")).toBe("&quot;");
            expect(escape("'")).toBe("&#039;");
        });

        it("should replace & first so entity ampersands are not double-escaped", () => {
            // Input: raw '<' (U+003C). After correct &-first escaping: '&lt;' (5 chars).
            // If '&' were NOT replaced first, the '&' introduced by escaping '<' would be
            // re-escaped, yielding '&amp;lt;' (8 chars) — the double-escape regression.
            expect(escape("<")).toBe("&lt;");
            expect(escape("&")).toBe("&amp;");
            // Combined: '<&>' should become '&lt;&amp;&gt;' (not '&amp;lt;&amp;amp;&amp;gt;')
            expect(escape("<&>")).toBe("&lt;&amp;&gt;");
        });

        it("should handle a combined attacker payload correctly", () => {
            expect(escape("<script>alert(\"xss\")</script>"))
                .toBe("&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;");
        });

        // D-01 documenting test: the escape set is intentionally limited to &<>"'.
        // Backtick, U+2028, U+2029, and null byte are NOT escaped because this service
        // renders into exactly two HTML contexts:
        //   (a) element content (<h5>, <p>, button text)  — backtick is not a metacharacter here
        //   (b) double-quoted class attribute              — backtick cannot close a double-quoted attr
        // U+2028/U+2029 are JavaScript line-separators exploitable only inside <script> sinks
        // (none present). Null byte is normalized/ignored by the HTML5 parser in these contexts.
        // This omission is a locked decision (D-01 — see 98-CONTEXT.md); this test records the
        // reasoning so it reads as intentional, not an oversight.
        it("should NOT escape backtick / U+2028 / U+2029 / null byte (not XSS-exploitable in service's HTML contexts, per D-01)", () => {
            // Backtick: not a metacharacter in element content or double-quoted attributes.
            expect(escape("`")).toBe("`");
            // U+2028 (line separator): only exploitable in <script> context, which this service lacks.
            expect(escape("\u2028")).toBe("\u2028");
            // U+2029 (paragraph separator): same rationale as U+2028.
            expect(escape("\u2029")).toBe("\u2029");
            // Null byte (U+0000): HTML5 parser normalizes it; not exploitable in these contexts.
            expect(escape("\0")).toBe("\0");
        });

        // D-03 / D-05: End-to-end DOM XSS tests for all six escaped inputs.
        //
        // Each test follows the canonical idiom (spec lines 29-42):
        //   service.confirm(options) \u2192 tick() \u2192 const modal = document.querySelector(".modal")!
        // Four assertion layers per test (D-03):
        //   (a) modal.querySelector("script") is null          \u2014 no script element parsed
        //   (b) hasOnAttribute(modal) is false                 \u2014 no on* attribute in subtree
        //   (c) no [href]/[src] value starts with "javascript:"
        //   (d) modal.innerHTML contains the escaped entity string
        //       (proves entity encoding, not silent browser stripping \u2014 Pitfall 1)
        //
        // Supersedes the two former partial XSS tests (spec lines 300-320 and 322-338, D-06).
        // Their unique textContent assertions are preserved in the title and body blocks below.

        // --- Element-content inputs (title, body, okBtn, cancelBtn) ---

        it("should produce no executable markup when title contains a script payload",
            fakeAsync(() => {
                service.confirm({
                    title: "<script>alert(\"xss\")</script>",
                    body: "safe body"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const modalTitle = modal.querySelector(".modal-title")!;

                // (a) No parsed script element
                expect(modal.querySelector("script")).toBeNull();
                // (b) No on* event-handler attribute anywhere in the subtree
                expect(hasOnAttribute(modal)).toBe(false);
                // (c) No javascript: URL
                expect(hasJavascriptUrl(modal)).toBe(false);
                // (d) Entity-encoded in raw innerHTML \u2014 proves escaping, not silent stripping
                expect(modal.innerHTML).toContain("&lt;script&gt;");
                expect(modal.innerHTML).toContain("&lt;/script&gt;");
                // Preserved from superseded test (line 314): browser-decoded visible text
                expect(modalTitle.textContent).toContain("<script>");
            }));

        it("should produce no executable markup when body contains a script payload",
            fakeAsync(() => {
                service.confirm({
                    title: "safe title",
                    body: "<script>alert(1)</script>"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const modalBodyP = modal.querySelector(".modal-body p")!;

                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
                expect(hasJavascriptUrl(modal)).toBe(false);
                expect(modal.innerHTML).toContain("&lt;script&gt;");
                expect(modal.innerHTML).toContain("&lt;/script&gt;");
                // Preserved from superseded test (line 315): img-based onerror payload visible
                // as literal text (mirrors the former textContent assertion for body)
                expect(modalBodyP.textContent).toContain("<script>");
            }));

        it("should produce no executable markup when body contains an img onerror payload",
            fakeAsync(() => {
                service.confirm({
                    title: "safe title",
                    body: "<img src=x onerror=alert(1)> test"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const modalBodyP = modal.querySelector(".modal-body p")!;

                expect(modal.querySelector("img")).toBeNull();
                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
                expect(modal.innerHTML).toContain("&lt;img");
                // Preserved from superseded test (line 315): decoded visible text
                expect(modalBodyP.textContent).toContain("<img src=x onerror=alert(1)>");
            }));

        it("should render HTML-tagged body text as escaped entities, not live elements",
            fakeAsync(() => {
                service.confirm({
                    title: "Confirm",
                    body: "Delete <b>file.txt</b> from server?"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const modalBodyP = modal.querySelector(".modal-body p")!;

                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
                // Entity-encoded \u2014 the '<' was escaped
                expect(modal.innerHTML).toContain("&lt;b&gt;");
                // Preserved from superseded test (line 334): visible text contains literal tags
                expect(modalBodyP.textContent).toContain("<b>file.txt</b>");
                // No live <b> element created (preserved from line 337)
                expect(modalBodyP.querySelector("b")).toBeNull();
            }));

        it("should produce no executable markup when okBtn contains a script payload",
            fakeAsync(() => {
                service.confirm({
                    title: "t",
                    body: "b",
                    okBtn: "<script>alert(1)</script>"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const okButton = modal.querySelector("[data-action=\"ok\"]")!;

                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
                expect(hasJavascriptUrl(modal)).toBe(false);
                expect(modal.innerHTML).toContain("&lt;script&gt;");
                // Payload rendered as inert button text (visible text contains literal tags)
                expect(okButton.textContent).toContain("<script>");
            }));

        it("should produce no executable markup when cancelBtn contains a script payload",
            fakeAsync(() => {
                service.confirm({
                    title: "t",
                    body: "b",
                    cancelBtn: "<script>alert(1)</script>"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const cancelButton = modal.querySelector("[data-action=\"cancel\"]")!;

                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
                expect(hasJavascriptUrl(modal)).toBe(false);
                expect(modal.innerHTML).toContain("&lt;script&gt;");
                // Payload rendered as inert button text
                expect(cancelButton.textContent).toContain("<script>");
            }));

        // D-02: skipCount-exemption documenting test and runtime-boundary probe.
        //
        // Success-criterion #3 audit (all six escaped inputs + one exempt numeric site):
        //   String inputs routed through escapeHtml before innerHTML (source lines 51-56):
        //     title, body, okBtn, okBtnClass, cancelBtn, cancelBtnClass
        //   skipMessage (source lines 59-64) is the ONLY un-escaped interpolation site.
        //   It interpolates only `options.skipCount` (TypeScript type: number | undefined)
        //   guarded by `if (skipCount && skipCount > 0)`. A real number cannot carry HTML
        //   metacharacters, so no attacker-controlled string reaches innerHTML through it.
        //   Routing skipCount through escapeHtml would be a misleading no-op (D-02).

        it("should leave skipCount interpolation un-escaped because skipCount is a " +
           "TypeScript number, not an attacker-controlled string (D-02 — only " +
           "bypass-exempt site, no string can reach it)", fakeAsync(() => {
            service.confirm({ title: "t", body: "b", skipCount: 3 });
            tick();

            const modal = document.querySelector(".modal")!;
            const skipP = modal.querySelectorAll(".modal-body p")[1]!;

            // The value rendered is the numeric literal '3', not a string from attacker input.
            expect(skipP.textContent).toContain("3 file");
            expect(skipP.textContent).toContain("will be skipped");
            // The skipCount path injects no executable markup
            expect(modal.querySelector("script")).toBeNull();
            expect(hasOnAttribute(modal)).toBe(false);
        }));

        // Runtime-boundary probe (codex adversarial review, 2026-05-29):
        // TypeScript types are erased at runtime. The service guards skipCount only with a
        // truthiness and `> 0` check, then interpolates `${options.skipCount}` un-escaped.
        // A caller that defeats the TypeScript type by passing a coercible object whose
        // toString() returns markup is the one theoretical path that bypasses escaping at
        // this numeric site. This test PINS the service's actual rendered behavior so the
        // runtime contract is documented, not assumed.
        //
        // D-02's "no attacker string reaches this site" is scoped to trusted TypeScript
        // callers (all current call sites pass real numbers — verified by grep). Runtime
        // hardening (coerce Number(skipCount) or escape the string) is a PUBLIC-BEHAVIOR
        // change deferred to v1.4.0 per CONTEXT.md. Do NOT modify confirm-modal.service.ts.
        it("should pin the runtime behavior of skipCount when a caller defeats the " +
           "TypeScript number type with a coercible object (D-02 scope: type-safety " +
           "guards this in trusted TS callers; runtime hardening deferred to v1.4.0)",
            fakeAsync(() => {
                // The object satisfies the `if (skipCount && skipCount > 0)` guard via
                // valueOf(), causing skipMessage to be emitted. The template literal
                // `${options.skipCount}` then calls toString(), which returns raw HTML markup.
                // The browser's HTML parser processes that markup when it is assigned to
                // innerHTML — so the <img> element IS created in the rendered DOM.
                // This test asserts exactly that observed runtime reality.
                const coercibleSkipCount = {
                    valueOf: (): number => 1,
                    toString: (): string => "<img src=x onerror=\"alert(1)\">"
                } as unknown as number;

                service.confirm({ title: "t", body: "b", skipCount: coercibleSkipCount });
                tick();

                const modal = document.querySelector(".modal")!;
                // The second .modal-body p is rendered because valueOf() satisfies the guard
                const skipP = modal.querySelectorAll(".modal-body p")[1]!;

                // Observed reality: toString() markup reaches innerHTML un-escaped.
                // The <img> element IS parsed and exists in the DOM — the service does not
                // sanitize this path at runtime. (Safe in production: all call sites use
                // real number literals. Hardening = v1.4.0.)
                expect(skipP.querySelector("img")).not.toBeNull();
                // The skip paragraph contains the "file" suffix from the template literal
                // (plural "s" because strict-equality `=== 1` fails for an object)
                expect(skipP.textContent).toContain("files will be skipped");
            }));

        // --- Class-attribute inputs (okBtnClass, cancelBtnClass) ---
        //
        // Payload: "btn\" onmouseover=\"alert(1)" attempts to close the double-quoted class
        // attribute and inject an event-handler attribute. escapeHtml encodes '"' to '&quot;',
        // keeping the payload inside the class value string (Pitfall 4, RESEARCH.md).

        it("should neutralize an attribute-breakout payload in okBtnClass", fakeAsync(() => {
            service.confirm({
                title: "t",
                body: "b",
                okBtnClass: "btn\" onmouseover=\"alert(1)"
            });
            tick();

            const modal = document.querySelector(".modal")!;
            const okButton = modal.querySelector("[data-action=\"ok\"]")!;

            // Primary DOM assertion: no onmouseover attribute on the button
            expect(okButton.getAttribute("onmouseover")).toBeNull();
            // Subtree walk: no on* attribute anywhere
            expect(hasOnAttribute(modal)).toBe(false);
            // String assertion: the '"' was encoded, trapping the payload inside class value
            expect(modal.innerHTML).toContain("&quot;");
            expect(modal.querySelector("script")).toBeNull();
        }));

        it("should neutralize an attribute-breakout payload in cancelBtnClass",
            fakeAsync(() => {
                service.confirm({
                    title: "t",
                    body: "b",
                    cancelBtnClass: "btn\" onmouseover=\"alert(1)"
                });
                tick();

                const modal = document.querySelector(".modal")!;
                const cancelButton = modal.querySelector("[data-action=\"cancel\"]")!;

                // Primary DOM assertion: no onmouseover attribute on the button
                expect(cancelButton.getAttribute("onmouseover")).toBeNull();
                // Subtree walk: no on* attribute anywhere
                expect(hasOnAttribute(modal)).toBe(false);
                // String assertion: the '"' was encoded
                expect(modal.innerHTML).toContain("&quot;");
                expect(modal.querySelector("script")).toBeNull();
            }));
    });
});
