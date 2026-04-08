import {Injectable} from "@angular/core";
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {Observable, of} from "rxjs";
import {catchError, map, shareReplay} from "rxjs/operators";

import {LoggerService} from "./logger.service";


/**
 * WebReaction encapsulates the response for an action
 * executed on a BaseWebService
 */
export class WebReaction {
    readonly success: boolean;
    readonly data: string | null;
    readonly errorMessage: string | null;

    constructor(success: boolean, data: string | null, errorMessage: string | null) {
        this.success = success;
        this.data = data;
        this.errorMessage = errorMessage;
    }
}


/**
 * RestService exposes the HTTP REST API to clients
 */
@Injectable()
export class RestService {

    constructor(private _logger: LoggerService,
                private _http: HttpClient) {
    }

    /**
     * Send backend a GET request and generate a WebReaction response
     * @param {string} url
     * @returns {Observable<WebReaction>}
     */
    public sendRequest(url: string): Observable<WebReaction> {
        return this._http.get(url, {responseType: "text"}).pipe(
            map(this.handleSuccess(url)),
            catchError(this.handleError(url)),
            shareReplay(1)
        );
        // shareReplay is needed to:
        //      prevent duplicate http requests
        //      share result with those that subscribe after the value was published
        // More info: https://blog.thoughtram.io/angular/2016/06/16/cold-vs-hot-observables.html
    }

    /**
     * Send backend a POST request and generate a WebReaction response
     * @param {string} url
     * @returns {Observable<WebReaction>}
     */
    public post(url: string): Observable<WebReaction> {
        return this._http.post(url, null, {responseType: "text"}).pipe(
            map(this.handleSuccess(url)),
            catchError(this.handleError(url)),
            shareReplay(1)
        );
    }

    /**
     * Send backend a DELETE request and generate a WebReaction response
     * @param {string} url
     * @returns {Observable<WebReaction>}
     */
    public delete(url: string): Observable<WebReaction> {
        return this._http.delete(url, {responseType: "text"}).pipe(
            map(this.handleSuccess(url)),
            catchError(this.handleError(url)),
            shareReplay(1)
        );
    }

    private handleSuccess(url: string): (data: string) => WebReaction {
        return (data: string): WebReaction => {
            this._logger.debug("%s http response: %s", url, data);
            return new WebReaction(true, data, null);
        };
    }

    private handleError(url: string): (err: HttpErrorResponse) => Observable<WebReaction> {
        return (err: HttpErrorResponse): Observable<WebReaction> => {
            this._logger.debug("%s error: %O", url, err);
            const errorMessage: string | null = err.error instanceof Event
                ? err.error.type
                : err.error;
            return of(new WebReaction(false, null, errorMessage));
        };
    }
}
