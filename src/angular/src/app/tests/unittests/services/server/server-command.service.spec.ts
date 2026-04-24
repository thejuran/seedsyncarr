import {TestBed} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {LoggerService} from "../../../../services/utils/logger.service";
import {ServerCommandService} from "../../../../services/server/server-command.service";
import {MockStreamServiceRegistry} from "../../../mocks/mock-stream-service.registry";
import {RestService} from "../../../../services/utils/rest.service";
import {ConnectedService} from "../../../../services/utils/connected.service";
import {StreamServiceRegistry} from "../../../../services/base/stream-service.registry";


describe("Testing server command service", () => {
    let mockRegistry: MockStreamServiceRegistry;
    let httpMock: HttpTestingController;
    let commandService: ServerCommandService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                ServerCommandService,
                LoggerService,
                RestService,
                ConnectedService,
                {provide: StreamServiceRegistry, useClass: MockStreamServiceRegistry}
            ]
        });

        mockRegistry = TestBed.inject(StreamServiceRegistry) as unknown as MockStreamServiceRegistry;
        httpMock = TestBed.inject(HttpTestingController);
        commandService = TestBed.inject(ServerCommandService);

        // Connect the services
        mockRegistry.connect();

        // Finish test config init
        commandService.onInit();
    });

    afterEach(() => {
        httpMock.verify();
    });

    it("should create an instance", () => {
        expect(commandService).toBeDefined();
    });


    it("should send a POST restart command", () => {
        let count = 0;
        commandService.restart().subscribe({
           next: reaction => {
               count++;
               expect(reaction.success).toBe(true);
           }
        });

        // Expect POST, not GET
        const req = httpMock.expectOne("/server/command/restart");
        expect(req.request.method).toBe("POST");
        req.flush("{}");

        expect(count).toBe(1);
    });
});
