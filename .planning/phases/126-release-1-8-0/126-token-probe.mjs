#!/usr/bin/env node
// Browser-origin probe for the "GitHub update check carries no app token" D-12a spot
// check (Phase 126, SEC-02). Loads a SeedSyncarr UI in headless Chromium and intercepts
// every request to api.github.com, printing only counts -- never a header value or the
// token itself.
//
// Usage: node 126-token-probe.mjs <baseUrl> <expectedToken>
//
// Prints exactly one line:
//   GITHUB_REQUESTS=<n> WITH_AUTH=<n> WITH_TOKEN=<n>
// GITHUB_REQUESTS: number of requests whose URL host is api.github.com
// WITH_AUTH:       of those, how many carry an Authorization header
// WITH_TOKEN:      of those, how many Authorization values include expectedToken
//
// Exit 0 when at least one GitHub request was observed (the probe ran and saw
// something -- its verdict is in the printed counts). Exit 3 when no GitHub request
// was observed at all (the probe is inconclusive, not a pass). Exit 2 on bad usage.
import puppeteer from "puppeteer";

const [, , baseUrl, expectedToken] = process.argv;

if (!baseUrl || !expectedToken) {
  console.error("usage: node 126-token-probe.mjs <baseUrl> <expectedToken>");
  process.exit(2);
}

let githubRequests = 0;
let withAuth = 0;
let withToken = 0;

async function main() {
  const browser = await puppeteer.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);

    page.on("request", (request) => {
      let host = "";
      try {
        host = new URL(request.url()).host;
      } catch {
        // Unparseable URL: not a GitHub request, fall through to continue().
      }

      if (host === "api.github.com") {
        if (request.method() === "OPTIONS") {
          // CORS preflight: a cross-origin request carrying a non-safelisted
          // header (Authorization) always triggers one of these first. It must
          // be answered with permissive headers or the browser silently drops
          // the real request -- which would make WITH_AUTH/WITH_TOKEN zero
          // regardless of the app's actual behavior (a vacuous probe). The
          // preflight itself never carries Authorization, so it is not counted.
          request
            .respond({
              status: 204,
              headers: {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "authorization, content-type",
              },
            })
            .catch(() => {});
          return;
        }

        githubRequests += 1;
        const headers = request.headers();
        const authHeader = headers["authorization"];
        if (authHeader !== undefined) {
          withAuth += 1;
          if (authHeader.includes(expectedToken)) {
            withToken += 1;
          }
        }
        request
          .respond({
            status: 200,
            headers: { "Access-Control-Allow-Origin": "*" },
            contentType: "application/json",
            body: JSON.stringify({ tag_name: "v0.0.0" }),
          })
          .catch(() => {});
        return;
      }

      request.continue().catch(() => {});
    });

    // networkidle2 (not networkidle0): the app keeps a long-lived SSE connection
    // open for its live model stream, which would make networkidle0 (0 open
    // connections) never resolve and always time out. networkidle2 tolerates
    // that one persistent connection while still waiting for everything else
    // (including the GitHub update-check request) to settle.
    await page.goto(baseUrl, { waitUntil: "networkidle2", timeout: 45000 });
    await new Promise((resolve) => setTimeout(resolve, 5000));
  } finally {
    await browser.close();
  }
}

main()
  .then(() => {
    console.log(`GITHUB_REQUESTS=${githubRequests} WITH_AUTH=${withAuth} WITH_TOKEN=${withToken}`);
    process.exit(githubRequests >= 1 ? 0 : 3);
  })
  .catch((err) => {
    console.error(`ERROR ${err && err.name ? err.name : "UnknownError"}`);
    process.exit(1);
  });
