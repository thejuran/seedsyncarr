import {LoggerService} from "../app/services/utils/logger.service";

export const environment = {
    production: true,
    useMockModel: false,
    logger: {
        level: LoggerService.Level.WARN
    }
};
