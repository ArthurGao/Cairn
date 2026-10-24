// Regenerate the API types from the backend's OpenAPI export (no running server needed) and
// fail when they differ from the committed lib/api/schema.d.ts.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const committedPath = join(root, "lib/api/schema.d.ts");
const write = process.argv.includes("--write");

const spec = execFileSync("uv", ["run", "--quiet", "python", "-m", "cairn.api.export_openapi"], {
  cwd: join(root, "../backend"),
  encoding: "utf8",
});
const generated = astToString(await openapiTS(JSON.parse(spec)));

if (write) {
  writeFileSync(committedPath, generated);
  console.log(`wrote ${committedPath}`);
} else if (readFileSync(committedPath, "utf8") !== generated) {
  console.error("lib/api/schema.d.ts is out of date: run `npm run api:gen`");
  process.exit(1);
} else {
  console.log("api:check ok — lib/api/schema.d.ts matches the backend");
}
