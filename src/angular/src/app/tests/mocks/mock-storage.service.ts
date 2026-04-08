import {StorageService} from "../../services/utils/local-storage.service";

export class MockStorageService implements StorageService {
    // noinspection JSUnusedLocalSymbols
    public get<T = unknown>(_key: string): T | null { return null; }

    // noinspection JSUnusedLocalSymbols
    set<T>(_key: string, _value: T): void {
        // Mock implementation - intentionally empty
    }

    // noinspection JSUnusedLocalSymbols
    remove(_key: string): void {
        // Mock implementation - intentionally empty
    }
}
