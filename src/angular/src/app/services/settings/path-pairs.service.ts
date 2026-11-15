import {Injectable} from "@angular/core";
import {Observable, BehaviorSubject} from "rxjs";
import {tap} from "rxjs/operators";

import {LoggerService} from "../utils/logger.service";
import {RestService, WebReaction} from "../utils/rest.service";
import {PathPair, PathPairInput} from "./path-pair";


/**
 * PathPairsService provides the store for the path pairs and their CRUD calls.
 * Changes are saved by the backend at once but only apply after a restart.
 */
@Injectable({
    providedIn: "root"
})
export class PathPairsService {
    private readonly LIST_URL = "/server/pathpairs";
    private readonly CREATE_URL = "/server/pathpairs/create";
    private readonly UPDATE_URL = (id: string): string => `/server/pathpairs/update/${encodeURIComponent(id)}`;
    private readonly DELETE_URL = (id: string): string => `/server/pathpairs/delete/${encodeURIComponent(id)}`;

    private _pairs: BehaviorSubject<PathPair[]> = new BehaviorSubject<PathPair[]>([]);

    constructor(private _restService: RestService,
                private _logger: LoggerService) {
    }

    /**
     * Returns an observable that provides the latest path pairs
     */
    get pairs(): Observable<PathPair[]> {
        return this._pairs.asObservable();
    }

    /**
     * Fetch the path pairs from the backend
     */
    public refresh(): void {
        this._restService.sendRequest(this.LIST_URL).subscribe({
            next: reaction => {
                if (!reaction.success || reaction.data == null) {
                    this._logger.debug("Could not get the path pairs");
                    return;
                }
                try {
                    const parsed: {path_pairs: PathPair[]} = JSON.parse(reaction.data);
                    this._pairs.next(parsed.path_pairs);
                } catch (error) {
                    this._logger.error("Failed to parse path pairs:", error);
                }
            }
        });
    }

    public create(input: PathPairInput): Observable<WebReaction> {
        this._logger.debug("create path pair %O", input);
        return this._restService.post(this.CREATE_URL, input).pipe(tap(r => this.refreshOnSuccess(r)));
    }

    public update(id: string, changes: Partial<PathPairInput>): Observable<WebReaction> {
        this._logger.debug("update path pair %s %O", id, changes);
        return this._restService.post(this.UPDATE_URL(id), changes).pipe(tap(r => this.refreshOnSuccess(r)));
    }

    public remove(id: string): Observable<WebReaction> {
        this._logger.debug("delete path pair %s", id);
        return this._restService.post(this.DELETE_URL(id)).pipe(tap(r => this.refreshOnSuccess(r)));
    }

    private refreshOnSuccess(reaction: WebReaction): void {
        if (reaction.success) {
            this.refresh();
        }
    }
}
