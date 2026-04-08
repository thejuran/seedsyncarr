import {Injectable, OnDestroy} from "@angular/core";
import {Observable} from "rxjs";

import {BaseWebService} from "../base/base-web.service";
import {StreamServiceRegistry} from "../base/stream-service.registry";
import {RestService, WebReaction} from "../utils/rest.service";


/**
 * ServerCommandService handles sending commands to the backend server
 */
@Injectable()
export class ServerCommandService extends BaseWebService implements OnDestroy {
    private readonly RESTART_URL = "/server/command/restart";

    constructor(_streamServiceProvider: StreamServiceRegistry,
                private _restService: RestService) {
        super(_streamServiceProvider);
    }

    /**
     * Send a restart command to the server
     * @returns {Observable<WebReaction>}
     */
    public restart(): Observable<WebReaction> {
        return this._restService.post(this.RESTART_URL);
    }

    protected onConnected(): void {
        // Nothing to do
    }

    protected onDisconnected(): void {
        // Nothing to do
    }

    override ngOnDestroy(): void {
        super.ngOnDestroy();
    }
}

/**
 * ConfigService factory and provider
 */
export const serverCommandServiceFactory = (
    _streamServiceRegistry: StreamServiceRegistry,
    _restService: RestService
): ServerCommandService => {
  const serverCommandService = new ServerCommandService(_streamServiceRegistry, _restService);
  serverCommandService.onInit();
  return serverCommandService;
};

// noinspection JSUnusedGlobalSymbols
export const ServerCommandServiceProvider = {
    provide: ServerCommandService,
    useFactory: serverCommandServiceFactory,
    deps: [StreamServiceRegistry, RestService]
};
