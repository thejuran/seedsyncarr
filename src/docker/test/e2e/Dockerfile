# Creates environment for e2e tests with Playwright
FROM node:22-slim AS seedsyncarr_test_e2e_env

# Install dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY src/e2e/package*.json /app/
WORKDIR /app
RUN npm install

# Install Playwright browsers and dependencies
RUN npx playwright install --with-deps chromium


# Builds and runs e2e tests
FROM seedsyncarr_test_e2e_env AS seedsyncarr_test_e2e

COPY \
    src/e2e/playwright.config.ts \
    src/e2e/tsconfig.json \
    src/e2e/urls.ts \
    /app/
COPY src/e2e/tests /app/tests
COPY \
    src/docker/test/e2e/run_tests.sh \
    src/docker/test/e2e/parse_status.py \
    /app/

WORKDIR /app

CMD ["/app/run_tests.sh"]
