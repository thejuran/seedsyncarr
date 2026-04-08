// Karma configuration file, see link for more information
// https://karma-runner.github.io/2.0/config/configuration-file.html

module.exports = function (config) {
    config.set({
        basePath: '',
        frameworks: ['jasmine', '@angular-devkit/build-angular'],
        plugins: [
            require('karma-jasmine'),
            require('karma-chrome-launcher'),
            require('karma-jasmine-html-reporter'),
            require('karma-coverage'),
            require('karma-spec-reporter')
        ],
        client: {
            clearContext: false, // leave Jasmine Spec Runner output visible in browser
            captureConsole: false,
            jasmine: {
                timeoutInterval: 10000,  // 10 second timeout for async tests
                random: false  // Run tests in consistent order for debugging
            }
        },
        coverageReporter: {
            type: 'html',
            dir: 'coverage/'
        },
        angularCli: {
            environment: 'dev'
        },
        reporters: ['spec', 'kjhtml'],
        port: 9876,
        colors: true,
        logLevel: config.LOG_INFO,
        autoWatch: true,
        browsers: ['Chrome'],
        singleRun: false,

        // Increased timeouts for CI stability
        browserDisconnectTimeout: 30000,
        browserDisconnectTolerance: 3,
        browserNoActivityTimeout: 120000,
        captureTimeout: 120000,
        processKillTimeout: 10000,

        customLaunchers: {
            ChromeHeadless: {
                base: 'Chrome',
                flags: [
                    '--headless',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--remote-debugging-port=9222'
                ]
            },
            ChromeHeadlessCI: {
                base: 'Chrome',
                flags: [
                    '--headless',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--remote-debugging-port=9222'
                ]
            }
        }
    });
};
