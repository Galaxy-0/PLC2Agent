#!/usr/bin/env python3
# Deterministic plant + protocol adapter. All control decisions are compiled ST.
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import select
import subprocess
import sys

INPUTS = "StartPb StopPb ResetPb EStopOk CommFresh AutoMode DownstreamReady ReqValid ReqSeq AckValid AckSeq Extended Retracted RecipeCommit RecipeVersion RecipeTimeoutTicks RecipeDelayTicks".split()
OUTPUTS = "ExtendCmd RetractCmd FeedPermit Busy FaultLatched FaultCode State AcceptedSeq DoneSeq CompletedCount ActiveRecipeVersion ActiveTimeoutTicks ActiveDelayTicks CycleTimeoutTicks CycleDelayTicks RecipeRejected".split()
BOOL_INPUTS = set(INPUTS) - {"ReqSeq", "AckSeq", "RecipeVersion", "RecipeTimeoutTicks", "RecipeDelayTicks"}
FAULTS = {"actuator_stuck", "retract_stuck", "ack_drop", "ack_mismatch", "feedback_conflict", "communication_stale"}
DEFAULTS = dict.fromkeys(INPUTS, 0)
DEFAULTS.update(EStopOk=1, CommFresh=1, AutoMode=1, DownstreamReady=1, Retracted=1, RecipeTimeoutTicks=30, RecipeDelayTicks=2)


def bounded_child():
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))


class Harness:
    def __init__(self, binary, seed=17):
        if sys.platform != "linux":
            raise RuntimeError("Linux only: Mac is an SSH/client machine")
        self.binary = str(Path(binary).resolve())
        self.seed = seed
        self.travel_ticks = random.Random(seed).randint(4, 7)
        self.position = 0
        self.inputs = DEFAULTS.copy()
        self.faults = set()
        self.deliveries = []
        self.pending = 0
        self.ack_id = 0
        self.ack_age = 0
        self.records = []
        self.out = dict.fromkeys(OUTPUTS, 0)
        self.proc = subprocess.Popen([self.binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1, preexec_fn=bounded_child)

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        self.proc.stdout.close()
        self.proc.stderr.close()

    def set_inputs(self, changes):
        if not isinstance(changes, dict):
            raise ValueError("inputs must be an object")
        for key, value in changes.items():
            if key in {"Extended", "Retracted", "AckValid", "AckSeq"}:
                raise ValueError(f"plant-owned input: {key}")
            if key not in INPUTS:
                raise ValueError(f"unknown input: {key}")
            if not isinstance(value, (int, bool)) or not -(2**31) <= value < 2**31:
                raise ValueError(f"invalid integer input: {key}")
            if key in BOOL_INPUTS and value not in (0, 1):
                raise ValueError(f"invalid BOOL input: {key}")
            if key in {"RecipeTimeoutTicks", "RecipeDelayTicks"} and not -32768 <= value <= 32767:
                raise ValueError(f"invalid INT input: {key}")
        self.inputs.update({k: int(v) for k, v in changes.items()})

    def tick(self, **changes):
        if len(self.records) >= 10000:
            raise ValueError("scan budget reached; reset required")
        self.set_inputs(changes)
        sampled = self.inputs.copy()
        sampled["Extended"] = int(self.position == self.travel_ticks)
        sampled["Retracted"] = int(self.position == 0)
        sampled["AckValid"] = int(self.ack_id > 0 and self.ack_age >= 2 and "ack_drop" not in self.faults)
        sampled["AckSeq"] = self.ack_id + (99 if "ack_mismatch" in self.faults and self.ack_id else 0)
        if "feedback_conflict" in self.faults:
            sampled["Extended"] = sampled["Retracted"] = 1
        if "communication_stale" in self.faults:
            sampled["CommFresh"] = 0
        self.proc.stdin.write(" ".join(str(sampled[k]) for k in INPUTS) + "\n")
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], 2)[0]:
            self.proc.kill()
            raise RuntimeError("native ST scan timed out")
        line = self.proc.stdout.readline()
        values = [int(x) for x in line.split()]
        if len(values) != len(OUTPUTS):
            raise RuntimeError(f"invalid native ST response: {line!r}")
        self.out = dict(zip(OUTPUTS, values))
        before = self.position
        if self.out["ExtendCmd"] and not self.out["RetractCmd"]:
            if not self.pending and self.position == 0:
                self.pending = self.out["AcceptedSeq"]
            if "actuator_stuck" not in self.faults:
                self.position = min(self.travel_ticks, self.position + 1)
        elif self.out["RetractCmd"] and not self.out["ExtendCmd"]:
            if "retract_stuck" not in self.faults:
                self.position = max(0, self.position - 1)
        if before < self.travel_ticks and self.position == self.travel_ticks and self.pending:
            self.deliveries.append(self.pending)
            self.ack_id = self.pending
            self.ack_age = 0
        if self.ack_id:
            self.ack_age += 1
        if self.position == 0 and before > 0:
            self.pending = 0
            self.ack_id = 0
            self.ack_age = 0
        self.records.append({"scan": len(self.records), "time_ms": len(self.records) * 20,
                             "inputs_sampled": sampled, "outputs_commanded": self.out.copy(),
                             "plant_before": before, "plant_after": self.position,
                             "receiver_ledger": self.deliveries.copy()})
        return self.out

    def many(self, n, **changes):
        self.set_inputs(changes)
        for _ in range(n):
            self.tick()
        return self.out

    def start(self):
        self.tick(StartPb=1)
        self.tick(StartPb=0)

    def request(self, seq=11):
        return self.tick(ReqValid=1, ReqSeq=seq)

    def until(self, predicate, limit=150):
        for _ in range(limit):
            if predicate(self.out):
                return self.out
            self.tick()
        raise AssertionError("expected condition not reached within bounded scans")

    def reconcile_home(self):
        # Explicit fixture-only manual reconciliation, never real hardware movement.
        self.position = self.pending = self.ack_id = self.ack_age = 0

    def invariants(self):
        previous_count = 0
        for r in self.records:
            i, o = r["inputs_sampled"], r["outputs_commanded"]
            assert not (o["ExtendCmd"] and o["RetractCmd"]), "opposing actuator commands"
            if not i["EStopOk"] or not i["CommFresh"] or o["FaultLatched"]:
                assert not (o["ExtendCmd"] or o["RetractCmd"] or o["FeedPermit"]), "unsafe command after trip"
            if i["StopPb"]:
                assert not o["FeedPermit"], "feed accepted during drain"
            if o["CompletedCount"] > previous_count:
                assert i["Retracted"] and not i["Extended"], "completion before home confirmation"
                assert o["DoneSeq"] in r["receiver_ledger"], "completion without physical receiver event"
            previous_count = o["CompletedCount"]


def tests():
    def normal(h):
        h.start(); h.request(); h.until(lambda o: o["CompletedCount"] == 1)
        assert h.deliveries == [11] and h.out["DoneSeq"] == 11
    def duplicate(h):
        normal(h); h.many(100)
        assert h.out["CompletedCount"] == 1 and h.deliveries == [11]
    def backpressure(h):
        h.start(); h.tick(DownstreamReady=0, ReqValid=1, ReqSeq=11); h.many(60)
        assert h.out["AcceptedSeq"] == 0 and not h.deliveries and not h.out["Busy"]
        h.tick(DownstreamReady=1); h.until(lambda o: o["CompletedCount"] == 1)
    def drain(h):
        h.start(); h.request(); h.many(2); h.tick(StopPb=1, ReqSeq=12)
        h.until(lambda o: o["CompletedCount"] == 1); h.many(60)
        assert h.out["State"] == 0 and h.out["AcceptedSeq"] == 11 and h.deliveries == [11]
    def stale(h):
        h.start(); h.request(); h.faults.add("communication_stale"); h.tick()
        assert h.out["FaultCode"] == 102 and h.out["FaultLatched"]
        h.faults.clear(); h.many(5)
        assert h.out["FaultLatched"] and h.out["CompletedCount"] == 0
    def extend_timeout(h):
        h.faults.add("actuator_stuck"); h.start(); h.request()
        h.until(lambda o: o["FaultLatched"], 32)
        assert h.out["FaultCode"] == 201 and h.out["CompletedCount"] == 0
    def ack_mismatch(h):
        h.faults.add("ack_mismatch"); h.start(); h.request()
        h.until(lambda o: o["FaultLatched"], 50)
        assert h.out["FaultCode"] == 202 and h.out["CompletedCount"] == 0
    def ack_loss(h):
        h.faults.add("ack_drop"); h.start(); h.request()
        h.until(lambda o: o["FaultLatched"], 50)
        assert h.out["FaultCode"] == 202 and h.deliveries == [11]
    def retract_timeout(h):
        h.faults.add("retract_stuck"); h.start(); h.request()
        h.until(lambda o: o["FaultLatched"], 60)
        assert h.out["FaultCode"] == 203 and h.out["CompletedCount"] == 0
    def conflict(h):
        h.start(); h.request(); h.faults.add("feedback_conflict"); h.tick()
        assert h.out["FaultCode"] == 103
    def reset_edge(h):
        h.start(); h.request(); h.many(2); h.tick(EStopOk=0, ResetPb=1)
        assert h.out["FaultCode"] == 101
        h.reconcile_home(); h.tick(EStopOk=1, ReqValid=0, ResetPb=1)
        assert h.out["FaultLatched"], "held reset acknowledged restored trip"
        h.tick(ResetPb=0); h.tick(ResetPb=1)
        assert not h.out["FaultLatched"] and h.out["State"] == 0
        h.tick(ResetPb=0); h.request(11); h.start(); h.many(10)
        assert not h.out["Busy"], "faulted transaction replayed after reconciliation"
        h.request(12); h.until(lambda o: o["CompletedCount"] == 1)
        assert h.deliveries == [12]
    def mode_change(h):
        h.start(); h.request(); h.tick(AutoMode=0)
        assert h.out["FaultCode"] == 104
    def recipe(h):
        h.tick(RecipeCommit=1, RecipeVersion=1, RecipeTimeoutTicks=12, RecipeDelayTicks=3)
        assert h.out["ActiveRecipeVersion"] == 1
        h.tick(RecipeCommit=0); h.start(); h.request()
        h.tick(RecipeCommit=1, RecipeVersion=2, RecipeTimeoutTicks=100, RecipeDelayTicks=1)
        assert h.out["RecipeRejected"] and h.out["CycleTimeoutTicks"] == 12
        h.tick(RecipeCommit=0); h.until(lambda o: o["CompletedCount"] == 1)
        h.tick(RecipeCommit=1)
        assert h.out["ActiveRecipeVersion"] == 2 and h.out["ActiveTimeoutTicks"] == 100
    def invalid_recipe(h):
        h.tick(RecipeCommit=1, RecipeVersion=1, RecipeTimeoutTicks=0)
        assert h.out["RecipeRejected"] and h.out["ActiveTimeoutTicks"] == 30
        h.tick(RecipeCommit=0)
        h.tick(RecipeCommit=1, RecipeTimeoutTicks=10, RecipeDelayTicks=10)
        assert h.out["RecipeRejected"] and h.out["ActiveRecipeVersion"] == 0
    def first_fault(h):
        h.start(); h.request(); h.tick(EStopOk=0); h.faults.add("communication_stale"); h.tick()
        assert h.out["FaultCode"] == 101
    return [("normal_transfer", normal), ("duplicate_request", duplicate), ("downstream_backpressure", backpressure),
            ("controlled_drain", drain), ("communication_stale", stale), ("extend_timeout", extend_timeout),
            ("mismatched_ack", ack_mismatch), ("lost_ack", ack_loss), ("retract_timeout", retract_timeout),
            ("conflicting_feedback", conflict), ("reset_edge_and_reconcile", reset_edge), ("mode_change", mode_change),
            ("recipe_snapshot", recipe), ("invalid_recipe", invalid_recipe), ("first_fault_preserved", first_fault)]


def verify(binary, report_path, trace_dir):
    Path(trace_dir).mkdir(parents=True, exist_ok=True)
    results = []
    for name, run in tests():
        h = Harness(binary)
        error = None
        try:
            run(h); h.invariants()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            h.close()
        trace = "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in h.records)
        path = Path(trace_dir) / f"{name}.ndjson"
        path.write_text(trace)
        results.append({"case": name, "pass": error is None, "error": error,
                        "scans": len(h.records), "trace_sha256": hashlib.sha256(trace.encode()).hexdigest(),
                        "trace_file": str(path), "final": h.out, "receiver_ledger": h.deliveries})
    report = {"schema_version": 1, "kind": "reference_environment_verification", "scan_ms": 20, "seed": 17,
              "passed": sum(r["pass"] for r in results), "total": len(results), "cases": results}
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "total": report["total"], "report": str(report_path)}))
    return 0 if report["passed"] == report["total"] else 1


def cli(binary):
    h = Harness(binary)
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                op = request["op"]
                if op == "reset":
                    seed = request.get("seed", 17)
                    if type(seed) is not int or not 0 <= seed <= 2**31-1:
                        raise ValueError("seed must be an integer in 0..2147483647")
                    h.close(); h = Harness(binary, seed)
                elif op == "set_inputs":
                    h.set_inputs(request["inputs"])
                elif op == "inject_fault":
                    fault = request["fault"]
                    if fault not in FAULTS:
                        raise ValueError("unknown fault")
                    enabled = request.get("enabled", True)
                    if type(enabled) is not bool:
                        raise ValueError("enabled must be boolean")
                    h.faults.add(fault) if enabled else h.faults.discard(fault)
                elif op == "step":
                    scans = request.get("scans", 1)
                    if type(scans) is not int or not 1 <= scans <= 1000:
                        raise ValueError("scans must be an integer in 1..1000")
                    h.many(scans)
                elif op == "trace":
                    print(json.dumps({"ok": True, "records": h.records[-1000:]}), flush=True)
                    continue
                elif op != "snapshot":
                    raise ValueError("unsupported op")
                print(json.dumps({"ok": True, "scan": len(h.records), "seed": h.seed, "position": h.position,
                                  "outputs": h.out, "receiver_ledger": h.deliveries, "faults": sorted(h.faults)}), flush=True)
            except (ValueError, KeyError, TypeError) as exc:
                print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
    finally:
        h.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default=str(Path(__file__).parent / "build/cell-cli"))
    parser.add_argument("--report", default=str(Path(__file__).parent / "build/report.json"))
    parser.add_argument("--trace-dir", default=str(Path(__file__).parent / "build/traces"))
    parser.add_argument("--cli", action="store_true")
    args = parser.parse_args()
    if args.cli:
        cli(args.binary)
    else:
        sys.exit(verify(args.binary, args.report, args.trace_dir))
