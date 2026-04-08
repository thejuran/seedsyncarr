import {Injectable} from "@angular/core";

@Injectable()
export class LoggerService {

    public level: LoggerService.Level;

    constructor() {
        this.level = LoggerService.Level.DEBUG;
    }

    get debug(): (...args: unknown[]) => void {
        if (this.level >= LoggerService.Level.DEBUG) {
            return console.debug.bind(console);
        } else {
            // No-op when debug logging is disabled
            return (): void => { /* Logging disabled at this level */ };
        }
    }

    get info(): (...args: unknown[]) => void {
        if (this.level >= LoggerService.Level.INFO) {
            return console.log.bind(console);
        } else {
            // No-op when info logging is disabled
            return (): void => { /* Logging disabled at this level */ };
        }
    }

    // noinspection JSUnusedGlobalSymbols
    get warn(): (...args: unknown[]) => void {
        if (this.level >= LoggerService.Level.WARN) {
            return console.warn.bind(console);
        } else {
            // No-op when warn logging is disabled
            return (): void => { /* Logging disabled at this level */ };
        }
    }

    get error(): (...args: unknown[]) => void {
        if (this.level >= LoggerService.Level.ERROR) {
            return console.error.bind(console);
        } else {
            // No-op when error logging is disabled
            return (): void => { /* Logging disabled at this level */ };
        }
    }
}

export namespace LoggerService {
    export enum Level {
        ERROR,
        WARN,
        INFO,
        DEBUG,
    }
}
