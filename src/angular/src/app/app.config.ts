import {ApplicationConfig, APP_INITIALIZER, provideZoneChangeDetection} from "@angular/core";
import {provideRouter, RouteReuseStrategy} from "@angular/router";
import {provideHttpClient, withInterceptors} from "@angular/common/http";
import {authInterceptor} from "./services/utils/auth.interceptor";

import {ROUTES} from "./routes";
import {environment} from "../environments/environment";
import {CachedReuseStrategy} from "./common/cached-reuse-strategy";
import {LoggerService} from "./services/utils/logger.service";
import {NotificationService} from "./services/utils/notification.service";
import {RestService} from "./services/utils/rest.service";
import {ViewFileService} from "./services/files/view-file.service";
import {ViewFileFilterService} from "./services/files/view-file-filter.service";
import {ViewFileSortService} from "./services/files/view-file-sort.service";
import {ViewFileOptionsService} from "./services/files/view-file-options.service";
import {DomService} from "./services/utils/dom.service";
import {VersionCheckService} from "./services/utils/version-check.service";
import {StreamDispatchService, StreamServiceRegistryProvider} from "./services/base/stream-service.registry";
import {ServerStatusService} from "./services/server/server-status.service";
import {ModelFileService} from "./services/files/model-file.service";
import {ConnectedService} from "./services/utils/connected.service";
import {LogService} from "./services/logs/log.service";
import {AutoQueueServiceProvider} from "./services/autoqueue/autoqueue.service";
import {ConfigServiceProvider} from "./services/settings/config.service";
import {ServerCommandServiceProvider} from "./services/server/server-command.service";
import {LOCAL_STORAGE, LocalStorageService} from "./services/utils/local-storage.service";

// noinspection JSUnusedLocalSymbols
function dummyFactory(_s: unknown): () => null {
    return () => null;
}

function initializeLogger(logger: LoggerService): () => void {
    return () => {
        logger.level = environment.logger.level;
    };
}

export const appConfig: ApplicationConfig = {
    providers: [
        provideZoneChangeDetection({ eventCoalescing: true }),
        provideRouter(ROUTES),
        provideHttpClient(withInterceptors([authInterceptor])),

        {provide: RouteReuseStrategy, useClass: CachedReuseStrategy},
        {provide: LOCAL_STORAGE, useClass: LocalStorageService},

        LoggerService,
        NotificationService,
        RestService,
        ViewFileService,
        ViewFileFilterService,
        ViewFileSortService,
        ViewFileOptionsService,
        DomService,
        VersionCheckService,

        // Stream services
        StreamDispatchService,
        StreamServiceRegistryProvider,
        ServerStatusService,
        ModelFileService,
        ConnectedService,
        LogService,

        AutoQueueServiceProvider,
        ConfigServiceProvider,
        ServerCommandServiceProvider,

        // Initialize logger level
        {
            provide: APP_INITIALIZER,
            useFactory: initializeLogger,
            deps: [LoggerService],
            multi: true
        },
        // Initialize services not tied to any components
        {
            provide: APP_INITIALIZER,
            useFactory: dummyFactory,
            deps: [ViewFileFilterService],
            multi: true
        },
        {
            provide: APP_INITIALIZER,
            useFactory: dummyFactory,
            deps: [ViewFileSortService],
            multi: true
        },
        {
            provide: APP_INITIALIZER,
            useFactory: dummyFactory,
            deps: [VersionCheckService],
            multi: true
        },
    ]
};
