FROM seedsyncarr/build/angular/env AS seedsyncarr_test_angular

# Install Chrome/Chromium for headless testing
# ARM64: Use Chromium from Debian repos (Chrome not available for ARM64 Linux)
# AMD64: Use Google Chrome
RUN apt-get update && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "arm64" ]; then \
        apt-get install -y chromium chromium-driver && \
        ln -sf /usr/bin/chromium /usr/bin/google-chrome; \
    else \
        apt-get install -y wget gnupg && \
        wget -qO - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable; \
    fi

COPY \
    src/angular/tsconfig.json \
    src/angular/karma.conf.js \
    src/angular/angular.json \
    /app/

RUN ls -l /app/

# ng src needs to be mounted on /app/src
WORKDIR /app/src

# Note: Angular 13+ CLI binary is ng.js
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false"]
