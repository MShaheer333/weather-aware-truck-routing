// One-time setup: Python venv + backend deps + .env + frontend deps.
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const backend = join(root, "backend");
const venvPython = join(backend, ".venv", isWin ? "Scripts/python.exe" : "bin/python");

const sh = (cmd, args, cwd) => {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: isWin && cmd === "npm" });
  if (r.status !== 0) process.exit(r.status ?? 1);
};

if (!existsSync(venvPython)) sh(isWin ? "python" : "python3", ["-m", "venv", ".venv"], backend);
sh(venvPython, ["-m", "pip", "install", "-r", "requirements.txt"], backend);
if (!existsSync(join(backend, ".env"))) copyFileSync(join(backend, ".env.example"), join(backend, ".env"));
sh("npm", ["install"], join(root, "frontend"));
console.log("\nSetup complete. Start everything with: npm run dev");
