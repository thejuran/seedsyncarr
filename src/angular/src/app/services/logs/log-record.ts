import {Record} from "immutable";


/**
 * LogRecord immutable
 */
interface ILogRecord {
    time: Date;
    level: LogRecord.Level;
    loggerName: string;
    message: string;
    exceptionTraceback: string;
}
const DefaultLogRecord: ILogRecord = {
    time: new Date(0),
    level: "INFO" as LogRecord.Level,
    loggerName: "",
    message: "",
    exceptionTraceback: "",
};
const LogRecordRecord = Record(DefaultLogRecord);
export class LogRecord extends LogRecordRecord implements ILogRecord {
    time!: Date;
    level!: LogRecord.Level;
    loggerName!: string;
    message!: string;
    exceptionTraceback!: string;

    constructor(props: Partial<LogRecord>) {
        super(props);
    }
}


export namespace LogRecord {
    export function fromJson(json: LogRecordJson): LogRecord {
        return new LogRecord({
            // str -> number, then sec -> ms
            time: new Date(1000 * +json.time),
            level: LogRecord.Level[json.level_name as keyof typeof LogRecord.Level],
            loggerName: json.logger_name,
            message: json.message,
            exceptionTraceback: json.exc_tb
        });
    }

    export enum Level {
        DEBUG       = "DEBUG",
        INFO        = "INFO",
        WARNING     = "WARNING",
        ERROR       = "ERROR",
        CRITICAL    = "CRITICAL",
    }
}


/**
 * LogRecord as serialized by the backend.
 * Note: naming convention matches that used in JSON
 */
export interface LogRecordJson {
    time: number;
    level_name: string;
    logger_name: string;
    message: string;
    exc_tb: string;
}
