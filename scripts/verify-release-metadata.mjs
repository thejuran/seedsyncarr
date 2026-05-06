#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const VERSION_PATTERN = /^\d+\.\d+\.\d+$/;

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function normalizeExpectedVersion(rawVersion) {
  if (typeof rawVersion !== "string" || rawVersion.trim() === "") {
    throw new Error("Expected release version is required, for example: 1.2.2 or v1.2.2");
  }

  const version = rawVersion.trim().replace(/^v/, "");
  if (!VERSION_PATTERN.test(version)) {
    throw new Error(`Expected release version must use X.Y.Z semver format; received: ${rawVersion}`);
  }

  return version;
}

export function hasChangelogReleaseSection(changelogText, expectedVersion) {
  const escapedVersion = escapeRegExp(expectedVersion);
  const releaseHeading = new RegExp(`^##\\s+\\[?${escapedVersion}\\]?(?:\\s+-\\s+.+)?\\s*$`, "m");
  return releaseHeading.test(changelogText);
}

function readTextFile(rootDir, relativePath, failures) {
  const fullPath = path.join(rootDir, relativePath);
  try {
    return fs.readFileSync(fullPath, "utf8");
  } catch (error) {
    failures.push(`${relativePath} could not be read: ${error.message}`);
    return undefined;
  }
}

function readJsonFile(rootDir, relativePath, failures) {
  const contents = readTextFile(rootDir, relativePath, failures);
  if (contents === undefined) {
    return undefined;
  }

  try {
    return JSON.parse(contents);
  } catch (error) {
    failures.push(`${relativePath} could not be parsed as JSON: ${error.message}`);
    return undefined;
  }
}

function checkVersionField({ failures, checks, label, actual, expectedVersion }) {
  if (actual === undefined) {
    failures.push(`${label} is missing, expected ${expectedVersion}`);
    return;
  }

  if (actual !== expectedVersion) {
    failures.push(`${label} is ${actual}, expected ${expectedVersion}`);
    return;
  }

  checks.push(`${label} is ${expectedVersion}`);
}

export function verifyReleaseMetadata({ rootDir = process.cwd(), expectedVersion }) {
  const failures = [];
  const checks = [];
  let normalizedVersion;

  try {
    normalizedVersion = normalizeExpectedVersion(expectedVersion);
  } catch (error) {
    return {
      expectedVersion,
      checks,
      failures: [error.message],
      passed: false,
    };
  }

  const changelog = readTextFile(rootDir, "CHANGELOG.md", failures);
  if (changelog !== undefined) {
    if (hasChangelogReleaseSection(changelog, normalizedVersion)) {
      checks.push(`CHANGELOG.md has release section [${normalizedVersion}]`);
    } else {
      failures.push(`CHANGELOG.md is missing a release section for [${normalizedVersion}]`);
    }
  }

  const releaseNotes = readTextFile(rootDir, "release-notes.md", failures);
  if (releaseNotes !== undefined) {
    const templatedChangelogLink = /v\{\{VERSION\}\}\/CHANGELOG\.md\b/;
    if (templatedChangelogLink.test(releaseNotes)) {
      checks.push("release-notes.md links to CHANGELOG.md through the {{VERSION}} tag placeholder");
    } else {
      failures.push(
        "release-notes.md must include a CHANGELOG.md link containing v{{VERSION}} so the generated GitHub release body points at the tagged changelog",
      );
    }
  }

  const rootPackage = readJsonFile(rootDir, "package.json", failures);
  if (rootPackage !== undefined) {
    checkVersionField({
      failures,
      checks,
      label: "package.json version",
      actual: rootPackage.version,
      expectedVersion: normalizedVersion,
    });
  }

  const angularPackage = readJsonFile(rootDir, "src/angular/package.json", failures);
  if (angularPackage !== undefined) {
    checkVersionField({
      failures,
      checks,
      label: "src/angular/package.json version",
      actual: angularPackage.version,
      expectedVersion: normalizedVersion,
    });
  }

  const angularLockfile = readJsonFile(rootDir, "src/angular/package-lock.json", failures);
  if (angularLockfile !== undefined) {
    checkVersionField({
      failures,
      checks,
      label: "src/angular/package-lock.json version",
      actual: angularLockfile.version,
      expectedVersion: normalizedVersion,
    });
    checkVersionField({
      failures,
      checks,
      label: 'src/angular/package-lock.json packages[""].version',
      actual: angularLockfile.packages?.[""]?.version,
      expectedVersion: normalizedVersion,
    });
  }

  return {
    expectedVersion: normalizedVersion,
    checks,
    failures,
    passed: failures.length === 0,
  };
}

export function formatVerificationResult(result) {
  const lines = [];

  if (result.passed) {
    lines.push(`Release metadata matches ${result.expectedVersion}:`);
    for (const check of result.checks) {
      lines.push(`- ${check}`);
    }
    return lines.join("\n");
  }

  lines.push(`Release metadata check failed for ${result.expectedVersion ?? "<invalid>"}:`);
  for (const failure of result.failures) {
    lines.push(`- ${failure}`);
  }
  return lines.join("\n");
}

function main(argv) {
  const result = verifyReleaseMetadata({ expectedVersion: argv[2] });
  const output = formatVerificationResult(result);

  if (result.passed) {
    console.log(output);
    return 0;
  }

  console.error(output);
  return 1;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = main(process.argv);
}
