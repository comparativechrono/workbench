"""Portable tests for temporal failure oracles; no Windows acceptance claim."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('tester_feedback_gate',
    Path(__file__).resolve().parents[1] / 'scripts/check_tester_feedback_windows.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def pixels(width=40, height=32, color=(255, 255, 255, 0)):
    return bytearray(bytes(color) * width * height)


def paint(raw, x, y, width, height, color, stride=40):
    for yy in range(y, y + height):
        for xx in range(x, x + width):
            offset = (yy * stride + xx) * 4
            raw[offset:offset + 4] = bytes(color)


class FeedbackGateTests(unittest.TestCase):
    def test_reported_black_rectangle_is_rejected_by_pixel_oracle(self):
        raw = pixels()
        paint(raw, 8, 8, 24, 16, (0, 0, 0, 99))
        self.assertIn([8, 8, 24, 24], gate.black_blocks(raw, 40, 32))

    def test_text_caret_and_blue_native_selection_are_not_black_blocks(self):
        raw = pixels()
        paint(raw, 0, 0, 40, 18, (180, 70, 10, 0))  # BGR selection, not near black.
        paint(raw, 1, 1, 2, 24, (0, 0, 0, 0))       # Caret or thin letter stem.
        for x in range(8, 35, 5):
            paint(raw, x, 20, 2, 8, (0, 0, 0, 0))
        self.assertEqual(gate.black_blocks(raw, 40, 32), [])

    def test_unused_alpha_is_ignored_but_real_rgb_changes_remain(self):
        first, second = bytes([20, 30, 40, 0]), bytes([20, 30, 40, 255])
        self.assertEqual(gate.normalized(first), gate.normalized(second))
        self.assertNotEqual(gate.normalized(first), gate.normalized(bytes([20, 30, 41, 0])))

    def test_truncated_frame_cannot_pass_as_empty_black_detection(self):
        with self.assertRaises(AssertionError):
            gate.black_blocks(bytes(100), 40, 32)

    def test_gate_rejects_unpinned_identity_and_evidence_inside_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(source_commit='1' * 40, gate_commit='2' * 40,
                starter_sha256='a' * 64, app_root=root / 'app', report=root / 'evidence/result.json',
                starter_archive=root / 'starter.zip')
            gate.validate_identities(args)
            args.gate_commit = 'HEAD'
            with self.assertRaises(AssertionError):
                gate.validate_identities(args)
            args.gate_commit = '2' * 40
            args.report = root / 'app/evidence.json'
            with self.assertRaises(AssertionError):
                gate.validate_identities(args)

    def test_main_window_is_not_mistaken_for_same_title_error_dialog(self):
        ui = SimpleNamespace(main=1, windows=lambda: [1, 2], label=lambda handle: 'Native Workbench')
        self.assertEqual(gate.window(ui, 'Native Workbench'), 2)

    def test_failed_temporal_scope_cannot_become_success(self):
        report = {'nativeGUIObservationsCompleted': True,
                  'scenarios': [{'status': 'pass'}, {'status': 'failed'}]}
        gate.finalize_report(report)
        self.assertFalse(report['success'])
        self.assertEqual(report['failed'], 1)


if __name__ == '__main__':
    unittest.main()
