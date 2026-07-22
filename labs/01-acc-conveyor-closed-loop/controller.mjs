#!/usr/bin/env node

import net from "node:net";

function arg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const host = arg("--host", "127.0.0.1");
const port = Number(arg("--port", "5020"));
const scanMs = Number(arg("--scan-ms", "50"));
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

const client = new ModbusTcpClient();
let running = false;
let reverse = false;
let previousStart = false;
let completedCycles = 0;
let stopping = false;
let previousTrace = "";
let previousOutputs = "";

function trace(message) {
  const now = new Date();
  const clock = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
  const milliseconds = String(now.getMilliseconds()).padStart(3, "0");
  console.log(`${clock}.${milliseconds} ${message}`);
}

async function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;
  try {
    await client.writeMultipleCoils(0, [false, false]);
  } catch {
    // The bridge may already be gone; shutdown still needs to complete.
  }
  client.close();
  process.exitCode = exitCode;
}

process.on("SIGINT", () => void stop());
process.on("SIGTERM", () => void stop());

try {
  await client.connect();
  trace(`CONNECTED modbus://${host}:${port} scan=${scanMs}ms`);

  while (!stopping) {
    const [start, stopHealthy, leftSensor, rightSensor] =
      await client.readDiscreteInputs(0, 4);

    if (start && !previousStart) {
      running = true;
      reverse = false;
      trace("X1 START rising edge -> Y1 RUN forward");
    }

    if (!stopHealthy && running) {
      running = false;
      reverse = false;
      trace("X2 STOP opened -> outputs de-energized");
    }

    if (running && !reverse && rightSensor) {
      reverse = true;
      trace("X4 RIGHT sensor -> Y2 REVERSE");
    }

    if (running && reverse && leftSensor) {
      running = false;
      reverse = false;
      completedCycles += 1;
      trace(`X3 LEFT sensor -> cycle ${completedCycles} complete, STOP`);
    }

    const outputs = `${Number(running)}${Number(running && reverse)}`;
    if (outputs !== previousOutputs) {
      await client.writeMultipleCoils(0, [running, running && reverse]);
      previousOutputs = outputs;
    }

    const state = `X=${Number(start)}${Number(stopHealthy)}${Number(leftSensor)}${Number(rightSensor)} ` +
      `Y=${outputs}`;
    if (state !== previousTrace) {
      trace(state);
      previousTrace = state;
    }

    previousStart = start;
    if (exitAfterCycle && completedCycles > 0) break;
    await new Promise((resolve) => setTimeout(resolve, scanMs));
  }

  await stop();
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  await stop(1);
}
