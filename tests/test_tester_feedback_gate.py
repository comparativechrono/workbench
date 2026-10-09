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
    def fake_ui(self, title='Remove sample row'):
        ui = gate.FeedbackUI.__new__(gate.FeedbackUI)
        ui.process = SimpleNamespace(poll=lambda: None)
        ui.progress = lambda *args, **kwargs: None
        ui.windows = lambda: [4]
        ui.label = lambda handle, klass=False: '#32770' if klass else title
        ui.controls = lambda owner: []
        ui.top_windows = lambda: [{'handle': 4, 'title': title, 'class': '#32770'}]
        return ui

    def test_destroyed_caption_is_not_requeried_as_an_unexpected_dialog(self):
        ui = gate.FeedbackUI.__new__(gate.FeedbackUI)
        alive = [True]
        ui.windows = lambda: [4]
        def caption(handle, text, size):
            text.value = 'Remove sample row'
            alive[0] = False  # Destruction raced the caption snapshot.
        ui.user = SimpleNamespace(IsWindow=lambda handle: alive[0], IsWindowVisible=lambda handle: True,
            GetClassNameW=lambda handle, text, size: setattr(text, 'value', '#32770'),
            GetWindowTextW=caption)
        ui.label = lambda *args: self.fail('Top-level captions must not send WM_GETTEXT')
        self.assertEqual(ui.top_windows(), [])

    def test_live_visible_common_caption_is_preserved_in_snapshot(self):
        ui = gate.FeedbackUI.__new__(gate.FeedbackUI)
        ui.windows = lambda: [4]
        ui.user = SimpleNamespace(IsWindow=lambda handle: True, IsWindowVisible=lambda handle: True,
            GetClassNameW=lambda handle, text, size: setattr(text, 'value', '#32770'),
            GetWindowTextW=lambda handle, text, size: setattr(text, 'value', 'Real error'))
        self.assertEqual(ui.top_windows(), [{'handle': 4, 'class': '#32770', 'title': 'Real error'}])

    def test_expected_native_confirmation_is_allowed_only_in_its_context(self):
        ui = self.fake_ui()
        with ui.common_dialog('Remove sample row'):
            ui.wait('expected confirmation', lambda: True)
        with self.assertRaisesRegex(AssertionError, 'Unexpected native dialog'):
            ui.wait('unplanned confirmation', lambda: True)

    def test_allowing_delete_does_not_allow_another_native_error(self):
        ui = self.fake_ui('Unexpected application failure')
        with ui.common_dialog('Remove sample row'):
            with self.assertRaisesRegex(AssertionError, 'Unexpected application failure'):
                ui.wait('expected confirmation', lambda: True)

    def test_failed_dialog_scope_does_not_leave_future_dialogs_permitted(self):
        ui = self.fake_ui()
        with self.assertRaises(ValueError):
            with ui.common_dialog('Remove sample row'):
                raise ValueError('failed interaction')
        self.assertEqual(ui.expected_dialog_titles, frozenset())

    def test_primary_assertion_is_retained_if_cleanup_also_fails(self):
        ui = SimpleNamespace(windows=lambda: [], process=object(),
                             close=lambda: (_ for _ in ()).throw(RuntimeError('cleanup failed')))
        report = {}
        with patch.object(gate, 'stop_process_tree') as stop:
            with self.assertRaisesRegex(AssertionError, 'original failure'):
                with gate.observed_desktop(ui, report, 'scenario'):
                    raise AssertionError('original failure')
            stop.assert_called_once_with(ui.process)
        self.assertEqual(report['primaryFailures'][0]['error'], 'original failure')
        self.assertEqual(report['cleanupErrors'], ['cleanup failed'])

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
        ui = SimpleNamespace(main=1, top_windows=lambda: [
            {'handle': handle, 'title': 'Native Workbench', 'class': '#32770'} for handle in [1, 2]])
        self.assertEqual(gate.window(ui, 'Native Workbench'), 2)

    def test_failed_temporal_scope_cannot_become_success(self):
        report = {'nativeGUIObservationsCompleted': True,
                  'scenarios': [{'status': 'pass'}, {'status': 'failed'}]}
        gate.finalize_report(report)
        self.assertFalse(report['success'])
        self.assertEqual(report['failed'], 1)


if __name__ == '__main__':
    unittest.main()
