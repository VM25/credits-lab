// Copy the backend's data/outputs into the frontend's public dir so the SPA
// fetches the REAL reconciled files. No metric is ever inlined in TSX.
import { cpSync, mkdirSync, existsSync, rmSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "data", "outputs");
const destParent = join(here, "..", "public", "data");
const dest = join(destParent, "outputs");

if (!existsSync(src)) {
  console.error(`[sync-data] missing ${src} — run the backend pipeline first (python -m src.run_pipeline).`);
  process.exit(1);
}
mkdirSync(destParent, { recursive: true });
// Remove any stale copy OR legacy symlink so we always produce a fresh real copy.
rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log(`[sync-data] copied ${readdirSync(src).length} files -> public/data/outputs`);
