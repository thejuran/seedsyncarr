import {Component} from "@angular/core";

declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");

@Component({
    selector: "app-about-page",
    templateUrl: "./about-page.component.html",
    styleUrls: ["./about-page.component.scss"],
    providers: [],
    standalone: true
})
export class AboutPageComponent {

    public version: string;

    constructor() {
        this.version = appVersion;
    }
}
