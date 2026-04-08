import {Injectable, OnDestroy} from "@angular/core";
import {Observable, BehaviorSubject} from "rxjs";
import {takeUntil} from "rxjs/operators";

import * as Immutable from "immutable";

import {LoggerService} from "../utils/logger.service";
import {BaseWebService} from "../base/base-web.service";
import {AutoQueuePattern, AutoQueuePatternJson} from "./autoqueue-pattern";
import {Localization} from "../../common/localization";
import {StreamServiceRegistry} from "../base/stream-service.registry";
import {RestService, WebReaction} from "../utils/rest.service";


/**
 * AutoQueueService provides the store for the autoqueue patterns
 */
@Injectable()
export class AutoQueueService extends BaseWebService implements OnDestroy {
    private readonly AUTOQUEUE_GET_URL = "/server/autoqueue/get";
    private readonly AUTOQUEUE_ADD_URL = (pattern: string): string => `/server/autoqueue/add/${pattern}`;
    private readonly AUTOQUEUE_REMOVE_URL = (pattern: string): string => `/server/autoqueue/remove/${pattern}`;

    private _patterns: BehaviorSubject<Immutable.List<AutoQueuePattern>> =
            new BehaviorSubject<Immutable.List<AutoQueuePattern>>(Immutable.List<AutoQueuePattern>());

    constructor(_streamServiceProvider: StreamServiceRegistry,
                private _restService: RestService,
                private _logger: LoggerService) {
        super(_streamServiceProvider);
    }

    /**
     * Returns an observable that provides that latest patterns
     * @returns {Observable<Immutable.List<AutoQueuePattern>>}
     */
    get patterns(): Observable<Immutable.List<AutoQueuePattern>> {
        return this._patterns.asObservable();
    }

    /**
     * Add a pattern
     * @param {string} pattern
     * @returns {Observable<WebReaction>}
     */
    public add(pattern: string): Observable<WebReaction> {
        this._logger.debug("add pattern %O", pattern);

        // Value check
        if (pattern == null || pattern.trim().length === 0) {
            return new Observable<WebReaction>(observer => {
                observer.next(new WebReaction(false, null, Localization.Notification.AUTOQUEUE_PATTERN_EMPTY));
            });
        }

        const currentPatterns = this._patterns.getValue();
        const index = currentPatterns.findIndex(pat => pat.pattern === pattern);
        if (index >= 0) {
            return new Observable<WebReaction>(observer => {
                observer.next(new WebReaction(false, null, `Pattern '${pattern}' already exists.`));
            });
        } else {
            // Double-encode the value
            const patternEncoded = encodeURIComponent(encodeURIComponent(pattern));
            const url = this.AUTOQUEUE_ADD_URL(patternEncoded);
            const obs = this._restService.sendRequest(url);
            obs.pipe(takeUntil(this.destroy$)).subscribe({
                next: reaction => {
                    if (reaction.success) {
                        // Update our copy and notify clients
                        const patterns = this._patterns.getValue();
                        const newPatterns = patterns.push(
                            new AutoQueuePattern({
                                pattern: pattern
                            })
                        );
                        this._patterns.next(newPatterns);
                    }
                }
            });
            return obs;
        }
    }

    /**
     * Remove a pattern
     * @param {string} pattern
     * @returns {Observable<WebReaction>}
     */
    public remove(pattern: string): Observable<WebReaction> {
        this._logger.debug("remove pattern %O", pattern);

        const currentPatterns = this._patterns.getValue();
        const index = currentPatterns.findIndex(pat => pat.pattern === pattern);
        if (index < 0) {
            return new Observable<WebReaction>(observer => {
                observer.next(new WebReaction(false, null, `Pattern '${pattern}' not found.`));
            });
        } else {
            // Double-encode the value
            const patternEncoded = encodeURIComponent(encodeURIComponent(pattern));
            const url = this.AUTOQUEUE_REMOVE_URL(patternEncoded);
            const obs = this._restService.sendRequest(url);
            obs.pipe(takeUntil(this.destroy$)).subscribe({
                next: reaction => {
                    if (reaction.success) {
                        // Update our copy and notify clients
                        // Re-read fresh state inside the callback to avoid stale index from
                        // pre-request snapshot (patterns may have changed during the request)
                        const patterns = this._patterns.getValue();
                        const finalIndex = patterns.findIndex(pat => pat.pattern === pattern);
                        if (finalIndex >= 0) {
                            const newPatterns = patterns.remove(finalIndex);
                            this._patterns.next(newPatterns);
                        }
                    }
                }
            });
            return obs;
        }
    }

    protected onConnected(): void {
        // Retry the get
        this.getPatterns();
    }

    protected onDisconnected(): void {
        // Send empty list
        this._patterns.next(Immutable.List([]));
    }

    override ngOnDestroy(): void {
        super.ngOnDestroy();
    }

    private getPatterns(): void {
        this._logger.debug("Getting autoqueue patterns...");
        this._restService.sendRequest(this.AUTOQUEUE_GET_URL).pipe(takeUntil(this.destroy$)).subscribe({
            next: reaction => {
                if (reaction.success) {
                    const parsed: AutoQueuePatternJson[] = JSON.parse(reaction.data!);
                    const newPatterns: AutoQueuePattern[] = [];
                    for (const patternJson of parsed) {
                        newPatterns.push(new AutoQueuePattern({
                            pattern: patternJson.pattern
                        }));
                    }
                    this._patterns.next(Immutable.List(newPatterns));
                } else {
                    this._patterns.next(Immutable.List([]));
                }
            }
        });
    }
}

/**
 * AutoQueueService factory and provider
 */
export const autoQueueServiceFactory = (
    _streamServiceRegistry: StreamServiceRegistry,
    _restService: RestService,
    _logger: LoggerService
): AutoQueueService => {
  const autoQueueService = new AutoQueueService(_streamServiceRegistry, _restService, _logger);
  autoQueueService.onInit();
  return autoQueueService;
};

export const AutoQueueServiceProvider = {
    provide: AutoQueueService,
    useFactory: autoQueueServiceFactory,
    deps: [StreamServiceRegistry, RestService, LoggerService]
};
