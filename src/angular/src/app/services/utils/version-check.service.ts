import {Injectable, OnDestroy} from "@angular/core";
import {Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";

import { compare } from "compare-versions";

import {RestService} from "./rest.service";
import {LoggerService} from "./logger.service";
import {NotificationService} from "./notification.service";
import {Notification} from "./notification";
import {Localization} from "../../common/localization";

declare function require(moduleName: string): { version: string };
const { version: appVersion } = require("../../../../package.json");


/**
 * VersionCheckService checks for the latest version and
 * triggers a notification
 */
@Injectable()
export class VersionCheckService implements OnDestroy {
    private destroy$ = new Subject<void>();
    private readonly GITHUB_LATEST_RELEASE_URL =
        "https://api.github.com/repos/thejuran/seedsyncarr/releases/latest";

    constructor(private _restService: RestService,
                private _notifService: NotificationService,
                private _logger: LoggerService) {
        this.checkVersion();
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    private checkVersion(): void {
        this._restService.sendRequest(this.GITHUB_LATEST_RELEASE_URL).pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                if (reaction.success) {
                    let jsonResponse;
                    let latestVersion;
                    let url;
                    if (!reaction.data) {
                        this._logger.warn("GitHub response had no data body");
                        return;
                    }
                    try {
                        jsonResponse = JSON.parse(reaction.data);
                        latestVersion = jsonResponse.tag_name;
                        url = jsonResponse.html_url;
                    } catch (e) {
                        this._logger.error("Unable to parse github response: %O", e);
                        return;
                    }
                    if (typeof latestVersion !== "string" || !latestVersion) {
                        this._logger.warn("Unexpected tag_name in GitHub response: %O", latestVersion);
                        return;
                    }
                    if (typeof url !== "string" || !/^https:\/\/github\.com\//.test(url)) {
                        this._logger.warn("Unexpected html_url in GitHub response: %O", url);
                        return;
                    }
                    const message = Localization.Notification.NEW_VERSION_AVAILABLE(url);
                    this._logger.debug("Latest version: ", message);
                    let isNewer: boolean;
                    try {
                        isNewer = VersionCheckService.isVersionNewer(latestVersion);
                    } catch (e) {
                        this._logger.warn("tag_name is not a valid semver string: %O", latestVersion);
                        return;
                    }
                    if (isNewer) {
                        const notif = new Notification({
                            level: Notification.Level.INFO,
                            dismissible: true,
                            text: message
                        });
                        this._notifService.show(notif);
                    }
                } else {
                    this._logger.warn("Unable to fetch latest version info: %O", reaction);
                }
            }
        });
    }

    private static isVersionNewer(version: string): boolean {
        // Remove the 'v' at the beginning, if any
        version = version.replace(/^v/, "");
        // Replace - with .
        version = version.replace(/-/g, ".");
        return compare(version, appVersion, ">");
    }
}
