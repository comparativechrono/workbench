"""Portable evidence guards; these are not Windows UI acceptance tests."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('ui_patch_gate',
    Path(__file__).resolve().parents[1] / 'scripts/check_ui_patch_windows.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class UIPatchGateTests(unittest.TestCase):
    def test_rejects_missing_or_unpinned_candidate_identities(self):
        good = dict(source_commit='1' * 40, gate_commit='2' * 40,
                    starter_sha256='a' * 64, update_sha256='b' * 64)
        gate.validate_identities(SimpleNamespace(**good))
        for key, bad in [('source_commit', 'HEAD'), ('gate_commit', '2' * 39),
                         ('starter_sha256', gate.BASELINE_SHA), ('update_sha256', 'unknown')]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                gate.validate_identities(SimpleNamespace(**dict(good, **{key: bad})))

    def test_clipped_old_window_fails_even_when_its_controls_fit_its_own_bounds(self):
        self.assertFalse(gate.inside([0, 0, 1040, 728], [0, 0, 1024, 728]))
        self.assertTrue(gate.inside([0, 0, 1024, 728], [0, 0, 1024, 728]))
        self.assertFalse(gate.inside([0, 0, 960, 769], [0, 0, 1024, 728]))
        self.assertTrue(gate.inside([-960, 0, 0, 680], [-1024, 0, 0, 728]))

    def test_overlapping_fixed_buttons_are_not_accepted_as_touching_edges(self):
        self.assertFalse(gate.overlaps([0, 0, 100, 30], [100, 0, 200, 30]))
        self.assertTrue(gate.overlaps([0, 0, 101, 30], [100, 0, 200, 30]))

    def test_initial_window_measurement_does_not_reposition_the_app(self):
        ui = gate.PatchUI.__new__(gate.PatchUI)
        ui.main = 7
        ui.bounds = lambda handle: [40, 20, 1000, 700]
        ui.work_area = lambda: [0, 0, 1024, 728]
        with patch.object(gate.NativeUI, 'fit_window') as fit:
            ui.fit_window(960, 680)
            fit.assert_not_called()
            self.assertEqual(ui.initial_bounds, [40, 20, 1000, 700])
            ui.fit_window(1024, 728)
            fit.assert_called_once_with(1024, 728)

    def test_real_pointer_click_keeps_hit_target_guard(self):
        calls = []
        ui = SimpleNamespace(bounds=lambda handle: [20, 30, 120, 70],
                             click_at=lambda x, y, **kw: calls.append((x, y, kw)))
        gate.pointer_click(ui, 5)
        self.assertEqual(calls, [(70, 50, {'expected': 5})])

    def test_cli_rejects_bad_identity_before_creating_report_or_running(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = ['gate.py']
            for name in ('app-root', 'baseline-archive', 'update-root', 'starter-archive',
                         'update-archive', 'work', 'report'):
                args += ['--' + name, str(root / name)]
            args += ['--source-commit', 'HEAD', '--gate-commit', '1' * 40,
                     '--starter-sha256', 'a' * 64, '--update-sha256', 'b' * 64]
            with patch('sys.argv', args), patch.object(gate, 'run') as run:
                with self.assertRaises(AssertionError):
                    gate.main()
                run.assert_not_called()
                self.assertEqual(list(root.iterdir()), [])

    def test_failed_scope_cannot_become_success_when_observations_finish(self):
        report = {'nativeGUIObservationsCompleted': True,
                  'scenarios': [{'status': 'pass'}, {'status': 'failed'}]}
        gate.finalize_report(report)
        self.assertEqual((report['passed'], report['failed']), (1, 1))
        self.assertFalse(report['success'])
        self.assertFalse(report['nativeGUIValidated'])


if __name__ == '__main__':
    unittest.main()
