import {ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit, OnDestroy} from "@angular/core";
import { NgTemplateOutlet, AsyncPipe } from "@angular/common";
import {FormsModule} from "@angular/forms";
import {Observable, Subject} from "rxjs";
import {takeUntil} from "rxjs/operators";

import {LoggerService} from "../../services/utils/logger.service";

import {OptionComponent, OptionType} from "./option.component";
import {ConfigService} from "../../services/settings/config.service";
import {Config} from "../../services/settings/config";
import {Notification} from "../../services/utils/notification";
import {Localization} from "../../common/localization";
import {NotificationService} from "../../services/utils/notification.service";
import {ServerCommandService} from "../../services/server/server-command.service";
import {AutoQueueService} from "../../services/autoqueue/autoqueue.service";
import {AutoQueuePattern} from "../../services/autoqueue/autoqueue-pattern";
import {
    OPTIONS_CONTEXT_CONNECTIONS, OPTIONS_CONTEXT_DISCOVERY, OPTIONS_CONTEXT_OTHER,
    OPTIONS_CONTEXT_SERVER, OPTIONS_CONTEXT_AUTOQUEUE, OPTIONS_CONTEXT_EXTRACT,
    OPTIONS_CONTEXT_AUTODELETE
} from "./options-list";
import {ConnectedService} from "../../services/utils/connected.service";
import {StreamServiceRegistry} from "../../services/base/stream-service.registry";

import * as Immutable from "immutable";

@Component({
    selector: "app-settings-page",
    templateUrl: "./settings-page.component.html",
    styleUrls: ["./settings-page.component.scss"],
    providers: [],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
    imports: [NgTemplateOutlet, AsyncPipe, FormsModule, OptionComponent]
})
export class SettingsPageComponent implements OnInit, OnDestroy {
    public OPTIONS_CONTEXT_SERVER = OPTIONS_CONTEXT_SERVER;
    public OPTIONS_CONTEXT_DISCOVERY = OPTIONS_CONTEXT_DISCOVERY;
    public OPTIONS_CONTEXT_CONNECTIONS = OPTIONS_CONTEXT_CONNECTIONS;
    public OPTIONS_CONTEXT_OTHER = OPTIONS_CONTEXT_OTHER;
    public OPTIONS_CONTEXT_AUTOQUEUE = OPTIONS_CONTEXT_AUTOQUEUE;
    public OPTIONS_CONTEXT_EXTRACT = OPTIONS_CONTEXT_EXTRACT;
    public OPTIONS_CONTEXT_AUTODELETE = OPTIONS_CONTEXT_AUTODELETE;

    public OptionType = OptionType;

    public config: Observable<Config | null>;

    public commandsEnabled: boolean;

    private _connectedService: ConnectedService;

    private destroy$ = new Subject<void>();

    private _configRestartNotif: Notification;
    private _badValueNotifs: Map<string, Notification>;

    public testSonarrConnectionLoading = false;
    public testSonarrConnectionResult: {success: boolean; message: string} | null = null;

    public testRadarrConnectionLoading = false;
    public testRadarrConnectionResult: {success: boolean; message: string} | null = null;

    public apiToken = "";
    public tokenCopied = false;
    public tokenRevealed = false;

    // Webhook copy state
    public sonarrWebhookCopied = false;
    public radarrWebhookCopied = false;

    // Floating save bar state
    public hasPendingChanges = false;
    public saveConfirmed = false;
    private saveConfirmedTimer: ReturnType<typeof setTimeout> | null = null;

    // AutoQueue pattern management
    public patterns: Observable<Immutable.List<AutoQueuePattern>>;
    public newPattern = "";
    public autoqueueEnabled = false;
    public patternsOnly = false;

    constructor(private _logger: LoggerService,
                _streamServiceRegistry: StreamServiceRegistry,
                private _configService: ConfigService,
                private _notifService: NotificationService,
                private _commandService: ServerCommandService,
                private _autoqueueService: AutoQueueService,
                private _cdr: ChangeDetectorRef) {
        this._connectedService = _streamServiceRegistry.connectedService;
        this.config = _configService.config;
        this.patterns = _autoqueueService.patterns;
        this.commandsEnabled = false;
        this._configRestartNotif = new Notification({
            level: Notification.Level.INFO,
            text: Localization.Notification.CONFIG_RESTART
        });
        this._badValueNotifs = new Map();
    }

    ngOnInit(): void {
        // Read API token from meta tag injected by Bottle server
        const meta = document.querySelector("meta[name=\"api-token\"]");
        this.apiToken = meta?.getAttribute("content") || "";

        this._connectedService.connected.pipe(takeUntil(this.destroy$)).subscribe({
            next: (connected: boolean) => {
                if (!connected) {
                    // Server went down, hide the config restart notification
                    this._notifService.hide(this._configRestartNotif);
                    this.newPattern = "";
                }

                // Enable/disable commands based on server connection
                this.commandsEnabled = connected;
            }
        });

        // Track autoqueue config for pattern CRUD enable/disable
        this._configService.config.pipe(takeUntil(this.destroy$)).subscribe({
            next: config => {
                if (config?.autoqueue != null) {
                    this.autoqueueEnabled = config.autoqueue.enabled;
                    this.patternsOnly = config.autoqueue.patterns_only;
                } else {
                    this.autoqueueEnabled = false;
                    this.patternsOnly = false;
                }
                this._cdr.markForCheck();
            }
        });
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    onSetConfig(section: string, option: string, value: string | number | boolean): void {
        this.hasPendingChanges = true;
        this._cdr.markForCheck();

        this._configService.set(section, option, value).pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                const notifKey = section + "." + option;
                if (reaction.success) {
                    this._logger.info(reaction.data);

                    // Hide bad value notification, if any
                    if (this._badValueNotifs.has(notifKey)) {
                        this._notifService.hide(this._badValueNotifs.get(notifKey)!);
                        this._badValueNotifs.delete(notifKey);
                    }

                    // Show the restart notification
                    this._notifService.show(this._configRestartNotif);

                    // Show save confirmation in floating bar
                    this.onSaveComplete();
                } else {
                    // Show bad value notification
                    const notif = new Notification({
                        level: Notification.Level.DANGER,
                        dismissible: true,
                        text: reaction.errorMessage ?? "Unknown error"
                    });
                    if (this._badValueNotifs.has(notifKey)) {
                        this._notifService.hide(this._badValueNotifs.get(notifKey)!);
                    }
                    this._notifService.show(notif);
                    this._badValueNotifs.set(notifKey, notif);

                    this._logger.error(reaction.errorMessage);

                    this.hasPendingChanges = false;
                    this._cdr.markForCheck();
                }
            }
        });
    }

    private onSaveComplete(): void {
        this.hasPendingChanges = false;
        this.saveConfirmed = true;
        this._cdr.markForCheck();
        if (this.saveConfirmedTimer) {
            clearTimeout(this.saveConfirmedTimer);
        }
        this.saveConfirmedTimer = setTimeout(() => {
            this.saveConfirmed = false;
            this._cdr.markForCheck();
        }, 2500);
    }

    onCopyToken(): void {
        if (this.apiToken) {
            navigator.clipboard.writeText(this.apiToken).then(() => {
                this.tokenCopied = true;
                this._cdr.markForCheck();
                setTimeout(() => {
                    this.tokenCopied = false;
                    this._cdr.markForCheck();
                }, 2000);
            }).catch(() => { /* clipboard unavailable (non-HTTPS or permissions) */ });
        }
    }

    onCopyWebhookFromInput(input: HTMLInputElement): void {
        navigator.clipboard.writeText(input.value).then(() => {
            // Determine which webhook was copied based on URL content
            if (input.value.includes('/webhook/sonarr')) {
                this.sonarrWebhookCopied = true;
                this._cdr.markForCheck();
                setTimeout(() => {
                    this.sonarrWebhookCopied = false;
                    this._cdr.markForCheck();
                }, 2000);
            } else if (input.value.includes('/webhook/radarr')) {
                this.radarrWebhookCopied = true;
                this._cdr.markForCheck();
                setTimeout(() => {
                    this.radarrWebhookCopied = false;
                    this._cdr.markForCheck();
                }, 2000);
            }
        }).catch(() => { /* clipboard unavailable */ });
    }

    onAddPattern(): void {
        if (!this.commandsEnabled || !this.newPattern || !this.autoqueueEnabled || !this.patternsOnly) {
            return;
        }
        this._autoqueueService.add(this.newPattern).pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                if (reaction.success) {
                    this.newPattern = "";
                    this._cdr.markForCheck();
                } else {
                    const notif = new Notification({
                        level: Notification.Level.DANGER,
                        dismissible: true,
                        text: reaction.errorMessage ?? "Unknown error"
                    });
                    this._notifService.show(notif);
                }
            }
        });
    }

    onRemovePattern(pattern: AutoQueuePattern): void {
        if (!this.commandsEnabled || !this.autoqueueEnabled || !this.patternsOnly) {
            return;
        }
        this._autoqueueService.remove(pattern.pattern).pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                if (!reaction.success) {
                    const notif = new Notification({
                        level: Notification.Level.DANGER,
                        dismissible: true,
                        text: reaction.errorMessage ?? "Unknown error"
                    });
                    this._notifService.show(notif);
                }
            }
        });
    }

    onCommandRestart(): void {
        this._commandService.restart().pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                if (reaction.success) {
                    this._logger.info(reaction.data);
                } else {
                    this._logger.error(reaction.errorMessage);
                }
            }
        });
    }

    onTestSonarrConnection(): void {
        this.testSonarrConnectionLoading = true;
        this.testSonarrConnectionResult = null;
        this._cdr.markForCheck();

        this._configService.testSonarrConnection().pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                this.testSonarrConnectionLoading = false;
                if (reaction.success) {
                    try {
                        const result = JSON.parse(reaction.data!);
                        if (result.success) {
                            this.testSonarrConnectionResult = {
                                success: true,
                                message: "Connected to Sonarr v" + result.version
                            };
                        } else {
                            this.testSonarrConnectionResult = {
                                success: false,
                                message: result.error
                            };
                        }
                    } catch {
                        this.testSonarrConnectionResult = {
                            success: false,
                            message: "Unexpected response from server"
                        };
                    }
                } else {
                    this.testSonarrConnectionResult = {
                        success: false,
                        message: reaction.errorMessage || "Failed to reach server"
                    };
                }
                this._cdr.markForCheck();
            }
        });
    }

    onTestRadarrConnection(): void {
        this.testRadarrConnectionLoading = true;
        this.testRadarrConnectionResult = null;
        this._cdr.markForCheck();

        this._configService.testRadarrConnection().pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                this.testRadarrConnectionLoading = false;
                if (reaction.success) {
                    try {
                        const result = JSON.parse(reaction.data!);
                        if (result.success) {
                            this.testRadarrConnectionResult = {
                                success: true,
                                message: "Connected to Radarr v" + result.version
                            };
                        } else {
                            this.testRadarrConnectionResult = {
                                success: false,
                                message: result.error
                            };
                        }
                    } catch {
                        this.testRadarrConnectionResult = {
                            success: false,
                            message: "Unexpected response from server"
                        };
                    }
                } else {
                    this.testRadarrConnectionResult = {
                        success: false,
                        message: reaction.errorMessage || "Failed to reach server"
                    };
                }
                this._cdr.markForCheck();
            }
        });
    }

}
