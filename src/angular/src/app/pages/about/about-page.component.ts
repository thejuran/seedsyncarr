import { ChangeDetectionStrategy, Component, VERSION } from "@angular/core";
import { APP_VERSION } from "../../common/version";

@Component({
    selector: "app-about-page",
    templateUrl: "./about-page.component.html",
    styleUrls: ["./about-page.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true
})
export class AboutPageComponent {

    readonly version: string = APP_VERSION;
    readonly angularVersion: string = VERSION.full;
}
