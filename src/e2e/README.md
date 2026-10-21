### To run e2e tests in dev mode:

1. Install dependencies

   ```bash
   cd src/e2e
   npm install
   ```
   
2. Choose which dev image to run: deb install or docker image

    - deb install

        ```bash
        make run-tests-e2e SEEDSYNCARR_VERSION=latest SEEDSYNCARR_ARCH=<arch code> DEV=1
        ```

    - docker image

        ```bash
        make run-tests-e2e SEEDSYNCARR_DEB=`readlink -f build/*.deb` SEEDSYNCARR_OS=<os code> DEV=1
        ```

        

3. Compile and run the tests

    ```bash
    cd src/e2e/
    rm -rf tmp && \
        ./node_modules/typescript/bin/tsc && \
        ./node_modules/protractor/bin/protractor tmp/conf.js
    ```



### About

The dev end-to-end tests use the following docker images:
1. myapp: Installs and runs the seedsyncarr deb package
2. chrome: Runs the selenium server
3. remote: Runs a remote SSH server

The automated e2e tests additionally have:
4. tests: Runs the e2e tests

Notes:
1. In dev mode, the app is visible at [http://localhost:8800](http://localhost:8800)
However the url used in test is still [http://myapp:8800](http://myapp:8800) as
that's how the selenium server accesses it.

2. The app requires a fully configured settings.cfg.
   This is done automatically in during the start of the docker image that runs the app.

3. The `chromium-token` project (`tests/auth-token.spec.ts`) runs after every
   other test. It sets `general.api_token` on `myapp` through
   `/server/config/set`, and the API cannot clear it. If you re-run the suite
   against a `DEV=1` `myapp` that already ran it, recreate the container
   first (re-run `make run-tests-e2e ... DEV=1`, which force-recreates
   `myapp`). To run only the token spec, use
   `npx playwright test --project chromium-token`, which also runs the
   `chromium` dependency first unless `--no-deps` is passed.

