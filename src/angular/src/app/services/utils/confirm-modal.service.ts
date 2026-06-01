import {Injectable, Renderer2, RendererFactory2} from "@angular/core";

export interface ConfirmModalOptions {
    title: string;
    body: string;
    okBtn?: string;
    okBtnClass?: string;
    cancelBtn?: string;
    cancelBtnClass?: string;
    skipCount?: number;  // Number of items that will be skipped (for bulk actions)
}

// Fully-resolved inputs for buildModalContent — all defaults already applied and skipCount
// coerced to a primitive number. Named fields (vs positional args) make an accidental
// transposition of the interchangeable string fields a compile-time error.
interface ModalContentOptions {
    title: string;
    body: string;
    okBtn: string;
    okBtnClass: string;
    cancelBtn: string;
    cancelBtnClass: string;
    skipCount: number;
}

@Injectable({
    providedIn: "root"
})
export class ConfirmModalService {
    private renderer: Renderer2;
    private modalElement: HTMLElement | null = null;
    private backdropElement: HTMLElement | null = null;
    private previouslyFocusedElement: HTMLElement | null = null;
    private keydownHandler: ((event: KeyboardEvent) => void) | null = null;

    constructor(rendererFactory: RendererFactory2) {
        this.renderer = rendererFactory.createRenderer(null, null);
    }

    confirm(options: ConfirmModalOptions): Promise<boolean> {
        return new Promise<boolean>((resolve) => {
            this.createModal(options, resolve);
        });
    }

    private createModal(options: ConfirmModalOptions, resolve: (value: boolean) => void): void {
        // Save previously focused element for focus restoration on close
        this.previouslyFocusedElement = document.activeElement as HTMLElement;

        const okBtn = options.okBtn || "OK";
        const okBtnClass = options.okBtnClass || "btn btn-primary";
        const cancelBtn = options.cancelBtn || "Cancel";
        const cancelBtnClass = options.cancelBtnClass || "btn btn-secondary";

        // Coerce skipCount to a primitive number (D-04 / BUG-01):
        // Number() calls valueOf() on the argument, yielding a primitive before the guard.
        // A toString()-overriding object cannot inject markup because n is a primitive number
        // after coercion, and ${n} in the template literal calls Number.prototype.toString.
        const n = Number(options.skipCount);

        // Create backdrop
        this.backdropElement = this.renderer.createElement("div");
        this.renderer.addClass(this.backdropElement, "modal-backdrop");
        this.renderer.addClass(this.backdropElement, "fade");
        this.renderer.addClass(this.backdropElement, "show");
        // Explicit positioning ensures backdrop covers viewport and stacks above sidebar (z-index: 300)
        this.renderer.setStyle(this.backdropElement, "position", "fixed");
        this.renderer.setStyle(this.backdropElement, "top", "0");
        this.renderer.setStyle(this.backdropElement, "left", "0");
        this.renderer.setStyle(this.backdropElement, "width", "100%");
        this.renderer.setStyle(this.backdropElement, "height", "100%");
        this.renderer.setStyle(this.backdropElement, "z-index", "1050");
        this.renderer.appendChild(document.body, this.backdropElement);

        // Create modal
        this.modalElement = this.renderer.createElement("div");
        this.renderer.addClass(this.modalElement, "modal");
        this.renderer.addClass(this.modalElement, "fade");
        this.renderer.addClass(this.modalElement, "show");
        // Explicit positioning ensures modal covers viewport and stacks above sidebar (z-index: 300)
        // without relying on Bootstrap's .modal CSS which may not be applied
        this.renderer.setStyle(this.modalElement, "position", "fixed");
        this.renderer.setStyle(this.modalElement, "top", "0");
        this.renderer.setStyle(this.modalElement, "left", "0");
        this.renderer.setStyle(this.modalElement, "width", "100%");
        this.renderer.setStyle(this.modalElement, "height", "100%");
        this.renderer.setStyle(this.modalElement, "display", "block");
        this.renderer.setStyle(this.modalElement, "z-index", "1055");
        this.renderer.setStyle(this.modalElement, "overflow-y", "auto");
        this.renderer.setAttribute(this.modalElement, "tabindex", "-1");
        this.renderer.setAttribute(this.modalElement, "role", "dialog");
        this.renderer.setAttribute(this.modalElement, "aria-modal", "true");
        this.renderer.setAttribute(this.modalElement, "aria-labelledby", "confirm-modal-title");

        // Build modal content tree with Renderer2 structural construction (BUG-01 / D-01):
        // Each user-supplied string is passed to renderer.createText() which returns a DOM
        // Text node. Text nodes cannot be parsed as HTML by the browser — a payload such as
        // <script>alert(1)</script> renders as inert visible text and creates no child elements.
        // This is a browser-level structural guarantee, strictly stronger than entity-escaping.
        const modalContent = this.buildModalContent({
            title: options.title,
            body: options.body,
            okBtn,
            okBtnClass,
            cancelBtn,
            cancelBtnClass,
            skipCount: n
        });
        this.renderer.appendChild(this.modalElement, modalContent);

        this.renderer.appendChild(document.body, this.modalElement);
        this.renderer.addClass(document.body, "modal-open");

        // Handle button clicks
        const cancelButton = this.modalElement!.querySelector("[data-action=\"cancel\"]") as HTMLElement;
        const okButton = this.modalElement!.querySelector("[data-action=\"ok\"]") as HTMLElement;

        const closeModal = (result: boolean): void => {
            this.destroyModal();
            resolve(result);
        };

        cancelButton.addEventListener("click", () => closeModal(false));
        okButton.addEventListener("click", () => closeModal(true));

        // Close on backdrop click
        this.modalElement!.addEventListener("click", (event) => {
            if (event.target === this.modalElement) {
                closeModal(false);
            }
        });

        // Focus trap: Tab/Shift+Tab always cycle between cancelButton and okButton; Escape closes modal
        this.keydownHandler = (event: KeyboardEvent): void => {
            if (event.key === "Escape") {
                event.preventDefault();
                closeModal(false);
            } else if (event.key === "Tab") {
                event.preventDefault();
                if (event.shiftKey) {
                    // Shift+Tab: always move to the other button
                    if (document.activeElement === cancelButton) {
                        okButton.focus();
                    } else {
                        cancelButton.focus();
                    }
                } else {
                    // Tab: always move to the other button
                    if (document.activeElement === okButton) {
                        cancelButton.focus();
                    } else {
                        okButton.focus();
                    }
                }
            }
        };
        this.modalElement!.addEventListener("keydown", this.keydownHandler);

        // Focus the cancel button (safe default) after DOM has settled
        setTimeout(() => cancelButton.focus(), 0);
    }

    /**
     * Build the inner modal content tree using Renderer2 structural construction (BUG-01 D-01).
     *
     * Every user-supplied string is passed to renderer.createText() — which returns a DOM
     * Text node. Text nodes are NEVER parsed as HTML by the browser. No escaping routine is
     * needed or used; the raw (un-escaped) string is correct here. Passing a pre-escaped
     * string would render literal entities (e.g. "&lt;") as visible text — Pitfall 1.
     *
     * Class strings are applied via renderer.setAttribute(el, "class", value), which assigns
     * the attribute structurally without HTML parsing. A breakout payload such as
     * `btn" onmouseover="alert(1)` becomes an inert (possibly invalid) class value — the
     * quote character cannot terminate an HTML attribute because no HTML parser is involved.
     *
     * Returns the fully assembled modal-dialog element, ready to be appended to modalElement
     * before the querySelector wiring (immediately after the call site) executes.
     *
     * Accepts a single options object rather than positional args: all the string fields are
     * interchangeable by type, so a named-field object makes an accidental transposition
     * (e.g. okBtn vs okBtnClass) a compile-time error instead of a silent runtime defect.
     */
    private buildModalContent(content: ModalContentOptions): HTMLElement {
        const {title, body, okBtn, okBtnClass, cancelBtn, cancelBtnClass, skipCount: n} = content;
        // modal-dialog
        const modalDialog = this.renderer.createElement("div");
        this.renderer.addClass(modalDialog, "modal-dialog");
        this.renderer.setAttribute(modalDialog, "role", "document");

        const modalContent = this.renderer.createElement("div");
        this.renderer.addClass(modalContent, "modal-content");

        // modal-header
        const modalHeader = this.renderer.createElement("div");
        this.renderer.addClass(modalHeader, "modal-header");
        const h5 = this.renderer.createElement("h5");
        this.renderer.addClass(h5, "modal-title");
        this.renderer.setAttribute(h5, "id", "confirm-modal-title");
        // Pass raw title — createText() makes it an inert Text node (never parsed as HTML)
        this.renderer.appendChild(h5, this.renderer.createText(title));
        this.renderer.appendChild(modalHeader, h5);

        // modal-body
        const modalBody = this.renderer.createElement("div");
        this.renderer.addClass(modalBody, "modal-body");
        const bodyP = this.renderer.createElement("p");
        this.renderer.appendChild(bodyP, this.renderer.createText(body));
        this.renderer.appendChild(modalBody, bodyP);

        // Optional skip-count paragraph (D-04): n is a primitive number after Number() coercion,
        // so ${n} calls Number.prototype.toString — never the object's custom toString.
        if (Number.isFinite(n) && n > 0) {
            const plural = n === 1 ? "" : "s";
            const skipP = this.renderer.createElement("p");
            this.renderer.addClass(skipP, "text-muted");
            this.renderer.addClass(skipP, "small");
            this.renderer.addClass(skipP, "mt-2");
            this.renderer.appendChild(skipP, this.renderer.createText(
                `${n} file${plural} will be skipped (not eligible for this action)`
            ));
            this.renderer.appendChild(modalBody, skipP);
        }

        // modal-footer
        const modalFooter = this.renderer.createElement("div");
        this.renderer.addClass(modalFooter, "modal-footer");

        // Cancel button (before OK per footer ordering convention)
        const cancelButton = this.renderer.createElement("button");
        this.renderer.setAttribute(cancelButton, "type", "button");
        // data-action="cancel" required for the querySelector wiring in createModal()
        this.renderer.setAttribute(cancelButton, "data-action", "cancel");
        // setAttribute bypasses HTML parser — breakout payloads become inert class values (D-03)
        this.renderer.setAttribute(cancelButton, "class", cancelBtnClass);
        this.renderer.appendChild(cancelButton, this.renderer.createText(cancelBtn));

        // OK button
        const okButton = this.renderer.createElement("button");
        this.renderer.setAttribute(okButton, "type", "button");
        // data-action="ok" required for the querySelector wiring in createModal()
        this.renderer.setAttribute(okButton, "data-action", "ok");
        this.renderer.setAttribute(okButton, "class", okBtnClass);
        this.renderer.appendChild(okButton, this.renderer.createText(okBtn));

        this.renderer.appendChild(modalFooter, cancelButton);
        this.renderer.appendChild(modalFooter, okButton);

        this.renderer.appendChild(modalContent, modalHeader);
        this.renderer.appendChild(modalContent, modalBody);
        this.renderer.appendChild(modalContent, modalFooter);
        this.renderer.appendChild(modalDialog, modalContent);

        return modalDialog;
    }

    private destroyModal(): void {
        if (this.modalElement) {
            if (this.keydownHandler) {
                this.modalElement.removeEventListener("keydown", this.keydownHandler);
                this.keydownHandler = null;
            }
            this.renderer.removeChild(document.body, this.modalElement);
            this.modalElement = null;
        }
        if (this.backdropElement) {
            this.renderer.removeChild(document.body, this.backdropElement);
            this.backdropElement = null;
        }
        this.renderer.removeClass(document.body, "modal-open");

        // Restore focus to the element that triggered the modal
        if (this.previouslyFocusedElement) {
            this.previouslyFocusedElement.focus();
            this.previouslyFocusedElement = null;
        }
    }
}
