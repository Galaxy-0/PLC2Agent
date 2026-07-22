import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const serverPath =
  process.env.IRONPLC_MCP ?? `${process.env.HOME}/.ironplc/bin/ironplcmcp`;
const sourcePath = fileURLToPath(new URL("./main.st", import.meta.url));
const source = await readFile(sourcePath, "utf8");

const server = spawn(serverPath, [], { stdio: ["pipe", "pipe", "inherit"] });
const pending = new Map();
let nextId = 1;
let stdoutBuffer = "";

server.stdout.setEncoding("utf8");
server.stdout.on("data", (chunk) => {
  stdoutBuffer += chunk;
  const lines = stdoutBuffer.split("\n");
  stdoutBuffer = lines.pop() ?? "";

  for (const line of lines) {
    if (!line.trim()) continue;
    const message = JSON.parse(line);
    if (message.id === undefined) continue;

    const waiter = pending.get(message.id);
    if (!waiter) continue;
    pending.delete(message.id);

    if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
    else waiter.resolve(message.result);
  }
});

function send(message) {
  server.stdin.write(`${JSON.stringify(message)}\n`);
}

function request(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    send({ jsonrpc: "2.0", id, method, params });
  });
}

function toolPayload(result) {
  if (result.structuredContent) return result.structuredContent;
  const text = result.content?.find((item) => item.type === "text")?.text;
  if (!text) throw new Error(`MCP tool returned no JSON payload: ${JSON.stringify(result)}`);
  return JSON.parse(text);
}

async function callTool(name, args) {
  const result = await request("tools/call", { name, arguments: args });
  if (result.isError) throw new Error(`${name} failed: ${JSON.stringify(result)}`);
  return toolPayload(result);
}

try {
  const initialized = await request("initialize", {
    protocolVersion: "2025-03-26",
    capabilities: {},
    clientInfo: { name: "plc2agent-smoke", version: "0.1.0" },
  });
  send({ jsonrpc: "2.0", method: "notifications/initialized" });

  const options = await callTool("list_options", {});
  const dialect = options.dialects.some((item) => item.id === "iec61131-3-ed3")
    ? "iec61131-3-ed3"
    : options.dialects[0].id;
  const common = {
    sources: [{ name: "main.st", content: source }],
    options: { dialect },
  };

  const checked = await callTool("check", common);
  if (!checked.ok) throw new Error(`check failed: ${JSON.stringify(checked.diagnostics)}`);

  const compiled = await callTool("compile", common);
  if (!compiled.ok) throw new Error(`compile failed: ${JSON.stringify(compiled.diagnostics)}`);

  const run = await callTool("run", {
    container_id: compiled.container_id,
    duration_ms: 1,
    variables: ["main.Button", "main.Buzzer"],
  });

  console.log(
    JSON.stringify(
      {
        server: initialized.serverInfo,
        dialect,
        check: { ok: checked.ok, diagnostics: checked.diagnostics },
        compile: {
          ok: compiled.ok,
          programs: compiled.programs,
          tasks: compiled.tasks,
        },
        run,
      },
      null,
      2,
    ),
  );
} finally {
  server.stdin.end();
  server.kill();
}
