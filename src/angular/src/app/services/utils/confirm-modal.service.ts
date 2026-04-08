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

    private static escapeHtml(text: string): string {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    private createModal(options: ConfirmModalOptions, resolve: (value: boolean) => void): void {
        // Save previously focused element for focus restoration on close
        this.previouslyFocusedElement = document.activeElement as HTMLElement;

        const okBtn = options.okBtn || "OK";
        const okBtnClass = options.okBtnClass || "btn btn-primary";
        const cancelBtn = options.cancelBtn || "Cancel";
        const cancelBtnClass = options.cancelBtnClass || "btn btn-secondary";

        const safeTitle = ConfirmModalService.escapeHtml(options.title);
        const safeBody = ConfirmModalService.escapeHtml(options.body);
        const safeOkBtn = ConfirmModalService.escapeHtml(okBtn);
        const safeOkBtnClass = ConfirmModalService.escapeHtml(okBtnClass);
        const safeCancelBtn = ConfirmModalService.escapeHtml(cancelBtn);
        const safeCancelBtnClass = ConfirmModalService.escapeHtml(cancelBtnClass);

        // Build skip count message if provided
        let skipMessage = "";
        if (options.skipCount && options.skipCount > 0) {
            const plural = options.skipCount === 1 ? "" : "s";
            skipMessage = `<p class="text-muted small mt-2">${options.skipCount} file${plural} ` +
                `will be skipped (not eligible for this action)</p>`;
        }

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

        this.modalElement!.innerHTML = `
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirm-modal-title">${safeTitle}</h5>
                    </div>
                    <div class="modal-body">
                        <p>${safeBody}</p>
                        ${skipMessage}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="${safeCancelBtnClass}" data-action="cancel">${safeCancelBtn}</button>
                        <button type="button" class="${safeOkBtnClass}" data-action="ok">${safeOkBtn}</button>
                    </div>
                </div>
            </div>
        `;

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
