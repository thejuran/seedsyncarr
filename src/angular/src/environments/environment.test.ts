import {LoggerService} from "../app/services/utils/logger.service";

export const environment = {
    production: false,
    useMockModel: false,
    logger: {
        level: LoggerService.Level.DEBUG
    }
};
