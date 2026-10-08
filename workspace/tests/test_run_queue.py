"""Durable queue contract checks; fake execution is not native/scientific evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_queue import RunQueue, freeze_plan, load_plan, strict_json
from service import Workbench
from desktop_host import DesktopHost


def wait_for(check, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = check()
        if value:
            return value
        time.sleep(.005)
    raise AssertionError("Timed out waiting for queue state")


class Engine:
    def __init__(self):
        self.calls = []
        self.prepare_calls = []
        self.release = threading.Event()
        self.release.set()
        self.prepare_release = threading.Event()
        self.prepare_release.set()
        self.preparing = threading.Event()
        self.running = threading.Event()
        self.fail_name = None
        self.active = 0
        self.maximum_active = 0

    def prepare(self, graph, output, cancel=None, run_metadata=None):
        self.preparing.set()
        while not self.prepare_release.wait(.01):
            if cancel.is_set():
                raise InterruptedError("Preparation cancelled")
        if graph.get("name") == self.fail_name:
            raise ValueError("Fixture preparation failed")
        self.prepare_calls.append(copy.deepcopy(graph))
        folder = Path(output) / ("run-" + str(len(self.prepare_calls)))
        folder.mkdir()
        value = {"schema": 1, "folder": str(folder), "graph": copy.deepcopy(graph), "nodes": [], "references": {}}
        if run_metadata:
            value["batch"] = copy.deepcopy(run_metadata)
        value["sha256"] = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        (folder / "plan.json").write_text(json.dumps(value))
        for name in ("graph.json", "workflow.cwl", "methods-planned.txt", "pipeline.svg", "performance.json"):
            (folder / name).write_text("fixture")
        return value

    def execute(self, plan, event, cancel):
        self.calls.append(copy.deepcopy(plan))
        self.active += 1
        self.maximum_active = max(self.active, self.maximum_active)
        self.running.set()
        try:
            while not self.release.wait(.01):
                if cancel.is_set():
                    return {"status": "cancelled"}
            if cancel.is_set():
                return {"status": "cancelled"}
            return {"status": "success", "batch": plan.get("batch")}
        finally:
            self.active -= 1


class Model:
    def __init__(self):
        self.graph = {"name": "Draft", "nodes": [], "sources": []}
    def snapshot(self):
        return {"graph": copy.deepcopy(self.graph)}
    def dispatch(self, action, payload):
        if action == "rename":
            self.graph["name"] = payload["name"]
    def update_catalog(self, catalog):
        pass


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="queue-contract-")
        self.root = Path(self.tmp.name)
        self.engine = Engine()
        self.app = Workbench(self.root, engine=self.engine, catalog={"tools": {}})
        self.host = DesktopHost(self.root, app=self.app, model=Model())

    def tearDown(self):
        self.engine.release.set()
        self.engine.prepare_release.set()
        self.host.close(grace=3)
        self.tmp.cleanup()

    def add(self, name="Frozen"):
        result = self.host.dispatch("queue/add", {"output_folder": str(self.root), "graph": {"name": name}})
        wait_for(lambda: not self.app.queue_state()["preparing"])
        return result["added"][0]

    def finish(self):
        wait_for(lambda: not self.app.queue_state()["queue_running"])
        return self.app.queue_state()

    def test_enqueue_freezes_graph_without_starting_and_serial_start_runs_only_selected_jobs(self):
        one, two = self.add("first"), self.add("second")
        self.assertEqual(self.engine.calls, [])
        self.engine.release.clear()
        self.host.dispatch("queue/start", {})
        self.assertTrue(self.engine.running.wait(2))
        self.host.dispatch("model", {"action": "rename", "payload": {"name": "Next draft"}})
        three = self.add("third")
        self.assertTrue(self.host.snapshot()["workspace_editable"])
        self.engine.release.set()
        state = self.finish()
        self.assertEqual([p["graph"]["name"] for p in self.engine.calls], ["first", "second"])
        self.assertEqual(self.engine.maximum_active, 1)
        self.assertEqual({j["job_id"]: j["status"] for j in state["jobs"]}, {one: "completed", two: "completed", three: "queued"})
        self.assertEqual(self.host.graph()["name"], "Next draft")

    def test_reopen_keeps_pending_jobs_paused_and_converts_abandoned_job_to_interrupted(self):
        one, two = self.add("first"), self.add("second")
        self.app.run_queue.update([one], status="running")
        self.host.close()
        self.app = Workbench(self.root, engine=self.engine, catalog={"tools": {}})
        self.host = DesktopHost(self.root, app=self.app, model=Model())
        state = self.app.queue_state()
        self.assertTrue(state["paused"])
        self.assertEqual([j["status"] for j in state["jobs"]], ["interrupted", "queued"])
        self.assertFalse(self.engine.calls)
        self.host.dispatch("queue/start", {})
        self.finish()
        self.assertEqual([p["graph"]["name"] for p in self.engine.calls], ["second"])

    def test_second_host_is_read_only_and_does_not_relabel_live_run(self):
        identity = self.add()
        self.app.run_queue.update([identity], status="running")
        other = Workbench(self.root, engine=Engine(), catalog={"tools": {}})
        try:
            self.assertIn("read-only", other.queue_state()["error"])
            self.assertEqual(other.queue_state()["jobs"][0]["status"], "running")
            with self.assertRaisesRegex(ValueError, "owns this installation"):
                other.start({"output_folder": str(self.root), "graph": {}})
            with self.assertRaises(ValueError):
                other.enqueue({"output_folder": str(self.root), "graph": {}})
            other.ensure_model_editable()
        finally:
            other.shutdown()

    def test_plan_companion_mutation_fails_before_engine_and_pauses_remaining(self):
        one, two = self.add("first"), self.add("second")
        job = self.app.queue_state()["jobs"][0]
        (Path(job["folder"]) / "workflow.cwl").write_text("modified")
        self.host.dispatch("queue/start", {})
        state = self.finish()
        self.assertEqual([j["status"] for j in state["jobs"]], ["failed", "queued"])
        self.assertIn("changed", state["jobs"][0]["message"])
        self.assertFalse(self.engine.calls)

    def test_added_output_or_prior_run_marker_refuses_rerun(self):
        self.add()
        job = self.app.queue_state()["jobs"][0]
        (Path(job["folder"]) / "run.json").write_text("{}")
        self.host.dispatch("queue/start", {})
        self.assertEqual(self.finish()["jobs"][0]["status"], "failed")
        self.assertFalse(self.engine.calls)

    def test_cancel_preparing_is_responsive_and_never_becomes_ready(self):
        self.engine.prepare_release.clear()
        result = self.host.dispatch("queue/add", {"output_folder": str(self.root), "graph": {"name": "slow"}})
        self.assertTrue(self.engine.preparing.wait(2))
        before = time.monotonic()
        self.assertTrue(self.host.dispatch("queue/status", {})["preparing"])
        self.host.dispatch("queue/cancel", {"job_id": result["added"][0]})
        self.assertLess(time.monotonic() - before, .5)
        wait_for(lambda: not self.app.queue_state()["preparing"])
        self.assertEqual(self.app.queue_state()["jobs"][0]["status"], "cancelled")
        self.assertFalse(self.engine.calls)

    def test_pause_leaves_active_job_running_and_cancel_pauses_next(self):
        one, two = self.add("first"), self.add("second")
        self.engine.release.clear()
        self.app.start_queue()
        self.assertTrue(self.engine.running.wait(2))
        self.app.pause_queue()
        self.assertEqual(self.app.queue_state()["scheduled"], [])
        self.assertEqual(self.app.get_run(one)["status"], "running")
        self.app.cancel_queued(one)
        state = self.finish()
        self.assertEqual([j["status"] for j in state["jobs"]], ["cancelled", "queued"])
        self.assertEqual(len(self.engine.calls), 1)

    def test_cancel_pending_does_not_cancel_other_jobs(self):
        one, two = self.add("first"), self.add("second")
        self.app.cancel_queued(one)
        self.app.start_queue()
        state = self.finish()
        self.assertEqual([j["status"] for j in state["jobs"]], ["cancelled", "completed"])

    def test_legacy_run_and_queue_share_execution_guard(self):
        self.add()
        self.engine.release.clear()
        self.app.start_queue()
        self.assertTrue(self.engine.running.wait(2))
        with self.assertRaisesRegex(ValueError, "active analysis|already running"):
            self.host.dispatch("run", {"output_folder": str(self.root)})
        with self.assertRaisesRegex(ValueError, "active analysis"):
            self.app.start_pack_operation("refresh", {})
        with self.assertRaisesRegex(ValueError, "active analysis"):
            self.app.start_queue()

    def test_state_disk_failure_leaves_previous_bytes_and_memory_intact(self):
        self.add()
        before = self.app.run_queue.path.read_bytes()
        snapshot = self.app.run_queue.snapshot()
        with patch("run_queue.os.replace", side_effect=OSError("fixture disk failure")):
            with self.assertRaises(OSError):
                self.app.run_queue.update([snapshot["jobs"][0]["job_id"]], message="changed")
        self.assertEqual(self.app.run_queue.path.read_bytes(), before)
        self.assertEqual(self.app.run_queue.snapshot(), snapshot)
        self.assertEqual(list(self.app.data.glob("run-queue.json.*.tmp")), [])

    def test_store_commit_does_not_hold_status_or_app_lock(self):
        self.add()
        entered, release, observed = threading.Event(), threading.Event(), threading.Event()
        original = self.app.run_queue._write
        def delayed(value):
            entered.set()
            if not release.wait(3):
                raise AssertionError("No fixture release")
            return original(value)
        with patch.object(self.app.run_queue, "_write", side_effect=delayed):
            worker = threading.Thread(target=lambda: self.app.cancel_queued(self.app.queue_state()["jobs"][0]["job_id"]))
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                other = threading.Thread(target=lambda: (self.app.activity(), self.app.queue_state(), observed.set()))
                other.start()
                self.assertTrue(observed.wait(.5))
            finally:
                release.set()
                worker.join(3)
                other.join(3)

    def test_corrupt_state_is_retained_and_all_execution_fails_closed(self):
        self.host.close()
        path = self.root / "user-data/run-queue.json"
        for raw in ('{"schema":1,"schema":1,"jobs":[]}', '{"schema":true,"jobs":[]}', '{invalid'):
            path.write_text(raw)
            store = RunQueue(self.app.data)
            try:
                self.assertTrue(store.error)
                with self.assertRaises(ValueError):
                    store.ready()
                self.assertEqual(path.read_text(), raw)
            finally:
                store.close()

    def test_batch_preview_token_is_immutable_single_use_and_retains_frozen_metadata(self):
        samples = [{"sampleId": "sample-A", "metadata": {"condition": "case"}, "graph": {"name": "Reviewed A"}},
                   {"sampleId": "sample-B", "metadata": {"condition": "control"}, "graph": {"name": "Reviewed B"}}]
        with patch("sample_table.preview_batch", return_value={"valid": True, "samples": samples}):
            preview = self.app.preview_batch({"graph": {}, "table": {}, "bindings": []})
        self.assertNotIn("graph", preview["samples"][0])
        samples[0]["graph"]["name"] = "unreviewed change"
        self.app.enqueue({"token": preview["token"], "output_folder": str(self.root)}, batch=True)
        wait_for(lambda: not self.app.queue_state()["preparing"])
        with self.assertRaisesRegex(ValueError, "expired"):
            self.app.enqueue({"token": preview["token"], "output_folder": str(self.root)}, batch=True)
        self.app.start_queue()
        self.finish()
        self.assertEqual(self.engine.calls[0]["graph"]["name"], "Reviewed A")
        self.assertEqual(self.engine.calls[0]["batch"]["sampleId"], "sample-A")
        self.assertEqual(self.engine.calls[0]["batch"]["metadata"], {"condition": "case"})

    def test_batch_preparation_failure_never_queues_a_partial_batch(self):
        self.engine.fail_name = "bad"
        samples = [{"sampleId": "A", "metadata": {}, "graph": {"name": "good"}},
                   {"sampleId": "B", "metadata": {}, "graph": {"name": "bad"}}]
        with patch("sample_table.preview_batch", return_value={"valid": True, "samples": samples}):
            preview = self.app.preview_batch({"graph": {}, "table": {}, "bindings": []})
        self.app.enqueue({"token": preview["token"], "output_folder": str(self.root)}, batch=True)
        wait_for(lambda: not self.app.queue_state()["preparing"])
        self.assertEqual([job["status"] for job in self.app.queue_state()["jobs"]], ["failed", "failed"])
        with self.assertRaisesRegex(ValueError, "no prepared"):
            self.app.start_queue()
        self.assertFalse(self.engine.calls)

    def saturated_cancel(self, preparing):
        import desktop_host
        if preparing:
            self.engine.prepare_release.clear()
            job = self.app.enqueue({"graph": {"name": "preparing"}, "output_folder": str(self.root)})["added"][0]
            self.assertTrue(self.engine.preparing.wait(2))
        else:
            job = self.add()
            self.engine.release.clear()
            self.app.start_queue()
            self.assertTrue(self.engine.running.wait(2))
        class Input:
            lines = queue.Queue()
            def readline(self, limit):
                return self.lines.get(timeout=10)
        class Output:
            replies = queue.Queue()
            def write(self, data):
                self.replies.put(json.loads(data))
            def flush(self):
                pass
        incoming, outgoing = Input(), Output()
        entered, release, count_lock = threading.Event(), threading.Event(), threading.Lock()
        count, closed = [0], []
        def delayed(*args, **kwargs):
            with count_lock:
                count[0] += 1
                if count[0] == 2:
                    entered.set()
            if not release.wait(5):
                raise AssertionError("Slow request fixture was not released")
            return {"verified": True}
        def send(identity, method, params=None):
            incoming.lines.put((json.dumps({"id": identity, "method": method, "params": params or {}}) + "\n").encode())
        with patch("reference_indexes.ReferenceIndexStore") as store:
            store.return_value.verify.side_effect = delayed
            worker = threading.Thread(target=lambda: closed.append(desktop_host.serve(self.host, incoming, outgoing)))
            worker.start()
            try:
                send(1, "index/verify", {"key": "a" * 64})
                send(2, "index/verify", {"key": "b" * 64})
                self.assertTrue(entered.wait(2), "Both slow slots must be occupied")
                send(3, "queue/status")
                reply = outgoing.replies.get(timeout=1)
                self.assertEqual(reply["id"], 3)
                self.assertTrue(reply["ok"])
                send(4, "queue/cancel", {"job_id": job})
                reply = outgoing.replies.get(timeout=1)
                self.assertEqual(reply["id"], 4)
                self.assertTrue(reply["ok"], reply)
                signal = self.app._queue_prepare_cancel if preparing else self.app.runs[job]["_cancel"]
                self.assertTrue(signal.is_set())
                send(5, "queue/cancel", {"job_id": job, "unexpected": True})
                reply = outgoing.replies.get(timeout=1)
                self.assertEqual(reply["id"], 5)
                self.assertFalse(reply["ok"])
            finally:
                release.set()
                incoming.lines.put(b"")
                worker.join(6)
        self.assertFalse(worker.is_alive())
        self.assertEqual(closed, [True])

    def test_active_cancel_bypasses_two_saturated_slow_workers(self):
        self.saturated_cancel(preparing=False)

    def test_preparing_cancel_bypasses_two_saturated_slow_workers(self):
        self.saturated_cancel(preparing=True)

    def test_unicode_metadata_uses_same_canonical_budget_as_frozen_plan(self):
        metadata = {"note": "界" * 4000}
        samples = [{"sampleId": "A", "metadata": metadata, "graph": {"name": "Unicode"}}]
        with patch("sample_table.preview_batch", return_value={"valid": True, "samples": samples}):
            preview = self.app.preview_batch({"graph": {}, "table": {}, "bindings": []})
        self.app.enqueue({"token": preview["token"], "output_folder": str(self.root)}, batch=True)
        wait_for(lambda: not self.app.queue_state()["preparing"])
        self.assertEqual(self.app.queue_state()["jobs"][0]["status"], "queued")
        self.assertEqual(self.app.run_queue.snapshot()["jobs"][0]["metadata"], metadata)

    def test_wide_table_and_many_preview_issues_are_byte_bounded_with_omissions(self):
        path = self.root / "wide.csv"
        path.write_text("sample_id,a,b,c,d,e,f,g,h\n" + "".join(
            "S" + str(i) + "," + ",".join(["界" * 4000] * 8) + "\n" for i in range(50)), encoding="utf-8")
        table = self.app.import_sample_table(str(path))
        self.assertGreater(table["preview_omitted"], 0)
        self.assertLess(len(json.dumps(table)), 270 * 1024)
        with patch("sample_table.preview_batch", return_value={"valid": False, "samples": [],
                   "errors": [{"message": "界" * 4000} for _ in range(300)], "warnings": []}):
            preview = self.app.preview_batch({"graph": {}, "table": {}, "bindings": []})
        self.assertFalse(preview["valid"])
        self.assertGreater(preview["errors_omitted"], 0)
        self.assertLess(len(json.dumps(preview)), 270 * 1024)

    def test_pending_cancel_is_reserved_before_start_even_during_slow_disk_write(self):
        identity = self.add()
        entered, release = threading.Event(), threading.Event()
        original = self.app.run_queue.update
        errors = []
        def delayed(identities, **values):
            if values.get("status") == "cancelled":
                entered.set()
                if not release.wait(3):
                    raise AssertionError("No fixture release")
            return original(identities, **values)
        def cancel():
            try:
                self.app.cancel_queued(identity)
            except Exception as error:
                errors.append(error)
        with patch.object(self.app.run_queue, "update", side_effect=delayed):
            worker = threading.Thread(target=cancel)
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaisesRegex(ValueError, "no prepared"):
                    self.app.start_queue()
                self.assertFalse(self.engine.calls)
            finally:
                release.set()
                worker.join(3)
        self.assertEqual(errors, [])
        self.assertEqual(self.app.queue_state()["jobs"][0]["status"], "cancelled")

    def test_abrupt_process_exit_releases_os_lock_and_marks_preparation_interrupted(self):
        data = self.root / "crashed-host"
        data.mkdir()
        code = """
import os, sys
sys.path.insert(0, sys.argv[1])
from run_queue import RunQueue
store = RunQueue(sys.argv[2])
store.add([{'graph': {'name': 'Interrupted child'}}], '1' * 32)
os._exit(0)
"""
        result = subprocess.run([sys.executable, "-I", "-c", code,
                                 str(Path(__file__).resolve().parents[1]), str(data)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        recovered = RunQueue(data)
        try:
            self.assertTrue(recovered.owned)
            self.assertEqual(recovered.snapshot()["jobs"][0]["status"], "interrupted")
        finally:
            recovered.close()

    def test_shutdown_waits_for_queue_admission_then_cancels_without_execution(self):
        entered, release = threading.Event(), threading.Event()
        original = self.app.run_queue.add
        errors, closed = [], []
        def delayed(*args):
            entered.set()
            if not release.wait(3):
                raise AssertionError("No fixture release")
            return original(*args)
        def enqueue():
            try:
                self.app.enqueue({"graph": {"name": "close race"}, "output_folder": str(self.root)})
            except Exception as error:
                errors.append(error)
        with patch.object(self.app.run_queue, "add", side_effect=delayed):
            worker = threading.Thread(target=enqueue)
            worker.start()
            self.assertTrue(entered.wait(2))
            closer = threading.Thread(target=lambda: closed.append(self.host.close(grace=3)))
            closer.start()
            wait_for(lambda: self.app._closing)
            self.assertTrue(self.app.run_queue.owned)
            release.set()
            worker.join(3)
            closer.join(3)
        self.assertEqual(errors, [])
        self.assertEqual(closed, [True])
        self.assertFalse(self.engine.calls)
        recovered = RunQueue(self.app.data)
        try:
            self.assertEqual(recovered.snapshot()["jobs"][0]["status"], "cancelled")
        finally:
            recovered.close()

    def test_table_token_bounds_response_and_keeps_import_bytes_after_file_edit(self):
        path = self.root / "samples.csv"
        path.write_text("sample_id,file\n" + "".join(f"S{i},file{i}.txt\n" for i in range(150)))
        imported = self.host.dispatch("sample/table", {"path": str(path)})
        self.assertEqual(imported["rowCount"], 150)
        self.assertEqual(len(imported["rows"]), 100)
        self.assertEqual(imported["preview_omitted"], 50)
        path.write_text("sample_id,file\nchanged,different.txt\n")
        with patch("sample_table.preview_batch", return_value={"valid": False, "samples": []}) as preview:
            self.host.dispatch("sample/preview", {"table_token": imported["table_token"], "bindings": []})
            self.assertEqual(len(preview.call_args.args[2]["rows"]), 150)
            self.assertEqual(preview.call_args.args[2]["rows"][0]["sample_id"], "S0")
        with patch("service.time.monotonic", return_value=time.monotonic() + 901):
            with self.assertRaisesRegex(ValueError, "expired"):
                self.host.dispatch("sample/preview", {"table_token": imported["table_token"], "bindings": []})


if __name__ == "__main__":
    unittest.main(verbosity=2)
