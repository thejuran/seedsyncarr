import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AboutPageComponent } from "./about-page.component";

describe("AboutPageComponent", () => {
    let component: AboutPageComponent;
    let fixture: ComponentFixture<AboutPageComponent>;
    let el: HTMLElement;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [AboutPageComponent]
        }).compileComponents();
        fixture = TestBed.createComponent(AboutPageComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        el = fixture.nativeElement;
    });

    // ABUT-01: Identity card
    it("should display brand title with amber arr span", () => {
        const title = el.querySelector(".identity-title");
        expect(title).toBeTruthy();
        expect(title!.textContent).toContain("SeedSync");
        const arrSpan = title!.querySelector(".brand-arr");
        expect(arrSpan).toBeTruthy();
        expect(arrSpan!.textContent).toBe("arr");
    });

    it("should display app version with Stable suffix", () => {
        const badge = el.querySelector(".version-badge");
        expect(badge).toBeTruthy();
        expect(badge!.textContent).toContain(component.version);
        expect(badge!.textContent).toContain("(Stable)");
    });

    it("should display brand favicon image", () => {
        const img = el.querySelector(".brand-favicon") as HTMLImageElement;
        expect(img).toBeTruthy();
        expect(img.src).toContain("favicon");
    });

    it("should display tagline text", () => {
        const tagline = el.querySelector(".identity-tagline");
        expect(tagline).toBeTruthy();
        expect(tagline!.textContent).toContain("Sync files from your seedbox");
    });

    // ABUT-02: System info table
    it("should render 7 system info rows", () => {
        const rows = el.querySelectorAll(".sysinfo-row");
        expect(rows.length).toBe(7);
    });

    it("should display App Version row with live value", () => {
        const rows = el.querySelectorAll(".sysinfo-row");
        const firstLabel = rows[0].querySelector(".sysinfo-label");
        const firstValue = rows[0].querySelector(".sysinfo-value");
        expect(firstLabel!.textContent!.trim()).toBe("APP VERSION");
        expect(firstValue!.textContent).toContain(component.version);
    });

    it("should display Angular version in Frontend Core row", () => {
        const rows = el.querySelectorAll(".sysinfo-row");
        const secondValue = rows[1].querySelector(".sysinfo-value");
        expect(secondValue!.textContent).toContain(component.angularVersion);
    });

    it("should show placeholder dashes for unavailable system info", () => {
        const rows = el.querySelectorAll(".sysinfo-row");
        // Python Version (index 2), Host OS (3), Uptime (4), Process ID (5)
        for (const idx of [2, 3, 4, 5]) {
            const value = rows[idx].querySelector(".sysinfo-value");
            expect(value!.textContent!.trim()).toBe("\u2014");
        }
    });

    it("should show config path as ~/.seedsyncarr", () => {
        const rows = el.querySelectorAll(".sysinfo-row");
        const configValue = rows[6].querySelector(".sysinfo-value");
        expect(configValue!.textContent!.trim()).toBe("~/.seedsyncarr");
    });

    // ABUT-03: Link cards
    it("should render 4 link cards", () => {
        const cards = el.querySelectorAll(".link-card");
        expect(cards.length).toBe(4);
    });

    it("should have correct hrefs on link cards", () => {
        const cards = el.querySelectorAll(".link-card") as NodeListOf<HTMLAnchorElement>;
        expect(cards[0].href).toBe("https://github.com/thejuran/seedsyncarr");
        expect(cards[1].href).toBe("https://thejuran.github.io/seedsyncarr/");
        expect(cards[2].href).toBe("https://github.com/thejuran/seedsyncarr/issues");
        expect(cards[3].href).toBe("https://github.com/thejuran/seedsyncarr/releases");
    });

    it("should open all link cards in new tabs", () => {
        const cards = el.querySelectorAll(".link-card") as NodeListOf<HTMLAnchorElement>;
        cards.forEach(card => {
            expect(card.target).toBe("_blank");
        });
    });

    // ABUT-04: License and copyright
    it("should display Apache License 2.0 badge", () => {
        const badge = el.querySelector(".license-badge");
        expect(badge).toBeTruthy();
        expect(badge!.textContent).toContain("Apache License 2.0");
    });

    it("should display copyright text", () => {
        const copyright = el.querySelector(".copyright-text");
        expect(copyright).toBeTruthy();
        expect(copyright!.textContent).toContain("2017");
        expect(copyright!.textContent).toContain("Inderpreet Singh");
        expect(copyright!.textContent).toContain("thejuran");
    });

    it("should display fork attribution note", () => {
        const forkNote = el.querySelector(".fork-note");
        expect(forkNote).toBeTruthy();
        expect(forkNote!.textContent).toContain("SeedSync");
        const link = forkNote!.querySelector("a") as HTMLAnchorElement;
        expect(link.href).toBe("https://github.com/ipsingh06/seedsync");
    });
});
