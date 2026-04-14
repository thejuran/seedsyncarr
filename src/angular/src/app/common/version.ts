declare function require(moduleName: string): { version?: string };
const { version: appVersion = "unknown" } = require("../../../package.json") as { version?: string };

export const APP_VERSION: string = appVersion;
