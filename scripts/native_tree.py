"""Read actual Win32 TreeView controls in native GUI gates.

TreeView messages with pointer arguments are not marshalled across processes.
Allocate only the small documented TVITEM/RECT buffers in the app process;
never inject notifications, application state, code, or private RPC handlers.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes


class NativeTree:
    def __init__(self, user, send, pid, hwnd):
        self.user, self.send, self.pid, self.hwnd = user, send, pid, hwnd

    def _buffer(self, payload, size, action):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
        kernel.VirtualAllocEx.restype = ctypes.c_void_p
        kernel.VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
        kernel.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        kernel.ReadProcessMemory.argtypes = kernel.WriteProcessMemory.argtypes
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        process = kernel.OpenProcess(0x0038, False, self.pid)  # VM_OPERATION/READ/WRITE.
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        address = None
        try:
            address = kernel.VirtualAllocEx(process, None, size, 0x3000, 0x04)
            if not address:
                raise ctypes.WinError(ctypes.get_last_error())
            raw = payload(address) if callable(payload) else payload
            count = ctypes.c_size_t()
            source = ctypes.create_string_buffer(raw)
            if not kernel.WriteProcessMemory(process, address, source, len(raw), ctypes.byref(count)) or count.value != len(raw):
                raise ctypes.WinError(ctypes.get_last_error())
            if not action(address):
                raise AssertionError("Native TreeView buffer query failed.")
            result = ctypes.create_string_buffer(size)
            if not kernel.ReadProcessMemory(process, address, result, size, ctypes.byref(count)) or count.value != size:
                raise ctypes.WinError(ctypes.get_last_error())
            return result.raw
        finally:
            if address:
                kernel.VirtualFreeEx(process, address, 0, 0x8000)
            kernel.CloseHandle(process)

    def next(self, item=0, relation=0):
        return self.send(self.hwnd, 0x110A, relation, item)  # TVM_GETNEXTITEM.

    def siblings(self, first):
        result = []
        while first:
            if first in result or len(result) >= 4096:
                raise AssertionError("Unexpected native TreeView sibling cycle/size.")
            result.append(first)
            first = self.next(first, 1)
        return result

    def roots(self):
        return self.siblings(self.next())

    def children(self, root):
        return self.siblings(self.next(root, 4))

    def tools(self):
        return [child for root in self.roots() for child in self.children(root)]

    def selected(self):
        return self.next(0, 9)

    def expanded(self, item):
        return bool(self.send(self.hwnd, 0x1127, item, 0x20) & 0x20)  # TVM_GETITEMSTATE/TVIS_EXPANDED.

    def inspect(self, item):
        class Item(ctypes.Structure):
            _fields_ = [("mask", wintypes.UINT), ("hItem", ctypes.c_void_p),
                        ("state", wintypes.UINT), ("stateMask", wintypes.UINT),
                        ("pszText", ctypes.c_void_p), ("cchTextMax", ctypes.c_int),
                        ("iImage", ctypes.c_int), ("iSelectedImage", ctypes.c_int),
                        ("cChildren", ctypes.c_int), ("lParam", wintypes.LPARAM)]
        offset, text_bytes = ctypes.sizeof(Item), 4096
        def payload(address):
            value = Item(mask=1 | 8, hItem=item, stateMask=0xffff,
                         pszText=address + offset, cchTextMax=text_bytes // 2)
            return bytes(value) + bytes(text_bytes)
        raw = self._buffer(payload, offset + text_bytes,
                           lambda address: self.send(self.hwnd, 0x113E, 0, address))
        state = Item.from_buffer_copy(raw).state
        return {"handle": item, "label": raw[offset:].decode("utf-16-le").split("\0", 1)[0],
                "itemState": state,
                "messageStateAll": self.send(self.hwnd, 0x1127, item, 0xffff),
                "messageStateExpanded": self.send(self.hwnd, 0x1127, item, 0x20)}

    def label(self, item):
        return self.inspect(item)["label"]

    def rect(self, item):
        # TVM_GETITEMRECT overlays HTREEITEM on the beginning of RECT.
        size = ctypes.sizeof(wintypes.RECT)
        raw = int(item).to_bytes(ctypes.sizeof(ctypes.c_void_p), "little").ljust(size, b"\0")
        raw = self._buffer(raw, size, lambda address: self.send(self.hwnd, 0x1104, 1, address))
        result = wintypes.RECT.from_buffer_copy(raw)
        origin = wintypes.POINT()
        if not self.user.ClientToScreen(self.hwnd, ctypes.byref(origin)):
            raise ctypes.WinError(ctypes.get_last_error())
        return [result.left + origin.x, result.top + origin.y,
                result.right + origin.x, result.bottom + origin.y]

    def point(self, item):
        self.send(self.hwnd, 0x1114, 0, item)  # TVM_ENSUREVISIBLE.
        left, top, right, bottom = self.rect(item)
        return left + min(40, max(2, (right-left)//2)), (top+bottom)//2

    def first_tool_point(self):
        tools = self.tools()
        if len(tools) != 1:
            raise AssertionError("Expected exactly one filtered tool, got " + str(len(tools)))
        return self.point(tools[0])
