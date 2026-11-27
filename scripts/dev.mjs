// Runs the Django API and the Vite dev server together. Ctrl+C stops both.
// Usage: npm run dev   (override ports with BACKEND_PORT / FRONTEND_PORT)
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import net from "node:net";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";

// A port is usable only if we can bind it on both IPv4 and IPv6 loopback (Windows lets one mask the other),
// which also skips ports reserved by the OS or held by other apps.
const canBind = (port, host) =>
  new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", (err) => resolve(!["EADDRINUSE", "EACCES"].includes(err.code)));
    server.once("listening", () => server.close(() => resolve(true)));
    server.listen(port, host);
  });
const freePort = async (start) =>
  (await canBind(start, "127.0.0.1")) && (await canBind(start, "::1")) ? start : freePort(start + 1);

const backendPort = String(process.env.BACKEND_PORT ?? (await freePort(8000)));
const frontendPort = String(process.env.FRONTEND_PORT ?? (await freePort(5173)));

const venvPython = join(root, "backend", ".venv", isWin ? "Scripts/python.exe" : "bin/python");
if (!existsSync(venvPython)) {
  console.error("Backend virtualenv not found. Run `npm run setup` first.");
  process.exit(1);
}
if (!existsSync(join(root, "frontend", "node_modules"))) {
  console.error("Frontend dependencies not found. Run `npm run setup` first.");
  process.exit(1);
}

const children = [];
const run = (name, color, cmd, args, cwd, env = {}) => {
  const child = spawn(cmd, args, { cwd, env: { ...process.env, ...env } });
  const tag = `\x1b[${color}m[${name}]\x1b[0m `;
  const pipe = (stream, out) =>
    stream.on("data", (buf) =>
      buf.toString().split(/\r?\n/).filter(Boolean).forEach((line) => out.write(tag + line + "\n")),
    );
  pipe(child.stdout, process.stdout);
  pipe(child.stderr, process.stderr);
  child.on("exit", (code) => {
    console.log(`${tag}exited (${code})`);
    shutdown(code ?? 0);
  });
  children.push(child);
};

let closing = false;
function shutdown(code = 0) {
  if (closing) return;
  closing = true;
  children.forEach((c) => c.kill());
  setTimeout(() => process.exit(code), 300);
}
process.on("SIGINT", () => shutdown());
process.on("SIGTERM", () => shutdown());

run("api", "36", venvPython, ["manage.py", "runserver", backendPort], join(root, "backend"));
const viteBin = join(root, "frontend", "node_modules", "vite", "bin", "vite.js");
run("web", "35", process.execPath, [viteBin, "--port", frontendPort, "--strictPort"], join(root, "frontend"), {
  API_PROXY: `http://localhost:${backendPort}`,
});

console.log(`\n  App:  http://localhost:${frontendPort}\n  API:  http://localhost:${backendPort}/api/health/\n`);
