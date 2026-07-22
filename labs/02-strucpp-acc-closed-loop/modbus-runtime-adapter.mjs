#!/usr/bin/env node

import { spawn } from "node:child_process";
import { once } from "node:events";
import net from "node:net";
import path from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

function arg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const host = arg("--host", "127.0.0.1");
const port = Number(arg("--port", "5020"));
const scanMs = Number(arg("--scan-ms", "50"));
const runtimePath = path.resolve(arg("--runtime", path.join(scriptDir, "build/conveyor")));
const exitAfterCycle = process.argv.includes("--exit-after-cycle");

class ModbusTcpClient {
  constructor() {
    this.socket = null;
    this.buffer = Buffer.alloc(0);
    this.transactionId = 0;
    this.pending = new Map();
  }

  async connect() {
    this.socket = net.createConnection({ host, port });
    this.socket.on("data", (chunk) => this.onData(chunk));
    this.socket.on("error", (error) => this.rejectAll(error));
    this.socket.on("close", () => this.rejectAll(new Error("Modbus connection closed")));
    await new Promise((resolve, reject) => {
      this.socket.once("connect", resolve);
      this.socket.once("error", reject);
    });
  }

  close() {
    this.socket?.end();
  }

  rejectAll(error) {
    for (const { reject, timer } of this.pending.values()) {
      clearTimeout(timer);
      reject(error);
    }
    this.pending.clear();
  }

  onData(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (this.buffer.length >= 7) {
      const frameLength = 6 + this.buffer.readUInt16BE(4);
      if (this.buffer.length < frameLength) return;
      const frame = this.buffer.subarray(0, frameLength);
      this.buffer = this.buffer.subarray(frameLength);

      const id = frame.readUInt16BE(0);
      const pending = this.pending.get(id);
      if (!pending) continue;
      this.pending.delete(id);
      clearTimeout(pending.timer);

      const pdu = frame.subarray(7);
      if (pdu[0] & 0x80) {
        pending.reject(new Error(`Modbus exception ${pdu[1]} for FC${pdu[0] & 0x7f}`));
      } else {
        pending.resolve(pdu);
      }
    }
  }

  request(pdu) {
    this.transactionId = (this.transactionId + 1) & 0xffff;
    const id = this.transactionId;
    const frame = Buffer.alloc(7 + pdu.length);
    frame.writeUInt16BE(id, 0);
    frame.writeUInt16BE(0, 2);
    frame.writeUInt16BE(1 + pdu.length, 4);
    frame[6] = 1;
    pdu.copy(frame, 7);

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Modbus request ${id} timed out`));
      }, 1000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.write(frame);
    });
  }

  async readDiscreteInputs(start, count) {
    const pdu = Buffer.alloc(5);
    pdu[0] = 0x02;
    pdu.writeUInt16BE(start, 1);
    pdu.writeUInt16BE(count, 3);
    const response = await this.request(pdu);
    return Array.from({ length: count }, (_, index) =>
      Boolean((response[2 + Math.floor(index / 8)] >> (index % 8)) & 1),
    );
  }

  async writeMultipleCoils(start, values) {
    const byteCount = Math.ceil(values.length / 8);
    const pdu = Buffer.alloc(6 + byteCount);
    pdu[0] = 0x0f;
    pdu.writeUInt16BE(start, 1);
    pdu.writeUInt16BE(values.length, 3);
    pdu[5] = byteCount;
    values.forEach((value, index) => {
      if (value) pdu[6 + Math.floor(index / 8)] |= 1 << (index % 8);
    });
    await this.request(pdu);
  }
}

class StructuredTextRuntime {
  constructor(executable) {
    this.process = spawn(executable, [], { stdio: ["pipe", "pipe", "pipe"] });
    this.waiter = null;
    this.closed = false;

    const output = createInterface({ input: this.process.stdout });
    output.on("line", (line) => this.onLine(line));
    this.process.stderr.on("data", (chunk) => process.stderr.write(chunk));
    this.process.stdin.on("error", (error) => {
      if (error.code !== "EPIPE") console.error(`ST runtime stdin: ${error.message}`);
    });
    this.process.on("exit", (code, signal) => {
      this.closed = true;
      this.waiter?.reject(new Error(`ST runtime exited: code=${code} signal=${signal}`));
      this.waiter = null;
    });
  }

  onLine(line) {
    if (!this.waiter) return;
    if (/^(Unknown|Usage:|ERR:|Error:)/.test(line)) {
      const { reject, timer } = this.waiter;
      this.waiter = null;
      clearTimeout(timer);
      reject(new Error(`ST runtime rejected command: ${line}`));
      return;
    }
    if (!this.waiter.match(line)) return;
    const { resolve, timer } = this.waiter;
    this.waiter = null;
    clearTimeout(timer);
    resolve(line);
  }

  waitFor(match, label) {
    if (this.closed) return Promise.reject(new Error("ST runtime is not running"));
    if (this.waiter) return Promise.reject(new Error("Concurrent ST runtime commands are not supported"));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.waiter = null;
        reject(new Error(`Timed out waiting for ST runtime: ${label}`));
      }, 2000);
      this.waiter = { match, resolve, reject, timer };
    });
  }

  async start() {
    await this.waitFor((line) => line.startsWith("Type help for commands"), "startup banner");
  }

  async command(command, match) {
    const response = this.waitFor(match, command);
    this.process.stdin.write(`${command}\n`);
    return response;
  }

  async setBool(name, value) {
    const expected = value ? "TRUE" : "FALSE";
    await this.command(
      `set CONVEYOR.${name} ${expected}`,
      (line) => line === `CONVEYOR.${name} = ${expected}`,
    );
  }

  async getBool(name) {
    const line = await this.command(
      `get CONVEYOR.${name}`,
      (candidate) => candidate.startsWith(`CONVEYOR.${name} : BOOL = `),
    );
    return line.endsWith("TRUE");
  }

  async scan([start, stopHealthy, leftSensor, rightSensor]) {
    await this.setBool("START", start);
    await this.setBool("STOPHEALTHY", stopHealthy);
    await this.setBool("LEFTSENSOR", leftSensor);
    await this.setBool("RIGHTSENSOR", rightSensor);
    await this.command("step", (line) => line.startsWith("Executed 1 cycle(s)."));

    return {
      motor: await this.getBool("MOTOR"),
      reverse: await this.getBool("REVERSE"),
      cycleComplete: await this.getBool("CYCLECOMPLETE"),
      faultLatched: await this.getBool("FAULTLATCHED"),
    };
  }

  async close() {
    if (this.closed) return;
    if (!this.process.stdin.destroyed) this.process.stdin.write("exit\n");
    await Promise.race([
      once(this.process, "exit"),
      new Promise((resolve) => setTimeout(resolve, 1000)),
    ]);
    if (!this.closed) this.process.kill("SIGTERM");
  }
}

function trace(message) {
  const now = new Date();
  const clock = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
  const milliseconds = String(now.getMilliseconds()).padStart(3, "0");
  console.log(`${clock}.${milliseconds} ${message}`);
}

const modbus = new ModbusTcpClient();
const runtime = new StructuredTextRuntime(runtimePath);
let stopping = false;
let previousState = "";
let previousOutputs = "";
let completedCycles = 0;

async function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;
  try {
    await modbus.writeMultipleCoils(0, [false, false]);
  } catch {
    // Safe shutdown still proceeds if the simulator bridge is already gone.
  }
  modbus.close();
  await runtime.close();
  process.exitCode = exitCode;
}

process.on("SIGINT", () => void stop());
process.on("SIGTERM", () => void stop());

try {
  await runtime.start();
  await modbus.connect();
  trace(`CONNECTED ST=${runtimePath} modbus://${host}:${port} scan=${scanMs}ms`);

  while (!stopping) {
    const inputs = await modbus.readDiscreteInputs(0, 4);
    const outputs = await runtime.scan(inputs);
    const outputSignature = `${Number(outputs.motor)}${Number(outputs.reverse)}`;

    if (outputSignature !== previousOutputs) {
      await modbus.writeMultipleCoils(0, [outputs.motor, outputs.reverse]);
      previousOutputs = outputSignature;
    }

    if (outputs.cycleComplete) {
      completedCycles += 1;
      trace(`ST CYCLE_COMPLETE pulse -> cycle ${completedCycles} complete`);
    }

    const inputSignature = inputs.map(Number).join("");
    const state = `X=${inputSignature} ST.motor=${Number(outputs.motor)} ` +
      `ST.reverse=${Number(outputs.reverse)} ST.fault=${Number(outputs.faultLatched)} ` +
      `Y=${outputSignature}`;
    if (state !== previousState) {
      trace(state);
      previousState = state;
    }

    if (exitAfterCycle && completedCycles > 0) break;
    await new Promise((resolve) => setTimeout(resolve, scanMs));
  }

  await stop();
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  await stop(1);
}
