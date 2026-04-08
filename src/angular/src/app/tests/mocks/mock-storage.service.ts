import {StorageService} from "../../services/utils/local-storage.service";

export class MockStorageService implements StorageService {
    public get<T = unknown>(_key: string): T | null { return null; }

    set<T>(_key: string, _value: T): void {
        // Mock implementation - intentionally empty
    }

    remove(_key: string): void {
        // Mock implementation - intentionally empty
    }
}
