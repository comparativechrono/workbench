"""Shared local workbench operations, independent of any UI transport.

Desktop stdio and the historical browser prototype use the same execution,
validation, persistence and native runner implementation in this module.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
import uuid

from catalog import load_catalog, load_pack
from engine import Engine

MAX_PUBLIC_LOG_BYTES = 256 * 1024
MAX_RECENT_BYTES = 3 * 1024 * 1024
MAX_HISTORY_BYTES = 12 * 1024 * 1024
MAX_SAVED_BYTES = 12 * 1024 * 1024

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def strict_json(data):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad_constant)


def short_text(value, label, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid " + label)
    return value.strip()


class Workbench:
    def __init__(self, app_root, *, engine=None, catalog=None):
        self.root = Path(app_root).resolve()
        self.web = self.root / "workspace" / "web"
        self.data = self.root / "user-data"
        self.data.mkdir(exist_ok=True)
        self.catalog = catalog if catalog is not None else load_catalog(self.root)
        self.engine = engine or Engine(self.root, self.catalog)
        self.lock = threading.RLock()
        self.dialog_lock = threading.Lock()
        self._processes = set()
        self._closing = False
        self._changing_packs = False
        self._pack_manager = None
        self._pack_worker = None
        self._pack_cancel = threading.Event()
        self._pack_listing = None
        self._setup_manager = None
        self._setup_worker = None
        self._setup_cancel = threading.Event()
        self._pack_operation = {"id": "", "active": False, "status": "idle",
                                "message": "", "bytes": 0, "total": 0, "cancellable": False}
        self._changing_references = False
        self._reference_manager = None
        self._reference_worker = None
        self._reference_cancel = threading.Event()
        self._reference_listing = None
        self._reference_operation = {"id": "", "active": False, "status": "idle",
                                     "message": "", "bytes": 0, "total": 0, "cancellable": False}
        self.runs = {}
        self.last_seen = time.monotonic()
        self.token = secrets.token_urlsafe(32)
        self.saved_path = self.data / "saved.json"
        self.history_path = self.data / "runs.json"
        self.history = self.read_json(self.history_path, [])
        # A previous host cannot still own an active run after a normal restart.
        # Keep these records explicitly interrupted; never infer success.
        for run in self.history:
            if run.get("status") in ("preparing", "running", "cancelling"):
                run["status"] = "interrupted"
                run["message"] = "The previous workbench session ended before completion. Inspect the recorded run folder."

    @staticmethod
    def read_json(path, default):
        if not path.exists():
            return copy.deepcopy(default)
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Saved workspace file is too large: " + str(path))
        return strict_json(path.read_text(encoding="utf-8"))

    def active(self):
        with self.lock:
            return any(run["status"] in ("preparing", "running", "cancelling") for run in self.runs.values())

    def activity(self):
        with self.lock:
            identity = next((r["run_id"] for r in self.runs.values()
                             if r["status"] in ("preparing", "running", "cancelling")), None)
            return {"active": identity is not None, "active_run": identity,
                    "changing_packs": self._changing_packs,
                    "changing_references": self._changing_references, "closing": self._closing}

    def recent(self, summaries=False):
        with self.lock:
            items = list(self.runs.values()) + [r for r in self.history if r["run_id"] not in self.runs]
            runs, size = [], 0
            for run in list(reversed(list(self.runs.values()))) + [r for r in self.history if r["run_id"] not in self.runs]:
                public = self.public_run(run)
                if summaries:
                    public = {key: public[key] for key in
                              ("run_id", "id", "name", "status", "folder", "started", "started_at",
                               "finished", "finished_at", "success", "cancelled") if key in public}
                    public["node_count"] = len(run.get("nodes", []))
                length = len(json.dumps(public, ensure_ascii=True).encode("utf-8"))
                if size + length > MAX_RECENT_BYTES:
                    continue
                runs.append(public)
                size += length
            return {"runs": runs, "omitted": len(items) - len(runs),
                    "note": "Older or large recent records may be omitted here. Full results remain in their recorded folders."}

    def ensure_editable(self):
        with self.lock:
            if self._closing:
                raise ValueError("The workbench is closing.")
            if self._changing_packs:
                raise ValueError("Wait for the pack operation to finish.")
            if self._changing_references:
                raise ValueError("Wait for the reference operation to finish or cancel it.")
            if self.active():
                raise ValueError("Wait for the active analysis to finish or cancel it before changing the workspace.")

    def saved(self):
        value = self.read_json(self.saved_path, {"pipelines": [], "presets": []})
        if not isinstance(value, dict) or not all(isinstance(value.get(k), list) for k in ("pipelines", "presets")):
            raise ValueError("Saved analyses cannot be read. Keep user-data/saved.json for recovery.")
        return value

    def saved_summaries(self):
        """Small picker records; full bindings-free templates stay server-side."""
        saved = self.saved()
        result = {}
        for key, items in saved.items():
            if key not in ("pipelines", "presets"):
                continue
            result[key] = []
            for item in items:
                summary = {field: item[field] for field in ("id", "name", "saved_at", "tool") if field in item}
                if key == "pipelines":
                    summary["node_count"] = len(item.get("graph", {}).get("nodes", []))
                result[key].append(summary)
        result["summaries"] = True
        return result

    def save(self, request):
        name = short_text(request.get("name"), "saved name")
        kind = request.get("kind")
        if kind == "pipeline":
            item = {"graph": self.engine.save_pipeline(request.get("graph"))}
            key = "pipelines"
        elif kind == "preset":
            node = {"tool": request.get("tool"), "params": request.get("params", {})}
            if "pin" in request:
                node["pin"] = copy.deepcopy(request["pin"])
            item = self.engine.save_preset(node)
            key = "presets"
        else:
            raise ValueError("Choose a pipeline or tool settings to save.")
        item.update(id=uuid.uuid4().hex, name=name, saved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with self.lock:
            saved = self.saved()
            if len(saved[key]) >= 500:
                raise ValueError("The saved analysis limit (500) has been reached.")
            saved[key].append(item)
            if len(json.dumps(saved, ensure_ascii=True, indent=2).encode("utf-8")) > MAX_SAVED_BYTES:
                raise ValueError("Saving this item would exceed the supported saved-workspace size. Existing saved items have been preserved.")
            atomic_json(self.saved_path, saved)
        return item

    def bridge(self, arguments, emit=None, cancel=None):
        command = [str(self.root / "WorkbenchBridge.exe"), *map(str, arguments)]
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        with self.lock:
            if self._closing or cancel is not None and cancel.is_set():
                raise InterruptedError("The workbench is closing or this operation was cancelled.")
            # The desktop launcher selected a safe short working directory for
            # CreateProcessW. Actual workflow steps set their own result cwd.
            process = subprocess.Popen(command, cwd=None if os.name == "nt" else self.root, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace", **kwargs)
            self._processes.add(process)
        try:
            result = None
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    event = {"type": "log", "message": line.rstrip()[:16000]}
                if not isinstance(event, dict):
                    event = {"type": "log", "message": str(event)[:16000]}
                if emit:
                    emit(event)
                if event.get("type") == "result":
                    result = event
            exit_code = process.wait()
        finally:
            with self.lock:
                self._processes.discard(process)
            if process.stdout:
                process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        if result is None:
            raise RuntimeError("The native runner did not return a result (exit " + str(exit_code) + ").")
        if result.get("success") and exit_code != 0:
            raise RuntimeError("The native runner reported success but exited abnormally (exit " + str(exit_code) + ").")
        return result

    def browse(self, request):
        if os.name != "nt":
            raise ValueError("Native file selection is available in the Windows build.")
        kind = request.get("kind")
        if kind == "folder":
            args = ["choose-folder"]
        elif kind == "file":
            args = ["choose-file"]
            if request.get("multiple") is True:
                args.append("--multiple")
            if request.get("filter"):
                args.extend(["--filter", short_text(request["filter"], "file filter", 2000)])
        else:
            raise ValueError("Unknown file selection type.")
        if not self.dialog_lock.acquire(blocking=False):
            raise ValueError("A file selection window is already open. Check the Windows taskbar.")
        try:
            return self.bridge(args)
        finally:
            self.dialog_lock.release()

    def review(self, graph):
        if hasattr(self.engine, "review"):
            return self.engine.review(graph)
        result = self.engine.validate(graph)
        issues = [{"severity": "error", "message": str(e)} for e in result.get("errors", [])]
        issues += [{"severity": "warning", "message": str(e)} for e in result.get("warnings", [])]
        return {"valid": result.get("ok", False), "issues": issues, "methods": result.get("methods", "")}

    def public_run(self, run):
        public = {key: copy.deepcopy(value) for key, value in run.items() if not key.startswith("_")}
        events, size = [], 0
        original = public.get("events", [])
        for event in reversed(original):
            length = len(json.dumps(event, ensure_ascii=True).encode("utf-8"))
            if size + length > MAX_PUBLIC_LOG_BYTES:
                break
            events.append(event)
            size += length
        public["events"] = list(reversed(events))
        public["events_omitted"] = public.get("events_omitted", 0) + len(original) - len(events)
        return public

    def get_run(self, identity):
        with self.lock:
            if identity in self.runs:
                return self.public_run(self.runs[identity])
            for run in self.history:
                if run.get("run_id") == identity:
                    return copy.deepcopy(run)
        raise ValueError("This run is not recorded in this workbench.")

    def persist_run(self, run):
        public = self.public_run(run)
        public["events_omitted"] += max(0, len(public.get("events", [])) - 100)
        public["events"] = public.get("events", [])[-100:]
        candidates = [public, *[r for r in self.history if r.get("run_id") != run["run_id"]]][:200]
        self.history, size = [], 0
        for item in candidates:
            length = len(json.dumps(item, ensure_ascii=True).encode("utf-8"))
            if self.history and size + length > MAX_HISTORY_BYTES:
                continue
            self.history.append(item)
            size += length
        atomic_json(self.history_path, self.history)

    def start(self, request, check=False):
        output = Path(short_text(request.get("output_folder"), "output folder", 30000))
        if not output.is_absolute() or not output.is_dir():
            raise ValueError("Choose an existing absolute output folder.")
        with self.lock:
            if self._closing:
                raise ValueError("The workbench is closing.")
            if self._changing_packs:
                raise ValueError("Wait for the tool pack import to finish before starting an analysis.")
            if self._changing_references:
                raise ValueError("Wait for the reference operation to finish or cancel it before starting an analysis.")
            if self.active():
                raise ValueError("An analysis is already running. Wait for it to finish or cancel it first.")
            identity = uuid.uuid4().hex
            run = {"run_id": identity, "status": "preparing", "events": [], "nodes": [],
                   "folder": "", "message": "Preparing installation checks" if check else "Preparing analysis",
                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "_cancel": threading.Event(), "_cancel_file": self.data / ("cancel-" + identity)}
            self.runs[identity] = run
            self.persist_run(run)
        def emit(event):
            if not isinstance(event, dict):
                event = {"type": "log", "message": str(event)}
            with self.lock:
                run["events"].append(event)
                run["events"] = run["events"][-1500:]
                if event.get("type") == "phase":
                    run["message"] = event.get("message", "")
                if event.get("type") == "step" and event.get("nodeId"):
                    node = next((n for n in run["nodes"] if n.get("id") == event["nodeId"]), None)
                    if node is None:
                        node = {"id": event["nodeId"]}
                        run["nodes"].append(node)
                    node.update({k: v for k, v in event.items() if k in ("status", "message", "name", "folder")})
                if event.get("type") == "run" and event.get("folder"):
                    run["folder"] = str(event["folder"])
        def work():
            try:
                if check:
                    run["status"] = "running"
                    from core_checks import run_core_checks
                    result = run_core_checks(self.root, self.catalog, output, event=emit,
                                             cancel=run["_cancel"], backend=getattr(self.engine, "backend", None))
                    if result.get("success") and not run["_cancel"].is_set():
                        from pack_checks import run_pack_checks
                        checks_parent = Path(result.get("folder") or output)
                        extra = run_pack_checks(self.root, self.catalog, checks_parent,
                                                event=emit, cancel=run["_cancel"], backend=getattr(self.engine, "backend", None))
                        result["pack_checks"] = extra
                        result["success"] = extra["success"]
                        result["cancelled"] = extra.get("cancelled", False)
                        result["message"] = str(result.get("message", "Installation checks completed.")) + " " + extra["message"]
                    run.update({k: v for k, v in result.items() if k != "type"})
                    run["status"] = "cancelled" if result.get("cancelled") else "completed" if result.get("success") else "failed"
                else:
                    plan = self.engine.prepare(copy.deepcopy(request.get("graph")), output, cancel=run["_cancel"])
                    with self.lock:
                        run["folder"] = str(plan.get("folder", plan.get("run_folder", "")))
                        run["graph"] = copy.deepcopy(plan.get("graph", {}))
                        run["methods_planned"] = plan.get("methods", "")
                        run["status"] = "running"
                        self.persist_run(run)
                    result = self.engine.execute(plan, event=emit, cancel=run["_cancel"])
                    with self.lock:
                        run.update({k: v for k, v in result.items() if k not in ("run_id", "events") and not k.startswith("_")})
                        status = str(result.get("status", "failed"))
                        run["status"] = "completed" if status in ("success", "succeeded", "complete") else status
                run["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            except Exception as error:
                with self.lock:
                    run["status"] = "cancelled" if run["_cancel"].is_set() else "failed"
                    run["message"] = str(error)
                    emit({"type": "error", "message": str(error)})
            finally:
                with self.lock:
                    run["_cancel_file"].unlink(missing_ok=True)
                    self.persist_run(run)
        worker = threading.Thread(target=work, name="workbench-run-" + identity, daemon=False)
        run["_worker"] = worker
        worker.start()
        return {"run_id": identity}

    def cancel(self, identity):
        with self.lock:
            run = self.runs.get(identity)
            if run is None:
                raise ValueError("This run is no longer active.")
            if run["status"] in ("preparing", "running", "cancelling"):
                run["_cancel"].set()
                run["_cancel_file"].touch()
                run["status"] = "cancelling"
            return self.public_run(run)

    def open_results(self, identity):
        run = self.get_run(identity)
        folder = Path(run.get("folder") or "__missing__")
        if not folder.is_absolute() or not folder.is_dir():
            raise ValueError("The run has not created a results folder yet.")
        if os.name != "nt":
            raise ValueError("Opening Explorer is available in the Windows build.")
        os.startfile(str(folder))
        return {"opened": True}

    def _install_pack_folder(self, source):
        """The final, local publication step shared by online and offline installs."""
        if self._pack_cancel.is_set() and self._pack_operation.get("active"):
            raise InterruptedError("Pack installation cancelled before publication.")
        path = Path(source)
        from pack_manager import filesystem_path
        physical = filesystem_path(path)
        # Python graph metadata must be accepted before the native importer
        # publishes anything. Native manifest checks alone are insufficient.
        load_pack(physical / "pack.ini" if physical.is_dir() else physical)
        result = self.bridge(["import", "--app-root", self.root, "--source", path])
        if not result.get("success"):
            raise ValueError(result.get("message", "The pack could not be installed."))
        catalog = load_catalog(self.root)
        with self.lock:
            self.catalog = catalog
            self.engine = Engine(self.root, self.catalog)
        return result

    def import_pack(self, request):
        with self.lock:
            self.ensure_editable()
            self._changing_packs = True
        try:
            source = short_text(request.get("source"), "pack source", 30000)
            return self._install_pack_folder(source)
        finally:
            with self.lock:
                self._changing_packs = False

    def _manager(self):
        # Lazy construction keeps normal startup and analysis wholly offline.
        with self.lock:
            if self._pack_manager is None:
                from pack_manager import PackManager
                self._pack_manager = PackManager(self.root, self._install_pack_folder,
                                                 catalog_callback=lambda: self.catalog)
            return self._pack_manager

    def pack_state(self):
        with self.lock:
            if self._pack_listing is None or not self._pack_operation["active"]:
                self._pack_listing = self._manager().snapshot()
            value = copy.deepcopy(self._pack_listing)
            value["operation"] = copy.deepcopy(self._pack_operation)
            value.update(self.activity())
            return value

    def start_pack_operation(self, action, request):
        if action not in ("refresh", "source", "install", "import"):
            raise ValueError("Unknown pack operation.")
        with self.lock:
            self.ensure_editable()
            manager = self._manager()
            self._pack_listing = manager.snapshot()
            self._changing_packs = True
            self._pack_cancel = threading.Event()
            identity = uuid.uuid4().hex
            self._pack_operation = {"id": identity, "active": True, "status": "running",
                                    "action": action, "message": "Preparing pack operation…",
                                    "bytes": 0, "total": 0, "cancellable": True}
        request = copy.deepcopy(request)

        def progress(event):
            if not isinstance(event, dict):
                event = {"message": str(event)}
            with self.lock:
                for key in ("message", "bytes", "total", "cancellable", "phase"):
                    if key in event:
                        self._pack_operation[key] = event[key]

        def work():
            try:
                if self._pack_cancel.is_set():
                    raise InterruptedError("Pack operation cancelled.")
                if action == "refresh":
                    progress({"message": "Refreshing approved catalogues…"})
                    result = manager.snapshot(refresh=True, cancel=self._pack_cancel, event=progress)
                elif action == "source":
                    result = manager.add_source(short_text(request.get("path"), "catalogue file", 30000))
                elif action == "install":
                    result = manager.install(short_text(request.get("source_id"), "catalogue", 100),
                                             short_text(request.get("pack_id"), "pack", 100),
                                             short_text(request.get("version"), "pack version", 100),
                                             cancel=self._pack_cancel, event=progress)
                else:
                    source = Path(short_text(request.get("path"), "pack file or folder", 30000))
                    if source.is_dir() or source.name == "pack.ini":
                        progress({"message": "Verifying and importing local pack…", "cancellable": False})
                        result = self._install_pack_folder(source)
                    else:
                        result = manager.import_archive(source, cancel=self._pack_cancel, event=progress)
                if isinstance(result, dict) and result.get("success") is False:
                    raise ValueError(result.get("message", "The pack operation failed."))
                with self.lock:
                    if action in ("install", "import"):
                        self.catalog = load_catalog(self.root)
                        self.engine = Engine(self.root, self.catalog)
                    self._pack_operation.update(status="completed", success=True,
                                                message=(result.get("message") if isinstance(result, dict) else None)
                                                        or "Pack operation completed.")
                    if isinstance(result, dict):
                        for key in ("warnings", "installed", "publisherVerified", "verification"):
                            if key in result:
                                self._pack_operation[key] = copy.deepcopy(result[key])
                    self._pack_listing = manager.snapshot()
            except Exception as error:
                with self.lock:
                    cancelled = isinstance(error, InterruptedError)
                    self._pack_operation.update(status="cancelled" if cancelled else "failed",
                                                success=False, message=str(error))
            finally:
                with self.lock:
                    self._pack_operation.update(active=False, cancellable=False)
                    self._changing_packs = False

        worker = threading.Thread(target=work, name="workbench-pack-operation", daemon=True)
        with self.lock:
            self._pack_worker = worker
        worker.start()
        return self.pack_state()

    def cancel_pack_operation(self):
        with self.lock:
            if self._pack_operation["active"]:
                if not self._pack_operation.get("cancellable", True):
                    raise ValueError("Installation is being committed. Wait for it to finish.")
                self._pack_cancel.set()
                self._pack_operation["message"] = "Cancelling pack operation…"
        return self.pack_state()

    def setup_manager(self):
        with self.lock:
            if self._setup_manager is None:
                from setup_manager import SetupManager
                self._setup_manager = SetupManager(self.root, self._manager())
            return self._setup_manager

    def setup_state(self):
        with self.lock:
            value = self.setup_manager().snapshot()
            value.update(self.activity())
            return value

    def start_setup_operation(self, action, request):
        with self.lock:
            self.ensure_editable()
            manager = self.setup_manager()
            manager.prepare(action, copy.deepcopy(request))
            self._changing_packs = True
            self._setup_cancel = threading.Event()

        def work():
            try:
                manager.run(self._setup_cancel)
            except Exception as error:
                manager.host_failure(error)
            finally:
                with self.lock:
                    # Completed publications update the catalogue even when a
                    # later selected download fails or is cancelled.
                    try:
                        catalog = load_catalog(self.root)
                        engine = Engine(self.root, catalog)
                        self.catalog, self.engine = catalog, engine
                        self._pack_listing = None
                    except Exception as error:
                        manager.host_failure(error)
                    finally:
                        self._changing_packs = False

        worker = threading.Thread(target=work, name="workbench-tool-setup", daemon=True)
        with self.lock:
            self._setup_worker = worker
        worker.start()
        return self.setup_state()

    def cancel_setup_operation(self):
        with self.lock:
            self.setup_manager().cancel(self._setup_cancel)
        return self.setup_state()

    def dismiss_setup(self):
        with self.lock:
            self.setup_manager().dismiss()
        return self.setup_state()

    def reference_manager(self):
        # Construction and local snapshots never contact a reference provider.
        with self.lock:
            if self._reference_manager is None:
                from reference_manager import ReferenceManager
                self._reference_manager = ReferenceManager(self.root)
            return self._reference_manager

    def reference_state(self):
        with self.lock:
            if self._reference_listing is None or not self._reference_operation["active"]:
                self._reference_listing = self.reference_manager().snapshot()
            result = copy.deepcopy(self._reference_listing)
            result["operation"] = copy.deepcopy(self._reference_operation)
            result.update(self.activity())
            return result

    def reference_request(self, action, request):
        """Accept named provider choices, never client-supplied download URLs."""
        fields = {"search": {"release", "query"}, "discover": {"release", "species_id"},
                  "download": {"selection_id", "file_ids", "destination"}}
        if action not in fields or not isinstance(request, dict) or set(request) - fields[action]:
            raise ValueError("Unknown reference operation or request field.")
        result = copy.deepcopy(request)
        if action in ("search", "discover"):
            release = result.setdefault("release", 116)
            if type(release) is not int or not 1 <= release <= 9999:
                raise ValueError("Choose a numeric Ensembl archive release.")
        if action == "search":
            query = result.setdefault("query", "")
            if not isinstance(query, str) or len(query) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in query):
                raise ValueError("Use a short species name for the reference search.")
            result["query"] = query.strip()
        elif action == "discover":
            species = result.get("species_id")
            if not isinstance(species, str) or re.fullmatch(r"[a-z0-9_]{1,100}", species) is None:
                raise ValueError("Choose a species from the reference search results.")
        else:
            result["selection_id"] = short_text(result.get("selection_id"), "reference selection", 100)
            identities = result.get("file_ids")
            if (not isinstance(identities, list) or not 1 <= len(identities) <= 20
                    or any(not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value) is None for value in identities)
                    or len(identities) != len(set(identities))):
                raise ValueError("Choose one or more distinct files from the discovered reference.")
            destination = Path(short_text(result.get("destination"), "reference destination folder", 30000))
            managed_default = destination == self.data / "references" and not destination.exists()
            if not destination.is_absolute() or not (destination.is_dir() or managed_default):
                raise ValueError("Choose an existing absolute reference destination folder.")
            result["destination"] = str(destination)
        return result

    def start_reference_operation(self, action, request):
        request = self.reference_request(action, request)
        with self.lock:
            self.ensure_editable()
            manager = self.reference_manager()
            self._reference_listing = manager.snapshot()
            self._changing_references = True
            cancel = self._reference_cancel = threading.Event()
            self._reference_operation = {"id": uuid.uuid4().hex, "active": True, "status": "running",
                                         "action": action, "message": "Preparing reference operation…",
                                         "bytes": 0, "total": 0, "cancellable": True}

            def progress(event):
                if not isinstance(event, dict):
                    event = {"message": str(event)}
                with self.lock:
                    for key in ("message", "bytes", "total", "cancellable", "phase"):
                        if key in event:
                            self._reference_operation[key] = event[key]

            def work():
                try:
                    if cancel.is_set():
                        raise InterruptedError("Reference operation cancelled.")
                    if action == "search":
                        manager.search(request["release"], request["query"], cancel=cancel, event=progress)
                    elif action == "discover":
                        manager.discover(request["release"], request["species_id"], cancel=cancel, event=progress)
                    else:
                        manager.download(request["selection_id"], request["file_ids"], request["destination"],
                                         cancel=cancel, event=progress)
                    with self.lock:
                        self._reference_listing = manager.snapshot()
                        self._reference_operation.update(status="completed", success=True,
                            message={"search": "Species search completed. Choose a species to discover its files.",
                                     "discover": "Reference files discovered. Review the assembly and files before downloading.",
                                     "download": "Reference download completed. The local files are ready to use."}[action])
                except Exception as error:
                    with self.lock:
                        cancelled = isinstance(error, InterruptedError)
                        self._reference_operation.update(status="cancelled" if cancelled else "failed",
                                                         success=False, message=str(error))
                finally:
                    with self.lock:
                        self._reference_operation.update(active=False, cancellable=False)
                        self._changing_references = False

            worker = threading.Thread(target=work, name="workbench-reference-operation", daemon=True)
            self._reference_worker = worker
            # Start while holding the lifecycle lock so shutdown cannot join an
            # unstarted worker between publication and Thread.start().
            worker.start()
        return self.reference_state()

    def cancel_reference_operation(self):
        with self.lock:
            if self._reference_operation["active"]:
                if not self._reference_operation.get("cancellable", True):
                    raise ValueError("The completed reference is being recorded. Wait for it to finish.")
                self._reference_cancel.set()
                self._reference_operation["message"] = "Cancelling reference operation…"
        return self.reference_state()

    def shutdown(self, grace=10):
        """Cancel background work, wait, and stop native processes if necessary.

        The native window additionally owns the private interpreter and all its
        descendants in a kill-on-close Windows Job Object for crash containment.
        """
        with self.lock:
            self._closing = True
            workers = []
            self._pack_cancel.set()
            if self._pack_worker is not None:
                workers.append(self._pack_worker)
            self._setup_cancel.set()
            if self._setup_worker is not None:
                workers.append(self._setup_worker)
            self._reference_cancel.set()
            if self._reference_worker is not None:
                workers.append(self._reference_worker)
            for run in self.runs.values():
                if run["status"] in ("preparing", "running", "cancelling"):
                    run["_cancel"].set()
                    run["_cancel_file"].touch()
                    run["status"] = "cancelling"
                if run.get("_worker"):
                    workers.append(run["_worker"])
        deadline = time.monotonic() + max(0, grace)
        for worker in workers:
            worker.join(timeout=max(0, deadline - time.monotonic()))
        backend = getattr(self.engine, "backend", None)
        if backend is not None and hasattr(backend, "shutdown"):
            backend.shutdown()
        with self.lock:
            processes = list(self._processes)
        for process in processes:
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        for worker in workers:
            if worker.is_alive():
                worker.join(timeout=3)
        return not any(worker.is_alive() for worker in workers)
