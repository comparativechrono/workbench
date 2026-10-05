#!/usr/bin/env python3
"""Check the exact installed native three-pane desktop, never a browser mock.

Run on native Windows using this disposable application's isolated bundled Python.
The gate owns its GUI process, saves pixel captures and observed control bounds,
and verifies session/connection contracts against the installed private host.
It never modifies published artifacts or asserts unsupported DPI coverage.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import time
import traceback

# The helper is gate infrastructure from the same checked-out gate commit.
# Application imports/execution still come exclusively from --app-root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_references_windows import PrivateHost, require, sha256, stop_process_tree, write_json


class NativeUI:
    def __init__(self, root, evidence):
        self.root, self.evidence = root, evidence
        self.user = u = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi = g = ctypes.WinDLL("gdi32", use_last_error=True)
        self.callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        u.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        self.previous_dpi = u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        u.GetDpiForWindow.argtypes = [wintypes.HWND]
        u.GetDpiForWindow.restype = wintypes.UINT
        u.EnumWindows.argtypes = [self.callback, wintypes.LPARAM]
        u.EnumChildWindows.argtypes = [wintypes.HWND, self.callback, wintypes.LPARAM]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetDlgCtrlID.argtypes = [wintypes.HWND]
        u.GetDlgItem.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetDlgItem.restype = wintypes.HWND
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindowEnabled.argtypes = [wintypes.HWND]
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        u.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                         wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                         ctypes.POINTER(ctypes.c_size_t)]
        u.SendMessageTimeoutW.restype = wintypes.LPARAM
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.GetDC.argtypes = [wintypes.HWND]
        u.GetDC.restype = wintypes.HDC
        u.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        u.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
        g.CreateCompatibleDC.argtypes = [wintypes.HDC]
        g.CreateCompatibleDC.restype = wintypes.HDC
        g.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        g.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        g.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
        g.SelectObject.restype = wintypes.HANDLE
        g.DeleteObject.argtypes = [wintypes.HANDLE]
        g.DeleteDC.argtypes = [wintypes.HDC]
        g.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                                ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        class MouseInput(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
        class InputUnion(ctypes.Union):
            _fields_ = [("mi", MouseInput)]
        class Input(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("data", InputUnion)]
        self.Input, self.MouseInput = Input, MouseInput
        u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        u.SendInput.restype = wintypes.UINT
        self.process = subprocess.Popen([str(root / "NativeWorkbench.exe")], cwd=root)
        self.main = None
        self.wait("native main window", lambda: self.find_main())
        u.ShowWindow(self.main, 9)
        u.SetForegroundWindow(self.main)

    def progress(self, phase, **details):
        value = {"phase": phase, "updatedUtc": datetime.now(timezone.utc).isoformat(), **details}
        write_json(self.evidence / "ui-progress.json", value)
        with (self.evidence / "ui-events.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps(value, ensure_ascii=False) + "\n")
        print(json.dumps(value), flush=True)

    def send(self, hwnd, message, wparam=0, lparam=0):
        result = ctypes.c_size_t()
        require(self.user.SendMessageTimeoutW(hwnd, message, wparam, lparam, 3, 5000, ctypes.byref(result)),
                "Native message timed out or failed: " + hex(message))
        return result.value

    def post(self, hwnd, message, wparam=0, lparam=0):
        require(self.user.PostMessageW(hwnd, message, wparam, lparam), "Could not queue native input.")

    def label(self, hwnd, class_name=False):
        buffer = ctypes.create_unicode_buffer(32768)
        if class_name:
            self.user.GetClassNameW(hwnd, buffer, len(buffer))
        else:
            self.send(hwnd, 0x000D, len(buffer), ctypes.addressof(buffer))
        return buffer.value

    def set_text(self, hwnd, value):
        buffer = ctypes.create_unicode_buffer(str(value))
        require(self.send(hwnd, 0x000C, 0, ctypes.addressof(buffer)), "Could not set native edit text.")

    def windows(self):
        found = []
        @self.callback
        def each(hwnd, _):
            owner = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == self.process.pid and self.user.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True
        self.user.EnumWindows(each, 0)
        return found

    def find_main(self):
        for hwnd in self.windows():
            if self.label(hwnd) == "Native Workbench":
                self.main = hwnd
                return hwnd
        return None

    def child(self, identity, owner=None):
        owner = owner or self.main
        direct = self.user.GetDlgItem(owner, identity)
        if direct:
            return direct
        found = []
        @self.callback
        def each(hwnd, _):
            if self.user.GetDlgCtrlID(hwnd) == identity:
                found.append(hwnd)
                return False
            return True
        self.user.EnumChildWindows(owner, each, 0)
        return found[0] if found else None

    def bounds(self, hwnd):
        rect = wintypes.RECT()
        require(self.user.GetWindowRect(hwnd, ctypes.byref(rect)), "Could not measure native control.")
        return [rect.left, rect.top, rect.right, rect.bottom]

    def controls(self, owner=None):
        found = []
        @self.callback
        def each(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                found.append({"id": self.user.GetDlgCtrlID(hwnd), "class": self.label(hwnd, True),
                              "text": self.label(hwnd), "bounds": self.bounds(hwnd), "hwnd": hwnd})
            return True
        self.user.EnumChildWindows(owner or self.main, each, 0)
        return found

    def wait(self, phase, predicate, seconds=30):
        self.progress(phase)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Native desktop exited unexpectedly.")
            dialogs = [h for h in self.windows() if self.label(h, True) == "#32770"]
            require(not dialogs, "Unexpected native dialog: " + json.dumps([self.controls(h) for h in dialogs]))
            if predicate():
                return
            time.sleep(.1)
        if self.main:
            self.capture("failure.bmp")
            self.progress(phase + " timed out", controls=self.controls())
        raise TimeoutError(phase)

    def click_button(self, identity):
        hwnd = self.child(identity)
        self.wait("native button " + str(identity), lambda:
                  hwnd and self.user.IsWindowVisible(hwnd) and self.user.IsWindowEnabled(hwnd))
        self.post(hwnd, 0x00F5)

    def key(self, hwnd, code):
        self.post(hwnd, 0x0100, code, 1)
        self.post(hwnd, 0x0101, code, 0xC0000001)

    def mouse(self, x, y, flags=0):
        # Documented SendInput absolute screen coordinates, genuine pointer flow.
        width, height = self.user.GetSystemMetrics(0), self.user.GetSystemMetrics(1)
        require(0 <= x < width and 0 <= y < height, "Pointer target is outside the actual desktop.")
        item = self.Input()
        item.type = 0
        item.data.mi = self.MouseInput(round(x * 65535 / (width - 1)), round(y * 65535 / (height - 1)),
                                       0, 0x8001 | flags, 0, 0)
        require(self.user.SendInput(1, ctypes.byref(item), ctypes.sizeof(item)) == 1,
                "Native pointer input was unavailable; do not count drag as passed.")

    def click_at(self, x, y):
        self.mouse(x, y)
        self.mouse(x, y, 2)
        self.mouse(x, y, 4)

    def drag(self, start, finish):
        self.mouse(*start)
        self.mouse(*start, 2)
        try:
            for step in range(1, 17):
                point = [round(a + (b - a) * step / 16) for a, b in zip(start, finish)]
                self.mouse(*point)
                time.sleep(.035)
        finally:
            self.mouse(*finish, 4)

    def capture(self, filename, owner=None):
        hwnd = owner or self.main
        path = self.evidence / filename
        left, top, right, bottom = self.bounds(hwnd)
        width, height = right-left, bottom-top
        dc = self.user.GetDC(hwnd)
        memory = self.gdi.CreateCompatibleDC(dc)
        bitmap = self.gdi.CreateCompatibleBitmap(dc, width, height)
        old = self.gdi.SelectObject(memory, bitmap)
        try:
            require(self.user.PrintWindow(hwnd, memory, 0), "Native pixel capture failed.")
            header = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 32, 0, width*height*4, 0, 0, 0, 0)
            info = ctypes.create_string_buffer(header + bytes(1024))
            pixels = ctypes.create_string_buffer(width*height*4)
            self.gdi.SelectObject(memory, old)
            require(self.gdi.GetDIBits(memory, bitmap, 0, height, pixels, info, 0) == height,
                    "Native screenshot pixel read failed.")
            raw = pixels.raw
            require(len(set(raw[::4])) > 4, "Native pixel capture appears blank.")
            path.write_bytes(struct.pack("<2sIHHI", b"BM", 54+len(raw), 0, 0, 54) + header + raw)
            return {"path": filename, "width": width, "height": height, "sha256": sha256(path)}
        finally:
            self.gdi.SelectObject(memory, old)
            self.gdi.DeleteObject(bitmap)
            self.gdi.DeleteDC(memory)
            self.user.ReleaseDC(hwnd, dc)

    def close(self):
        try:
            if self.main and self.process.poll() is None:
                self.post(self.main, 0x0010)
                require(self.process.wait(timeout=30) == 0, "Native desktop did not close cleanly.")
        finally:
            stop_process_tree(self.process)
            self.user.SetThreadDpiAwarenessContext(self.previous_dpi)
            log = self.root / "user-data" / "desktop-host.stderr.txt"
            if log.is_file():
                shutil.copyfile(log, self.evidence / "ui-desktop-host.stderr.txt")


def host_contracts(root, evidence):
    host = PrivateHost(root, evidence, "ui-contracts", offline=True)
    try:
        initial = host.call("init")
        require(initial.get("mode") == "tool", "Default mode must be standalone tool mode.")
        standalone = host.call("workspace/tool", {"toolId": "bam/reference-index"})
        node = standalone["nodes"][0]["id"]
        source = standalone["sources"][0]["id"]
        fixture = root / "examples" / "starter" / "reference.fa"
        host.call("model", {"action": "apply_fields", "payload": {
            "nodeId": node, "name": "Preserved reference index",
            "files": {source: {"reference": str(fixture)}}}})
        standalone = host.call("state")
        workflow = host.call("workspace/mode", {"mode": "workflow"})
        require(not workflow["nodes"], "Standalone operation leaked into empty workflow.")
        first = host.call("model", {"action": "add_tool", "payload": {"toolId": "bam/sort"}})
        first_id = first["selected"]
        second = host.call("model", {"action": "add_tool", "payload": {"toolId": "bam/sort"}})
        second_id = second["selected"]
        compatible_preview = host.call("workspace/connection-targets", {"ref": first_id + "::sorted"})
        require({"nodeId": second_id, "portId": "alignment"} in compatible_preview["targets"],
                "Compatible starter output was absent from the native port preview.")
        connected = host.call("model", {"action": "connect", "payload": {
            "nodeId": second_id, "portId": "alignment", "refs": [first_id + "::sorted"]}})
        require(connected["graph"]["nodes"][1]["inputs"]["alignment"] == [first_id + "::sorted"],
                "Compatible connection was not installed.")
        cycle_preview = host.call("workspace/connection-targets", {"ref": second_id + "::sorted"})
        require({"nodeId": first_id, "portId": "alignment"} not in cycle_preview["targets"],
                "Native port preview offered a graph cycle.")
        reference_node = host.call("model", {"action": "add_tool", "payload": {"toolId": "bam/reference-index"}})
        reference_ref = reference_node["selected"] + "::reference"
        type_preview = host.call("workspace/connection-targets", {"ref": reference_ref})
        require({"nodeId": first_id, "portId": "alignment"} not in type_preview["targets"],
                "Native port preview offered a FASTA reference to an alignment input.")
        before = reference_node["graph"]
        rejected = []
        for label, payload in [
            ("cycle", {"nodeId": first_id, "portId": "alignment", "refs": [second_id + "::sorted"]}),
            ("type", {"nodeId": first_id, "portId": "alignment", "refs": [reference_ref]}),
        ]:
            try:
                host.call("model", {"action": "connect", "payload": payload})
            except ValueError as exc:
                rejected.append({"case": label, "message": str(exc)})
            else:
                raise AssertionError("Invalid connection was accepted: " + label)
            require(host.call("state")["graph"] == before, "Rejected connection mutated workflow.")
        back = host.call("workspace/mode", {"mode": "tool"})
        require(back["graph"] == standalone["graph"], "Standalone inputs/settings lost during workflow switch.")
        other = host.call("workspace/tool", {"toolId": "bam/index"})
        require(len(other["nodes"]) == 1, "Standalone selection appended another operation.")
        restored = host.call("workspace/tool", {"toolId": "bam/reference-index"})
        require(restored["graph"] == standalone["graph"], "Per-tool inputs/settings were not preserved.")
        restored_workflow = host.call("workspace/mode", {"mode": "workflow"})
        require(restored_workflow["graph"] == before, "Workflow lost after standalone selection.")
        return {"networkSocketOperationsDenied": True, "standaloneGraph": standalone["graph"],
                "workflowGraph": before, "rejected": rejected,
                "portPreviews": {"compatible": compatible_preview, "cycle": cycle_preview, "type": type_preview},
                "checks": ["Default standalone mode", "Independent preserved tool and workflow graphs",
                           "Compatible graph edge", "Bounded native compatibility preview",
                           "Atomic cycle and semantic type rejection", "Per-tool settings and input retention"]}
    finally:
        host.close()


# GUI assertions are filled against the public native controls/layout contract
# alongside the three-pane implementation; no test-only application RPC is used.
def gui_contracts(root, evidence):
    ui = NativeUI(root, evidence)
    captures, geometry = [], []
    try:
        ui.wait("installed native tool library", lambda:
                ui.user.IsWindowEnabled(ui.child(410)) and ui.send(ui.child(104), 0x1004) > 0)
        ui.user.MoveWindow(ui.main, 0, 0, 1280, 900, True)
        dpi = ui.user.GetDpiForWindow(ui.main)
        scale = dpi / 96
        def point(hwnd, x, y):
            left, top, _, _ = ui.bounds(hwnd)
            return round(left + x * scale), round(top + y * scale)
        def edits():
            return [c for c in ui.controls() if c["id"] >= 2000 and c["class"].lower() == "edit"]
        def has_text(value):
            return any(c["text"] == value for c in edits())
        def select_tool(query, *, drag_to=None):
            ui.set_text(ui.child(102), query)
            ui.wait("filter tool " + query, lambda: ui.send(ui.child(104), 0x1004) == 1)
            tasks = ui.child(104)
            left, top, right, _ = ui.bounds(tasks)
            header = ui.send(tasks, 0x101F)  # LVM_GETHEADER, handle result only.
            first_y = ui.bounds(header)[3] + round(11 * scale) if header and ui.user.IsWindowVisible(header) else top + round(13 * scale)
            start = (left + min(round(70 * scale), (right-left)//2), first_y)
            if drag_to:
                ui.drag(start, point(ui.child(117), *drag_to))
            else:
                ui.click_at(*start)
        def name_edit():
            found = [c for c in edits() if c["text"] in ("Coordinate sort", "First coordinate sort", "Second coordinate sort")]
            require(found, "Selected workflow tool has no editable native name.")
            return found[0]["hwnd"]
        def measure(mode, size):
            rows = ui.controls()
            by_id = {c["id"]: c for c in rows if c["id"] > 0}
            for identity in (102, 104, 410, 411, 118):
                require(identity in by_id, "Missing visible native control: " + str(identity))
            tools, form = by_id[104]["bounds"], by_id[118]["bounds"]
            require(tools[2] <= form[0], "Tool library overlaps the selected tool form.")
            if mode == "tool":
                for identity in (101, 413, 111, 403):
                    require(identity in by_id, "General setting hidden in standalone mode: " + str(identity))
                    require(form[2] <= by_id[identity]["bounds"][0], "Central parameters overlap general settings.")
                require(117 not in by_id, "Workflow canvas remained visible in standalone mode.")
            else:
                require(117 in by_id, "Workflow canvas is not visible.")
                canvas = by_id[117]["bounds"]
                require(tools[2] <= canvas[0] and canvas[2] <= form[0], "Workflow panes overlap.")
            geometry.append({"mode": mode, "size": size, "dpi": ui.user.GetDpiForWindow(ui.main), "controls": rows})
        select_tool("Index a reference")
        ui.wait("single click opens standalone reference indexing form", lambda: has_text("Index a reference"))
        measure("tool", "1280x900")
        require(ui.user.IsWindowVisible(ui.child(403)), "References absent from general settings.")
        empty_inputs = [c for c in edits() if not c["text"]]
        require(empty_inputs, "Standalone reference input edit missing.")
        chosen_reference = str(root / "examples" / "starter" / "reference.fa")
        ui.set_text(empty_inputs[0]["hwnd"], chosen_reference)
        ui.set_text(ui.child(413), str(root / "examples" / "starter"))
        captures.append(ui.capture("tools-reference-1280.bmp"))
        ui.click_button(411)
        ui.wait("workflow canvas opens", lambda: ui.user.IsWindowVisible(ui.child(117)) and ui.user.IsWindowVisible(ui.child(105)))
        select_tool("Coordinate sort", drag_to=(144, 60))
        ui.wait("dragged tool shows workflow parameters", lambda: has_text("Coordinate sort"))
        ui.set_text(name_edit(), "First coordinate sort")
        # Dropping a second tool commits the first form and leaves its position.
        select_tool("Coordinate sort", drag_to=(414, 290))
        ui.wait("second dragged tool selected", lambda: has_text("Coordinate sort"))
        ui.set_text(name_edit(), "Second coordinate sort")
        # Explicitly dropped nodes have deterministic documented positions:
        # pointer minus(120,20); socket rows derive from the actual pack schema.
        canvas = ui.child(117)
        ui.drag(point(canvas, 266, 147), point(canvas, 294, 335))
        ui.wait("compatible output connected through native port drag", lambda: any(
            c["class"].lower() == "static" and "From:" in c["text"] and "First coordinate sort" in c["text"]
            for c in ui.controls()), seconds=30)
        measure("workflow", "1280x900")
        captures.append(ui.capture("workflow-connected-1280.bmp"))
        ui.click_at(*point(canvas, 120, 58))
        ui.wait("canvas selection opens first tool on right", lambda: has_text("First coordinate sort"))
        captures.append(ui.capture("workflow-first-selected.bmp"))
        ui.click_button(412)
        ui.wait("workflow general settings available", lambda:
                ui.user.IsWindowVisible(ui.child(413)) and ui.user.IsWindowVisible(ui.child(403)))
        captures.append(ui.capture("workflow-general-settings.bmp"))
        ui.click_button(410)
        ui.wait("standalone input retained after workflow editing", lambda: has_text(chosen_reference))
        require(ui.label(ui.child(413)) == str(root / "examples" / "starter"), "Input browsing folder was lost.")
        measure("tool", "restored")
        ui.user.MoveWindow(ui.main, 0, 0, 1100, 740, True)
        time.sleep(.2)
        measure("tool", "requested1100x740")
        captures.append(ui.capture("tools-minimum.bmp"))
        ui.click_button(411)
        ui.wait("workflow canvas restored", lambda: ui.user.IsWindowVisible(ui.child(117)))
        ui.click_at(*point(ui.child(117), 120, 58))
        ui.wait("workflow selection retained", lambda: has_text("First coordinate sort"))
        measure("workflow", "requested1100x740")
        captures.append(ui.capture("workflow-minimum.bmp"))
        write_json(evidence / "ui-control-geometry.json", geometry)
        return {"dpi": dpi, "displayPixels": [ui.user.GetSystemMetrics(0), ui.user.GetSystemMetrics(1)],
                "captures": captures, "geometryFile": "ui-control-geometry.json",
                "checks": ["Single-click standalone tool form", "Three independent panes with general settings",
                           "Actual mouse drag from tool list onto workflow canvas twice",
                           "Actual compatible output-to-input mouse connection",
                           "Canvas selection displays tool options on right",
                           "General settings remain available in workflow mode",
                           "Standalone input and browsing folder survive workflow mode",
                           "Workflow graph/selection survives mode switching", "Normal/minimum observed pane separation"],
                "limits": ["DPI coverage is only the actual reported monitor DPI; no simulated WM_DPICHANGED claim.",
                           "Human usability acceptance, multi-monitor movement and native folder pickers remain separate."]}
    finally:
        ui.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--asset-sha256", required=True)
    parser.add_argument("--asset-name", required=True)
    parser.add_argument("--gui-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root, report_path = args.app_root.resolve(), args.report.resolve()
    evidence = report_path.parent
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"schema": 1, "success": False, "startedUtc": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version, "nativeWindowsExecuted": False,
              "appRoot": str(root), "sourceCommit": args.source_commit, "assetSha256": args.asset_sha256,
              "assetName": args.asset_name, "gateSha256": sha256(__file__), "checks": [], "skips": []}
    try:
        require(os.name == "nt", "This gate requires actual native Windows; it has no passing skip mode.")
        require(Path(sys.executable).resolve() == (root / "runtime/python/python.exe").resolve(),
                "Run using the exact application's private Python.")
        if args.gui_worker:
            report["gui"] = gui_contracts(root, evidence)
            report["checks"] = report["gui"]["checks"]
        else:
            report["appFiles"] = {str(p.relative_to(root)): sha256(p) for p in [root/"NativeWorkbench.exe", *sorted((root/"workspace").glob("*.py"))]}
            report["host"] = host_contracts(root, evidence)
            report["checks"].extend(report["host"]["checks"])
            worker_report = evidence / "ui-worker.json"
            command = [sys.executable, "-I", "-u", str(Path(__file__).resolve()), "--gui-worker",
                       "--app-root", str(root), "--report", str(worker_report), "--source-commit", args.source_commit,
                       "--asset-sha256", args.asset_sha256, "--asset-name", args.asset_name]
            with (evidence/"ui-worker.stderr.txt").open("wb") as err:
                worker = subprocess.Popen(command, stderr=err)
                try:
                    worker.wait(timeout=240)
                finally:
                    stop_process_tree(worker)
            require(worker_report.is_file(), "Native GUI worker did not produce a report.")
            result = json.loads(worker_report.read_text(encoding="utf-8"))
            require(worker.returncode == 0 and result.get("success"), "Native GUI worker failed: " + json.dumps(result))
            report["gui"] = result["gui"]
            report["checks"].extend(result["checks"])
        report["nativeWindowsExecuted"] = True
        report["success"] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        report["completedUtc"] = datetime.now(timezone.utc).isoformat()
        report["passed"] = len(report["checks"])
        write_json(report_path, report)
    print(json.dumps({"success": report["success"], "passed": report["passed"], "report": str(report_path)}), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
