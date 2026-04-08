import {Injectable, InjectionToken} from "@angular/core";

export interface StorageService {
    get<T = unknown>(key: string): T | null;
    set<T>(key: string, value: T): void;
    remove(key: string): void;
}

export const LOCAL_STORAGE = new InjectionToken<StorageService>("LOCAL_STORAGE");

@Injectable({
    providedIn: "root"
})
export class LocalStorageService implements StorageService {

    get<T = unknown>(key: string): T | null {
        const item = localStorage.getItem(key);
        if (item === null) {
            return null;
        }
        try {
            return JSON.parse(item) as T;
        } catch {
            return item as T;
        }
    }

    set<T>(key: string, value: T): void {
        localStorage.setItem(key, JSON.stringify(value));
    }

    remove(key: string): void {
        localStorage.removeItem(key);
    }
}
