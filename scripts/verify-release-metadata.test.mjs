import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  hasChangelogReleaseSection,
  normalizeExpectedVersion,
  verifyReleaseMetadata,
} from "./verify-release-metadata.mjs";

const verifierScriptPath = path.resolve("scripts/verify-release-metadata.mjs");

async function writeFixture(rootDir, overrides = {}) {
  const version = overrides.version ?? "1.2.2";
  const changelogVersion = overrides.changelogVersion ?? version;
  const rootPackageVersion = overrides.rootPackageVersion ?? version;
  const angularPackageVersion = overrides.angularPackageVersion ?? version;
  const angularLockfileVersion = overrides.angularLockfileVersion ?? version;
  const angularLockfileRootVersion = overrides.angularLockfileRootVersion ?? version;
  const releaseNotes = overrides.releaseNotes ?? "Release notes\n\n**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md\n";

  await fs.mkdir(path.join(rootDir, "src/angular"), { recursive: true });
  await fs.writeFile(
    path.join(rootDir, "CHANGELOG.md"),
    overrides.changelog ?? `# Changelog\n\n## [${changelogVersion}] - 2026-05-05\n\n### Fixed\n\n- Something.\n`,
  );
  await fs.writeFile(path.join(rootDir, "release-notes.md"), releaseNotes);
  await fs.writeFile(
    path.join(rootDir, "package.json"),
    JSON.stringify({ version: rootPackageVersion }, null, 2),
  );
  await fs.writeFile(
    path.join(rootDir, "src/angular/package.json"),
    overrides.angularPackageJson ?? JSON.stringify({ name: "seedsyncarr", version: angularPackageVersion }, null, 2),
  );
  await fs.writeFile(
    path.join(rootDir, "src/angular/package-lock.json"),
    JSON.stringify({
      name: "seedsyncarr",
      version: angularLockfileVersion,
      lockfileVersion: 3,
      packages: {
        "": {
          name: "seedsyncarr",
          version: angularLockfileRootVersion,
        },
      },
    }, null, 2),
  );
}

async function withFixture(overrides, callback) {
  const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "release-metadata-"));
  try {
    await writeFixture(rootDir, overrides);
    await callback(rootDir);
  } finally {
    await fs.rm(rootDir, { recursive: true, force: true });
  }
}

function getWorkflowJobBlock(workflow, jobName) {
  const jobBlock = workflow.match(new RegExp(`(?:^|\\n)  ${jobName}:([\\s\\S]*?)(?=\\n  [a-zA-Z0-9_-]+:|\\n*$)`));
  assert.ok(jobBlock, `${jobName} job should exist`);
  return jobBlock[1];
}

test("normalizeExpectedVersion accepts a plain semver release", () => {
  assert.equal(normalizeExpectedVersion("1.2.2"), "1.2.2");
});

test("normalizeExpectedVersion accepts an optional leading v", () => {
  assert.equal(normalizeExpectedVersion("v1.2.2"), "1.2.2");
});

test("normalizeExpectedVersion rejects invalid release versions", () => {
  assert.throws(() => normalizeExpectedVersion("latest"), /X\.Y\.Z semver/);
  assert.throws(() => normalizeExpectedVersion("1.2"), /X\.Y\.Z semver/);
  assert.throws(() => normalizeExpectedVersion(""), /required/);
});

test("hasChangelogReleaseSection detects bracketed Keep a Changelog headings", () => {
  assert.equal(hasChangelogReleaseSection("## [1.2.2] - 2026-05-05\n", "1.2.2"), true);
});

test("verifyReleaseMetadata passes when all metadata matches", async () => {
  await withFixture({}, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, true);
    assert.deepEqual(result.failures, []);
  });
});

test("verifyReleaseMetadata accepts expected versions with leading v", async () => {
  await withFixture({}, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "v1.2.2" });
    assert.equal(result.passed, true);
    assert.equal(result.expectedVersion, "1.2.2");
  });
});

test("CLI exits zero when release metadata matches", async () => {
  await withFixture({}, async (rootDir) => {
    const result = spawnSync(
      process.execPath,
      [verifierScriptPath, "1.2.2"],
      { cwd: rootDir, encoding: "utf8" },
    );

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Release metadata matches 1\.2\.2/);
    assert.equal(result.stderr, "");
  });
});

test("CLI exits non-zero when release metadata mismatches", async () => {
  await withFixture({ rootPackageVersion: "1.2.1" }, async (rootDir) => {
    const result = spawnSync(
      process.execPath,
      [verifierScriptPath, "1.2.2"],
      { cwd: rootDir, encoding: "utf8" },
    );

    assert.equal(result.status, 1);
    assert.match(result.stderr, /package\.json version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata fails when changelog section is missing", async () => {
  await withFixture({ changelogVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /CHANGELOG\.md is missing/);
  });
});

test("verifyReleaseMetadata fails when root package version mismatches", async () => {
  await withFixture({ rootPackageVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /package\.json version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata fails when Angular package version mismatches", async () => {
  await withFixture({ angularPackageVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /src\/angular\/package\.json version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata fails when Angular lockfile top-level version mismatches", async () => {
  await withFixture({ angularLockfileVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /src\/angular\/package-lock\.json version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata fails when Angular lockfile package root version mismatches", async () => {
  await withFixture({ angularLockfileRootVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /packages\[""\]\.version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata ignores Python pyproject version because PyPI stamps it from the tag", async () => {
  await withFixture({}, async (rootDir) => {
    await fs.mkdir(path.join(rootDir, "src/python"), { recursive: true });
    await fs.writeFile(
      path.join(rootDir, "src/python/pyproject.toml"),
      '[tool.poetry]\nname = "seedsyncarr"\nversion = "0.0.0"\n',
    );

    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, true);
  });
});

test("verifyReleaseMetadata reports multiple mismatches together", async () => {
  await withFixture({ changelogVersion: "1.2.1", rootPackageVersion: "1.2.1" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.ok(result.failures.length >= 2);
    assert.match(result.failures.join("\n"), /CHANGELOG\.md is missing/);
    assert.match(result.failures.join("\n"), /package\.json version is 1\.2\.1/);
  });
});

test("verifyReleaseMetadata fails clearly on malformed JSON", async () => {
  await withFixture({ angularPackageJson: "{" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /src\/angular\/package\.json could not be parsed as JSON/);
  });
});

test("verifyReleaseMetadata fails when release notes cannot be templated with the tag version", async () => {
  await withFixture({ releaseNotes: "Release notes without a placeholder\n" }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /release-notes\.md must include a CHANGELOG\.md link containing v\{\{VERSION\}\}/);
  });
});

test("verifyReleaseMetadata fails when the changelog link uses a hard-coded stale version", async () => {
  await withFixture({
    releaseNotes: "Release {{VERSION}}\n\n**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v1.2.1/CHANGELOG.md\n",
  }, async (rootDir) => {
    const result = verifyReleaseMetadata({ rootDir, expectedVersion: "1.2.2" });
    assert.equal(result.passed, false);
    assert.match(result.failures.join("\n"), /CHANGELOG\.md link containing v\{\{VERSION\}\}/);
  });
});

test("tag publishing jobs are gated by release metadata verification", async () => {
  const workflow = await fs.readFile(new URL("../.github/workflows/ci.yml", import.meta.url), "utf8");

  for (const jobName of ["build-docker-image", "publish-docker-image", "publish-github-release", "publish-pypi"]) {
    const jobBlock = getWorkflowJobBlock(workflow, jobName);
    assert.match(
      jobBlock,
      /needs:\s*\[[^\]]*verify-release-metadata[^\]]*\]/,
      `${jobName} should need verify-release-metadata before release-capable publishing`,
    );
  }

  const buildDockerImageJob = getWorkflowJobBlock(workflow, "build-docker-image");
  assert.match(
    buildDockerImageJob,
    /needs:\s*\[[^\]]*unittests-release-metadata[^\]]*\]/,
    "build-docker-image should need release metadata verifier tests before release-capable publishing",
  );
});

test("release metadata verifier tests run in CI", async () => {
  const workflow = await fs.readFile(new URL("../.github/workflows/ci.yml", import.meta.url), "utf8");
  const jobBlock = getWorkflowJobBlock(workflow, "unittests-release-metadata");

  assert.match(jobBlock, /npm run test:release-metadata/);
});

test("release metadata verifier job runs the tag guard command", async () => {
  const workflow = await fs.readFile(new URL("../.github/workflows/ci.yml", import.meta.url), "utf8");
  const jobBlock = getWorkflowJobBlock(workflow, "verify-release-metadata");

  assert.match(jobBlock, /if:\s*startsWith\(github\.ref,\s*'refs\/tags\/v'\)/);
  assert.match(jobBlock, /npm run verify:release-metadata -- "\$\{GITHUB_REF_NAME#v\}"/);
});
