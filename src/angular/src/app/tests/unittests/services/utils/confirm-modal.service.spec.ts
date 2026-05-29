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

    it("should sanitize HTML in title and body to prevent XSS", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "<script>alert(\"xss\")</script>",
            body: "<img src=x onerror=alert(1)> test"
        };

        service.confirm(options);
        tick();

        const modal = document.querySelector(".modal");
        const modalTitle = modal!.querySelector(".modal-title");
        const modalBodyP = modal!.querySelector(".modal-body p");

        // The literal tag strings should appear as text content, not as injected elements
        expect(modalTitle!.textContent).toContain("<script>");
        expect(modalBodyP!.textContent).toContain("<img src=x onerror=alert(1)>");

        // No actual script or img elements should be injected inside the modal
        expect(modal!.querySelector("script")).toBeNull();
        expect(modal!.querySelector("img")).toBeNull();
    }));

    it("should render HTML entities as literal text in body", fakeAsync(() => {
        const options: ConfirmModalOptions = {
            title: "Confirm",
            body: "Delete <b>file.txt</b> from server?"
        };

        service.confirm(options);
        tick();

        const modalBodyP = document.querySelector(".modal-body p");

        // The <b> tags should appear as literal text, not as a bold element
        expect(modalBodyP!.textContent).toContain("<b>file.txt</b>");

        // No actual <b> element should be created inside the modal body paragraph
        expect(modalBodyP!.querySelector("b")).toBeNull();
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
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
    });
});
