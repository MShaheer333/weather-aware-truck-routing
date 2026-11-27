// Runs `python manage.py <args>` with the backend virtualenv (cross-platform helper).
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = join(root, "backend", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const r = spawnSync(python, ["manage.py", ...process.argv.slice(2)], { cwd: join(root, "backend"), stdio: "inherit" });
process.exit(r.status ?? 1);
