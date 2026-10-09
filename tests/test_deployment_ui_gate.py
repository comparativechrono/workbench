"""Portable evidence-integrity checks; these do not simulate Windows UI passes."""
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('deployment_ui_gate',
    Path(__file__).resolve().parents[1] / 'scripts/check_deployment_ui_windows.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class DeploymentUIGateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def archive(self, members):
        path = self.root / 'input.zip'
        with zipfile.ZipFile(path, 'w') as zipped:
            for name, content in members.items():
                zipped.writestr(name, content)
        return path

    def test_flat_published_updater_layout_verifies_launcher_and_private_runtime(self):
        members = {'UpdateWorkbench.exe': b'published launcher', 'runtime/python/python.exe': b'private runtime'}
        archive = self.archive(members)
        extraction = self.root / 'updater'
        for name, content in members.items():
            path = extraction / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.assertEqual(gate.verify_extracted(archive, extraction), 2)
        (extraction / 'UpdateWorkbench.exe').write_bytes(b'changed launcher!!')
        with self.assertRaisesRegex(AssertionError, 'Extraction differs'):
            gate.verify_extracted(archive, extraction)

    def test_starter_root_is_stripped_once_and_missing_file_is_rejected(self):
        archive = self.archive({'native-workbench/NativeWorkbench.exe': b'app', 'native-workbench/manifest.json': b'{}'})
        extraction = self.root / 'starter'
        extraction.mkdir()
        (extraction / 'NativeWorkbench.exe').write_bytes(b'app')
        (extraction / 'manifest.json').write_bytes(b'{}')
        self.assertEqual(gate.verify_extracted(archive, extraction), 2)
        (extraction / 'manifest.json').unlink()
        with self.assertRaisesRegex(AssertionError, 'Extraction differs'):
            gate.verify_extracted(archive, extraction)

    def test_archive_traversal_is_rejected_before_reading_outside_extraction(self):
        archive = self.archive({'../outside.exe': b'untrusted'})
        with self.assertRaisesRegex(AssertionError, 'Unsafe archived path'):
            gate.verify_extracted(archive, self.root / 'updater')

    def test_snapshot_detects_addition_deletion_and_content_change(self):
        folder = self.root / 'saved'
        folder.mkdir()
        path = folder / 'settings.json'
        path.write_text('{"packVersion":"0.4.0"}', encoding='utf-8')
        baseline = gate.tree_hashes(folder)
        path.write_text('{"packVersion":"0.4.1"}', encoding='utf-8')
        self.assertNotEqual(gate.tree_hashes(folder), baseline)
        path.unlink()
        self.assertNotEqual(gate.tree_hashes(folder), baseline)
        (folder / 'other.json').write_text('{}', encoding='utf-8')
        self.assertNotEqual(gate.tree_hashes(folder), baseline)

    def test_preservation_permits_only_the_exact_legacy_session_lock_addition(self):
        before = {'user-data/saved.json': 'unchanged', 'external/reference.fa': 'unchanged-reference'}
        after = dict(before, **{'user-data/session.lock': hashlib.sha256(b'\0').hexdigest()})
        self.assertEqual(gate.verify_preserved(before, after)['existingFiles'], 2)
        for bad in [dict(after, **{'user-data/session.lock': hashlib.sha256(b'').hexdigest()}),
                    dict(after, **{'user-data/saved.json': 'changed'}),
                    dict(after, **{'user-data/unexpected.json': 'new'}),
                    {'user-data/saved.json': 'unchanged'}]:
            with self.assertRaisesRegex(AssertionError, 'changed existing files'):
                gate.verify_preserved(before, bad)


if __name__ == '__main__':
    unittest.main()
