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

    describe("XSS / structural DOM safety coverage (BUG-01)", () => {
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

        // Scans the modal subtree for any href/src attribute carrying a dangerous-scheme URL.
        // Extracted to a describe-scope helper (mirrors hasOnAttribute) so the four D-03
        // end-to-end tests share one dangerous-URL check instead of duplicating it.
        //
        // Checks the full set of script-executing schemes, not just javascript: — a regression
        // that emitted a data:text/html or vbscript: URL would otherwise slip past this assertion
        // and leave the test green (CodeQL js/incomplete-url-scheme-check). Browsers ignore
        // leading whitespace/control chars before the scheme, so those are stripped before the
        // prefix test to match how the URL would actually be evaluated.
        const DANGEROUS_URL_SCHEMES = ["javascript:", "data:", "vbscript:"];
        // eslint-disable-next-line no-control-regex -- intentional: strip leading control chars to mirror browser scheme parsing
        const LEADING_WS_OR_CONTROL = /^[\u0000-\u0020]+/;
        function hasDangerousUrl(root: Element): boolean {
            const isDangerous = (raw: string | null): boolean => {
                // Strip leading whitespace + C0 control chars (matches how browsers parse the
                // scheme), then compare case-insensitively against all script-executing schemes.
                const normalized = (raw || "").replace(LEADING_WS_OR_CONTROL, "").toLowerCase();
                return DANGEROUS_URL_SCHEMES.some(scheme => normalized.startsWith(scheme));
            };
            return Array.from(root.querySelectorAll("[href],[src]")).some(el =>
                isDangerous(el.getAttribute("href")) || isDangerous(el.getAttribute("src"))
            );
        }

        // BUG-01 / D-01-D-05: End-to-end DOM XSS tests for all six inputs.
        // Modal content is built structurally via Renderer2 createText() (D-01/D-02) —
        // user strings become text nodes and are never parsed as HTML by the browser.
        //
        // Each test follows the canonical idiom:
        //   service.confirm(options) -> tick() -> const modal = document.querySelector(".modal")!
        // Assertion layers per test:
        //   (a) modal.querySelector("script") is null      -- no script element parsed
        //   (b) hasOnAttribute(modal) is false             -- no on* attribute in subtree
        //   (c) no [href]/[src] value starts with "javascript:"
        //   (d) textContent contains the literal payload   -- visible text (structural outcome)
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
                expect(hasDangerousUrl(modal)).toBe(false);
                // (d) Literal payload visible as text (structural outcome)
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
                expect(hasDangerousUrl(modal)).toBe(false);
                // Literal payload visible as text (structural outcome)
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
                // Literal payload visible as text (structural outcome)
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
                // Literal payload visible as text (structural outcome)
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
                expect(hasDangerousUrl(modal)).toBe(false);
                // Payload rendered as inert button text (structural outcome)
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
                expect(hasDangerousUrl(modal)).toBe(false);
                // Payload rendered as inert button text (structural outcome)
                expect(cancelButton.textContent).toContain("<script>");
            }));

        // BUG-01 D-02/D-04: skipCount companion test and D-05 runtime-boundary probe.
        //
        // After BUG-01: all string inputs (title, body, okBtn, okBtnClass, cancelBtn,
        // cancelBtnClass) are rendered via Renderer2 createText() — structural text nodes.
        // skipCount is coerced with Number() (D-04) before the guard, then used as a
        // primitive number in the template literal. A real numeric skipCount still renders
        // exactly as before. A toString()-overriding object is blocked by the coercion.

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

        // D-05 runtime-boundary probe (BUG-01 D-04/D-05, shipped Phase 103):
        // Phase 103 delivers Number() coercion for skipCount (D-04). The prior deferral
        // comment from slice-1 is now resolved — this probe is inverted to assert the
        // hardened behavior. After D-04: Number(coercibleObject) = 1 (via valueOf()),
        // the toString() method is NEVER called, and no markup reaches the DOM.
        // The skip paragraph is also a Renderer2 text node (D-01), doubly safe.
        it("should harden skipCount against toString()-overriding objects via Number() coercion (BUG-01 D-04/D-05)",
            fakeAsync(() => {
                // Number({valueOf: ()=>1, toString: ()=>"<img...>"}) === 1 (valueOf path).
                // toString() is never called because Number() returns a primitive number.
                // The skip paragraph renders "1 file will be skipped" as a text node.
                const coercibleSkipCount = {
                    valueOf: (): number => 1,
                    toString: (): string => "<img src=x onerror=\"alert(1)\">"
                } as unknown as number;

                service.confirm({ title: "t", body: "b", skipCount: coercibleSkipCount });
                tick();

                const modal = document.querySelector(".modal")!;
                // The second .modal-body p is rendered because Number(obj) = 1, satisfies guard
                const skipP = modal.querySelectorAll(".modal-body p")[1]!;

                // After D-04: toString() markup does NOT reach the DOM.
                // No <img> element is created — Number() coercion blocks the attack.
                expect(skipP.querySelector("img")).toBeNull();
                // Singular "1 file" because Number(obj) === 1 (primitive, strict-equality holds)
                expect(skipP.textContent).toContain("1 file will be skipped");
                expect(modal.querySelector("script")).toBeNull();
                expect(hasOnAttribute(modal)).toBe(false);
            }));

        // --- Class-attribute inputs (okBtnClass, cancelBtnClass) ---
        //
        // Payload: "btn\" onmouseover=\"alert(1)" attempts to close the double-quoted class
        // attribute and inject an event-handler attribute. After BUG-01, class strings are
        // applied via renderer.setAttribute(button, "class", value) — Renderer2 bypasses the
        // HTML parser, so the breakout payload becomes a literal (invalid) class value,
        // never a new attribute. The onmouseover attribute must not appear on the button.

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
            // Structural: breakout payload is inert (Renderer2 setAttribute bypasses HTML parser)
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
                // Structural: breakout payload is inert (Renderer2 setAttribute bypasses HTML parser)
                expect(modal.querySelector("script")).toBeNull();
            }));
    });
});
