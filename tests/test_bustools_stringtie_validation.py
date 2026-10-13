"""Fail-closed batch evidence contracts; these tests do not execute Windows."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bustools_stringtie_gate', ROOT / 'scripts/check_bustools_stringtie_windows.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
sys.path.insert(0, str(ROOT / 'scripts'))
audit_spec = importlib.util.spec_from_file_location('bustools_stringtie_audit', ROOT / 'scripts/audit_bustools_stringtie_candidate.py')
audit = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(audit)


class BustoolsStringTieEvidenceContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self):
        packs = {}
        for identity in ('bustools', 'stringtie'):
            archive = self.root / (identity + '.zip')
            archive.write_bytes(('exact ' + identity + ' payload').encode())
            packs[identity] = {**gate.file_record(archive), 'id': identity, 'version': '1.0.0'}
        source = self.root / 'upstream.tar.gz'
        source.write_bytes(b'exact corresponding source fixture')
        name = 'corresponding-sources/bustools/upstream.tar.gz'
        inventory = {'schema': 1, 'sourceCommit': 'a' * 40, 'files': [
            {'path': name, 'bytes': source.stat().st_size, 'sha256': gate.sha(source)}]}
        companion = self.root / 'source.zip'
        gate.common.zip_files(companion, [(name, source)],
                              {'SOURCE-INVENTORY.json': inventory, 'BUILD-PROVENANCE.json': {}})
        record = {'sourceCommit': 'a' * 40, 'packs': packs, 'sourceCompanion': gate.file_record(companion)}
        gate.write_json(self.root / 'BUILD-PROVENANCE.json', record)
        return record

    def test_candidate_requires_both_exact_selected_pack_identities(self):
        record = self.fixture()
        self.assertEqual(gate.common.verify_candidate(self.root, 'a' * 40), record)
        for missing in ('bustools', 'stringtie'):
            with self.subTest(missing=missing):
                changed = {**record, 'packs': {key: value for key, value in record['packs'].items() if key != missing}}
                gate.write_json(self.root / 'BUILD-PROVENANCE.json', changed)
                with self.assertRaisesRegex(ValueError, 'source/packs'):
                    gate.common.verify_candidate(self.root, 'a' * 40)
        record['packs']['kalign'] = record['packs']['bustools']
        gate.write_json(self.root / 'BUILD-PROVENANCE.json', record)
        with self.assertRaisesRegex(ValueError, 'source/packs'):
            gate.common.verify_candidate(self.root, 'a' * 40)

    def test_each_frozen_pack_requires_exact_bytes(self):
        record = self.fixture()
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                path = self.root / record['packs'][identity]['file']
                original = path.read_bytes()
                path.write_bytes(b'changed candidate bytes')
                with self.assertRaisesRegex(ValueError, 'artifact differs'):
                    gate.common.verify_candidate(self.root, 'a' * 40)
                path.write_bytes(original)

    def test_companion_requires_exact_bytes_and_commit(self):
        record = self.fixture()
        with self.assertRaisesRegex(ValueError, 'source/packs'):
            gate.common.verify_candidate(self.root, 'b' * 40)
        path = self.root / record['sourceCompanion']['file']
        path.write_bytes(path.read_bytes() + b'extra')
        with self.assertRaisesRegex(ValueError, 'artifact differs'):
            gate.common.verify_candidate(self.root, 'a' * 40)

    def test_validator_recheck_cannot_hide_production_or_shared_helper_changes(self):
        for name in ('scripts/build_bustools_native.py', 'scripts/prepare_stringtie_pack.py',
                     'tools/bustools/guard.cpp', 'tools/stringtie/guard.cpp',
                     'tests/test_bustools_pack.py', 'tests/test_stringtie_pack.py',
                     'scripts/check_prodigal_fasttree_windows.py', 'workspace/catalog.py'):
            self.assertFalse(gate.common.allowed_gate_change(name), name)
        with mock.patch.object(gate.common.subprocess, 'check_output', side_effect=[
                'b' * 40 + '\n', b'scripts/check_bustools_stringtie_gui.py\0tools/stringtie/guard.cpp\0']):
            with self.assertRaisesRegex(ValueError, 'production or recipe'):
                gate.common.frozen_source_changes('a' * 40, 'b' * 40)

    def test_private_helper_configuration_preserves_existing_candidate(self):
        original_spec = importlib.util.spec_from_file_location('original_pack_gate', ROOT / 'scripts/check_prodigal_fasttree_windows.py')
        original = importlib.util.module_from_spec(original_spec)
        original_spec.loader.exec_module(original)
        self.assertEqual(original.PACK_IDS, ('prodigal', 'fasttree'))
        self.assertEqual(gate.PACK_IDS, ('bustools', 'stringtie'))
        self.assertEqual(gate.common.OPERATIONS, {'bustools': {'count-bus'}, 'stringtie': {'assemble-guided', 'estimate-reference'}})
        self.assertEqual(gate.APPLICATIONS, original.APPLICATIONS)

    def test_source_or_skipped_report_cannot_claim_native_science(self):
        passed = {'success': True, 'nativeWindowsExecuted': True, 'testsRun': 2,
                  'skipped': [], 'executions': [{'returncode': 0}]}
        self.assertTrue(gate.scientific_report_passed(passed))
        for field, value in [('success', False), ('nativeWindowsExecuted', False),
                             ('testsRun', 0), ('testsRun', None),
                             ('skipped', [['test_x', 'no executable']]), ('executions', [])]:
            with self.subTest(field=field, value=value):
                self.assertFalse(gate.scientific_report_passed({**passed, field: value}))

    @staticmethod
    def correspondence_fixture(identity):
        paths = {
            'pack/licenses/guard.cpp': 'tools/' + identity + '/guard.cpp',
            'pack/licenses/fixtures.py': 'tools/' + identity + '/fixtures.py',
            'pack/licenses/build_' + identity + '_native.py': 'scripts/build_' + identity + '_native.py',
            'pack/licenses/prepare_' + identity + '_pack.py': 'scripts/prepare_' + identity + '_pack.py',
            'pack/PACK-README.md': 'docs/' + identity.upper() + '-PACK.md',
            'pack/licenses/Workbench-LICENSE.txt': 'LICENSE',
        }
        originals = {name: ('committed fixture ' + name).encode() for name in paths.values()}
        originals['tools/' + identity + '/fixtures.py'] = (ROOT / ('tools/' + identity + '/fixtures.py')).read_bytes()
        for original in audit.EXTERNAL_NOTICE_PINS:
            if original.startswith('tools/' + identity + '/'):
                originals[original] = (ROOT / original).read_bytes()
                paths['pack/licenses/' + original.rsplit('/', 1)[1]] = original
        retained = {name: originals[source] for name, source in paths.items()}
        retained.update({'pack/fixtures/' + name: data for name, data in audit.expected_generated_fixtures(identity, originals).items()})
        version, commit = audit.UPSTREAM_IDENTITIES[identity]
        patch = b''.join(('--- a/' + path + '\n+++ b/' + path + '\n@@ -1 +1 @@\n-old\n+new\n').encode()
                         for path in sorted(audit.PATCH_PATHS.get(identity, set())))
        if patch:
            retained['pack/licenses/workbench1.patch'] = patch
        retained['pack/licenses/compiler-LICENSE.TXT'] = b'compiler notice fixture'
        build = {'platform': 'windows-x86_64', 'executionTestsPerformedByBuild': False,
                 'version': version + ('-workbench1' if identity in audit.PATCH_PATHS else ''), 'upstreamVersion': version, 'sourceCommit': commit,
                 'upstreamCommit': commit, 'upstreamSourceUnmodified': identity not in audit.PATCH_PATHS,
                 'upstreamScientificAlgorithmsUnmodified': True, 'sortThreads': 1, 'openmp': False, 'threadsExposed': 1,
                 'builderSha256': audit.digest(originals['scripts/build_' + identity + '_native.py']),
                 'guardSourceSha256': audit.digest(originals['tools/' + identity + '/guard.cpp']),
                 'patchSha256': audit.digest(patch) if patch else None, '_fixtureReviewedPatchSha256': audit.digest(patch),
                 'compilerNotices': {'LICENSE.TXT': audit.digest(retained['pack/licenses/compiler-LICENSE.TXT'])},
                 'files': {}, 'sources': {}}
        # Fixture PE headers exercise architecture and stack checks; they are
        # synthetic data, not native executable or execution evidence.
        header = bytearray(256)
        header[:2] = b'MZ'
        struct.pack_into('<I', header, 60, 64)
        header[64:68] = b'PE\0\0'
        struct.pack_into('<H', header, 68, 0x8664)
        struct.pack_into('<H', header, 88, 0x20b)
        struct.pack_into('<QQ', header, 160, 8388608, 65536)
        for name in [identity + '.exe', identity + '-guard.exe']:
            data = bytes(header) + name.encode()
            retained['pack/bin/' + name] = data
            build['files'][name] = {'bytes': len(data), 'sha256': audit.digest(data)}
        for source_name in audit.UPSTREAM_PINS[identity]:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:gz') as archive:
                mappings = audit.NOTICE_PATHS[identity].get(source_name, {})
                if identity == 'stringtie' and source_name == 'tre-0.9.0.tar.gz':
                    for name in ('config.h', 'tre-config.h'):
                        data = ('TRE upstream configuration ' + name).encode()
                        info = tarfile.TarInfo('tre-0.9.0/win32/' + name)
                        info.size = len(data)
                        archive.addfile(info, io.BytesIO(data))
                        retained['pack/licenses/configuration/tre-config/' + name] = data
                for original, target in mappings.items():
                    data = ('Original upstream source notice ' + original).encode()
                    info = tarfile.TarInfo(original)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                    retained['pack/licenses/' + target] = data
            retained['pack/licenses/' + source_name] = stream.getvalue()
        if identity == 'stringtie':
            for name, data in audit.STRINGTIE_CONFIGURATION.items():
                retained['pack/licenses/configuration/' + name] = data
            prefix = 'pack/licenses/configuration/'
            build['generatedConfiguration'] = {name.removeprefix(prefix): audit.digest(data)
                for name, data in retained.items() if name.startswith(prefix)}
        pins = {name: audit.digest(retained['pack/licenses/' + name]) for name in audit.UPSTREAM_PINS[identity]}
        build['sources'] = {name: {'sha256': checksum} for name, checksum in pins.items()}
        return originals, retained, build, pins

    def correspondence(self, identity, originals, retained, build, pins):
        retained['pack/licenses/build-provenance.json'] = json.dumps(build).encode()
        pack = mock.Mock()
        pack.read.side_effect = retained.__getitem__
        pack.namelist.side_effect = lambda: list(retained)
        # Replace only known test archive pins, so all byte/provenance checks run
        # over a tiny self-contained fixture rather than downloaded sources.
        with mock.patch.dict(audit.UPSTREAM_PINS, {identity: pins}), mock.patch.object(audit, 'BUSTOOLS_PATCH_SHA256', build['_fixtureReviewedPatchSha256']):
            return audit.source_correspondence(identity, pack, originals)

    def test_compiled_guard_and_recipe_must_match_the_committed_sources(self):
        for identity in ('bustools', 'stringtie'):
            for field in ('guardSourceSha256', 'builderSha256'):
                with self.subTest(identity=identity, field=field):
                    originals, retained, build, pins = self.correspondence_fixture(identity)
                    build[field] = '0' * 64
                    with self.assertRaisesRegex(ValueError, 'Compiled .* provenance differs'):
                        self.correspondence(identity, originals, retained, build, pins)

    def test_retained_guard_cannot_be_changed_to_match_a_different_build(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                retained['pack/licenses/guard.cpp'] += b' changed'
                build['guardSourceSha256'] = audit.digest(retained['pack/licenses/guard.cpp'])
                with self.assertRaisesRegex(ValueError, 'retained source differs from Git'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_unreviewed_source_pin_is_rejected_even_with_updated_build_hash(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                name = next(iter(pins))
                retained['pack/licenses/' + name] += b' changed upstream bytes'
                build['sources'][name]['sha256'] = audit.digest(retained['pack/licenses/' + name])
                with self.assertRaisesRegex(ValueError, 'Pinned corresponding source changed'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_unreviewed_upstream_commit_is_rejected(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                build['sourceCommit'] = build['upstreamCommit'] = '0' * 40
                with self.assertRaisesRegex(ValueError, 'Unexpected upstream identity'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_rehashed_patch_with_unreviewed_path_is_rejected(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                self.correspondence(identity, originals, retained, build, pins)
                retained['pack/licenses/workbench1.patch'] = retained.get('pack/licenses/workbench1.patch', b'') + b'--- a/science.cpp\n+++ b/science.cpp\n'
                build['patchSha256'] = audit.digest(retained['pack/licenses/workbench1.patch'])
                with self.assertRaisesRegex(ValueError, '(Pinned|Unreviewed) compatibility patch'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_upstream_notices_must_match_the_pinned_source_archive(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                self.correspondence(identity, originals, retained, build, pins)
                mappings = next(iter(audit.NOTICE_PATHS[identity].values()))
                retained['pack/licenses/' + next(iter(mappings.values()))] += b' changed notice'
                with self.assertRaisesRegex(ValueError, 'Upstream component notice differs'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_rehashed_non_native_binary_is_rejected(self):
        for identity in ('bustools', 'stringtie'):
            with self.subTest(identity=identity):
                originals, retained, build, pins = self.correspondence_fixture(identity)
                name = identity + '.exe'
                retained['pack/bin/' + name] = b'not a native executable'
                build['files'][name] = {'bytes': len(retained['pack/bin/' + name]),
                                       'sha256': audit.digest(retained['pack/bin/' + name])}
                with self.assertRaisesRegex(ValueError, 'not a PE executable'):
                    self.correspondence(identity, originals, retained, build, pins)

    def test_rehashed_fixture_cannot_override_the_source_oracle(self):
        originals, retained, build, pins = self.correspondence_fixture('bustools')
        retained['pack/fixtures/expected.json'] = b'{"count": 6}'
        with self.assertRaisesRegex(ValueError, 'Fixture differs from Git'):
            self.correspondence('bustools', originals, retained, build, pins)

    def test_reinventoried_generated_configuration_cannot_enable_other_features(self):
        originals, retained, build, pins = self.correspondence_fixture('stringtie')
        self.correspondence('stringtie', originals, retained, build, pins)
        name = 'config/config.h'
        retained['pack/licenses/configuration/' + name] += b'#define ENABLE_REMOTE_PLUGINS 1\n'
        build['generatedConfiguration'][name] = audit.digest(retained['pack/licenses/configuration/' + name])
        with self.assertRaisesRegex(ValueError, 'Generated native configuration differs'):
            self.correspondence('stringtie', originals, retained, build, pins)

    def test_generated_bam_requires_exact_deterministic_bgzf_bytes(self):
        originals, retained, build, pins = self.correspondence_fixture('stringtie')
        self.correspondence('stringtie', originals, retained, build, pins)
        name = 'pack/fixtures/spliced.bam'
        changed = bytearray(retained[name])
        changed[4] = 1  # Gzip mtime only; decoded alignment records are unchanged.
        retained[name] = bytes(changed)
        with self.assertRaisesRegex(ValueError, 'Fixture differs from Git factory: spliced.bam'):
            self.correspondence('stringtie', originals, retained, build, pins)


if __name__ == '__main__':
    unittest.main()
