// Render the Mermaid diagrams in diagrams/ to PNG files in docs/assets/diagrams/.
//
//   npm ci --prefix scripts                 # install the pinned Mermaid CLI once
//   node scripts/render-diagrams.mjs         # render every diagram and update the manifest
//   node scripts/render-diagrams.mjs --check # fail when a PNG is missing or out of date
//
// The manifest records the CLI version, render options, and source checksums, so the
// check mode detects any change that requires re-rendering.

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, promises as fs } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDirectory = dirname(fileURLToPath(import.meta.url));
const root = resolve(scriptsDirectory, "..");
const sourceDirectory = join(root, "diagrams");
const outputDirectory = join(root, "docs", "assets", "diagrams");
const configPath = join(sourceDirectory, "mermaid-config.json");
const manifestPath = join(outputDirectory, "manifest.json");
const cliPackagePath = join(scriptsDirectory, "node_modules", "@mermaid-js", "mermaid-cli");
const renderOptions = ["--scale", "2", "--backgroundColor", "white"];
const checkOnly = process.argv.includes("--check");

async function readJson(path) {
  return JSON.parse(await fs.readFile(path, "utf8"));
}

// Line endings are normalized, so a checkout with CRLF endings still matches.
async function checksum(path) {
  const text = (await fs.readFile(path, "utf8")).replaceAll("\r\n", "\n");
  return createHash("sha256").update(text).digest("hex");
}

async function mermaidSources() {
  const entries = await fs.readdir(sourceDirectory, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mmd"))
    .map((entry) => join(sourceDirectory, entry.name))
    .sort((left, right) => left.localeCompare(right, "en"));
}

async function cliVersion() {
  const pinned = (await readJson(join(scriptsDirectory, "package.json"))).devDependencies[
    "@mermaid-js/mermaid-cli"
  ];
  if (!existsSync(cliPackagePath)) {
    throw new Error("Mermaid CLI is not installed. Run `npm ci --prefix scripts` first.");
  }
  const installed = (await readJson(join(cliPackagePath, "package.json"))).version;
  if (installed !== pinned) {
    throw new Error(`Mermaid CLI ${pinned} is pinned but ${installed} is installed.`);
  }
  return installed;
}

function render(source, output) {
  const cli = join(cliPackagePath, "src", "cli.js");
  const args = [cli, "-i", source, "-o", output, "-c", configPath, ...renderOptions];
  return new Promise((resolveRender, reject) => {
    const child = spawn(process.execPath, args, { cwd: root, shell: false, stdio: "inherit" });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolveRender();
      else reject(new Error(`Rendering ${relative(root, source)} failed with exit code ${code}.`));
    });
  });
}

const sources = await mermaidSources();
if (sources.length === 0) throw new Error("No Mermaid sources found in diagrams/.");

const expected = {
  mermaidCli: await cliVersion(),
  options: renderOptions,
  config: await checksum(configPath),
  sources: Object.fromEntries(
    await Promise.all(sources.map(async (path) => [basename(path), await checksum(path)])),
  ),
};

if (checkOnly) {
  if (!existsSync(manifestPath)) throw new Error("Missing diagram manifest. Render the diagrams.");
  if (JSON.stringify(await readJson(manifestPath)) !== JSON.stringify(expected)) {
    throw new Error("Diagrams are out of date. Run `node scripts/render-diagrams.mjs`.");
  }
  for (const source of sources) {
    const output = join(outputDirectory, `${basename(source, ".mmd")}.png`);
    if (!existsSync(output)) throw new Error(`Missing rendered diagram ${relative(root, output)}.`);
  }
  console.log(`All ${sources.length} diagrams are up to date.`);
} else {
  await fs.mkdir(outputDirectory, { recursive: true });
  for (const source of sources) {
    await render(source, join(outputDirectory, `${basename(source, ".mmd")}.png`));
  }
  await fs.writeFile(manifestPath, `${JSON.stringify(expected, null, 2)}\n`);
  console.log(`Rendered ${sources.length} diagrams.`);
}
