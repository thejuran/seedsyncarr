import {TestBed} from "@angular/core/testing";

import {ConnectedService} from "../../services/utils/connected.service";
import {MockModelFileService} from "./mock-model-file.service";


export class MockStreamServiceRegistry {
    // Real connected service
    connectedService = TestBed.inject(ConnectedService);

    // Fake model file service
    modelFileService = new MockModelFileService();

    connect(): void {
        this.connectedService.notifyConnected();
    }

    disconnect(): void {
        this.connectedService.notifyDisconnected();
    }
}
