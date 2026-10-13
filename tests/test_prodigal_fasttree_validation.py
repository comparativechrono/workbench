"""Contract tests for evidence binding; not native/scientific execution claims."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pack_candidate_gate', ROOT / 'scripts/check_prodigal_fasttree_windows.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class CandidateEvidenceContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_unsafe_archive_names_are_rejected(self):
        for name in ('../escape', '/absolute', 'a/../escape', 'a\\b', 'C:/a', 'a//b', 'a/./b', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                gate.safe_member(name)
        self.assertEqual(gate.safe_member('source/tools/pack.py'), ('source', 'tools', 'pack.py'))

    def test_file_verification_checks_bytes_and_hash(self):
        path = self.root / 'candidate.zip'
        path.write_bytes(b'original')
        record = gate.file_record(path)
        gate.verify_file(path, record)
        path.write_bytes(b'modified')  # Same length, different bytes.
        with self.assertRaisesRegex(ValueError, 'differs'):
            gate.verify_file(path, record)

    def test_exact_application_extraction_preserves_core_and_allows_user_data(self):
        archive, app = self.root / 'app.zip', self.root / 'app'
        app.mkdir()
        (app / 'core.py').write_bytes(b'published core')
        (app / 'user-data').mkdir()
        (app / 'user-data/result.json').write_text('{}')
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('native-workbench/core.py', b'published core')
        self.assertEqual(gate.verify_extracted(archive, app), 1)
        (app / 'core.py').write_bytes(b'modified core')
        with self.assertRaisesRegex(ValueError, 'Application file changed'):
            gate.verify_extracted(archive, app)

    def test_archive_cannot_escape_application_root(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('native-workbench/../escape', b'bad')
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            gate.verify_extracted(archive, self.root)

    def test_companion_case_collisions_are_rejected(self):
        item = self.root / 'input'
        item.write_bytes(b'fixture')
        with self.assertRaisesRegex(ValueError, 'collision'):
            gate.zip_files(self.root / 'source.zip', [('source/A', item), ('source/a', item)], {})

    def test_frozen_identity_and_companion_member_tampering_are_rejected(self):
        packs = {}
        for identity in gate.PACK_IDS:
            path = self.root / (identity + '.zip')
            path.write_bytes(identity.encode())
            packs[identity] = {**gate.file_record(path), 'id': identity, 'version': '1.0.0'}
        companion = self.root / 'sources.zip'
        source = self.root / 'lock.json'
        source.write_text('{"upstream":"pinned"}')
        inventory = {'schema': 1, 'sourceCommit': 'a' * 40, 'files': [
            {'path': 'corresponding-sources/tool/lock.json', 'bytes': source.stat().st_size, 'sha256': gate.sha(source)}]}
        gate.zip_files(companion, [('corresponding-sources/tool/lock.json', source)],
                       {'SOURCE-INVENTORY.json': inventory, 'BUILD-PROVENANCE.json': {}})
        record = {'sourceCommit': 'a' * 40, 'packs': packs, 'sourceCompanion': gate.file_record(companion)}
        gate.write_json(self.root / 'BUILD-PROVENANCE.json', record)
        self.assertEqual(gate.verify_candidate(self.root, 'a' * 40), record)
        with self.assertRaisesRegex(ValueError, 'source/packs'):
            gate.verify_candidate(self.root, 'b' * 40)
        # Updating outer hash does not hide a corrupted inner member inventory.
        with zipfile.ZipFile(companion, 'w') as zipped:
            zipped.writestr('corresponding-sources/tool/lock.json', 'changed upstream')
            zipped.writestr('SOURCE-INVENTORY.json', json.dumps(inventory))
            zipped.writestr('BUILD-PROVENANCE.json', '{}')
        record['sourceCompanion'] = gate.file_record(companion)
        gate.write_json(self.root / 'BUILD-PROVENANCE.json', record)
        with self.assertRaisesRegex(ValueError, 'member differs'):
            gate.verify_candidate(self.root, 'a' * 40)


if __name__ == '__main__':
    unittest.main()
