"""Fail-closed batch evidence contracts; these tests do not execute Windows."""
from __future__ import annotations

import importlib.util
import copy
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

    def memory_regression_fixture(self):
        pack = self.root / 'stringtie'
        for name in ('bin/stringtie-guard.exe', 'fixtures/spliced.bam', 'fixtures/guide.gtf'):
            path = pack / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        binding = {'files': {'flag-layout-check.cpp': {'sha256': 'a' * 64},
                             'flag-layout-check.exe': {'sha256': 'b' * 64}},
                   'build': {'patchedHeaderSha256': 'c' * 64}}
        poison = {'executed': True, 'returncode': 0, 'sourceSha256': 'a' * 64,
                  'executableSha256': 'b' * 64, 'patchedHeaderSha256': 'c' * 64,
                  'result': {'success': True, 'unionBytes': 4, 'poison': 165, 'fieldsChecked': 19}}
        report = {'memoryBoundaryRegression': {'poisonedLayout': poison,
                  'repeatedModes': {'assemble-guided': 10, 'estimate-reference': 10}, 'fullOutputOracle': True},
                  'executions': [{'operation': mode, 'repetition': repeat, 'returncode': 0,
                      'expectedSuccess': True, 'outputOraclePassed': True,
                      'guardSha256': gate.sha(pack / 'bin/stringtie-guard.exe'),
                      'bamSha256': gate.sha(pack / 'fixtures/spliced.bam'),
                      'gtfSha256': gate.sha(pack / 'fixtures/guide.gtf')}
                     for mode in ('assemble-guided', 'estimate-reference') for repeat in range(1, 11)]}
        return report, binding, pack

    def test_native_heap_regression_rejects_missing_duplicate_or_intermittent_runs(self):
        report, binding, pack = self.memory_regression_fixture()
        self.assertTrue(gate.stringtie_memory_regression_passed(report, binding, pack))
        for field, value in [('returncode', -1073740940), ('outputOraclePassed', False),
                             ('guardSha256', 'f' * 64), ('bamSha256', 'f' * 64),
                             ('gtfSha256', 'f' * 64), ('repetition', 2)]:
            changed = copy.deepcopy(report)
            changed['executions'][0][field] = value
            with self.subTest(field=field):
                self.assertFalse(gate.stringtie_memory_regression_passed(changed, binding, pack))
        changed = copy.deepcopy(report)
        changed['executions'].pop()
        self.assertFalse(gate.stringtie_memory_regression_passed(changed, binding, pack))

    def test_native_heap_regression_requires_the_exact_executed_poison_probe(self):
        report, binding, pack = self.memory_regression_fixture()
        for field, value in [('executed', False), ('returncode', 3), ('sourceSha256', 'f' * 64),
                             ('executableSha256', 'f' * 64), ('patchedHeaderSha256', 'f' * 64),
                             ('result', {'success': True, 'unionBytes': 8, 'poison': 165, 'fieldsChecked': 19})]:
            changed = copy.deepcopy(report)
            changed['memoryBoundaryRegression']['poisonedLayout'][field] = value
            with self.subTest(field=field):
                self.assertFalse(gate.stringtie_memory_regression_passed(changed, binding, pack))
        changed = copy.deepcopy(report)
        changed['memoryBoundaryRegression']['fullOutputOracle'] = False
        self.assertFalse(gate.stringtie_memory_regression_passed(changed, binding, pack))

    def test_layout_probe_extraction_binds_runtime_pack_recipe_compiler_and_patch(self):
        pack = self.root / 'pack'
        (pack / 'licenses').mkdir(parents=True)
        source, executable = b'probe source', b'probe binary'
        diagnostic = {'sourceSha256': audit.digest(source), 'executableSha256': audit.digest(executable),
            'builderSha256': 'a' * 64, 'compilerSha256': 'b' * 64, 'patchSha256': 'c' * 64,
            'nativeExecutionPerformed': False}
        build = {'builderSha256': 'a' * 64, 'guardCompilerSha256': 'b' * 64,
                 'patchSha256': 'c' * 64, 'flagLayoutCheck': diagnostic}
        gate.write_json(pack / 'licenses/build-provenance.json', build)
        with gate.zipfile.ZipFile(self.root / 'source.zip', 'w') as companion:
            prefix = 'build-evidence/1/stringtie-flags/'
            for name, data in [('flag-layout-check.cpp', source), ('flag-layout-check.exe', executable),
                               ('flag-layout-check.json', json.dumps(diagnostic).encode())]:
                companion.writestr(prefix + name, data)
        frozen = {'sourceCompanion': {'file': 'source.zip'}}
        path, binding = gate.extract_stringtie_layout_check(self.root, frozen, self.root / 'recovered', pack)
        self.assertEqual(path.read_bytes(), executable)
        self.assertEqual(binding['files']['flag-layout-check.cpp']['sha256'], audit.digest(source))
        for field in ('builderSha256', 'guardCompilerSha256', 'patchSha256'):
            changed = {**build, field: 'f' * 64}
            gate.write_json(pack / 'licenses/build-provenance.json', changed)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'recipe, compiler or patch'):
                gate.extract_stringtie_layout_check(self.root, frozen, self.root / 'recovered', pack)

    def test_layout_source_audit_reconstructs_upstream_header_and_rejects_resigned_probe_changes(self):
        header = ('class GffObj:public GSeg {\n   union {\n      unsigned int flags;\n      struct {\n' +
                  ''.join('        bool flag_' + str(i) + ' :1;\n' for i in range(17)) +
                  '        unsigned int gff_level :4;\n        unsigned int flag_USER_FLAGS :8;\n'
                  '      };\n   };\n   //-- friends:\n};\n')
        patched = header.replace('bool flag_', 'unsigned int flag_').replace('      unsigned int flags;',
            '      // Workbench: one 32-bit storage unit also under the Windows bitfield ABI.\n      unsigned int flags;')
        # The fixture generator emits its supplied header verbatim, making the
        # independently reconstructed header comparison explicit and observable.
        recipe = b'def flag_layout_probe(header):\n    return header\n'
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            entry = tarfile.TarInfo('stringtie-' + audit.UPSTREAM_IDENTITIES['stringtie'][1] + '/gclib/gff.h')
            entry.size = len(header.encode())
            archive.addfile(entry, io.BytesIO(header.encode()))
        pe = bytearray(256)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 128)
        pe[128:132] = b'PE\0\0'
        struct.pack_into('<H', pe, 132, 0x8664)
        diagnostic = {'sourceSha256': audit.digest(patched.encode()), 'executableSha256': audit.digest(pe),
            'builderSha256': audit.digest(recipe), 'compilerSha256': 'c' * 64,
            'patchSha256': audit.PATCH_SHA256['stringtie'], 'nativeExecutionPerformed': False,
            'patchedHeaderSha256': audit.digest(patched.encode())}
        build = {'flagLayoutCheck': diagnostic, 'guardCompilerSha256': 'c' * 64,
                 'patchSha256': audit.PATCH_SHA256['stringtie']}
        prefix = 'build-evidence/1/stringtie-flags/'
        data = {prefix + 'flag-layout-check.cpp': patched.encode(), prefix + 'flag-layout-check.exe': bytes(pe),
                'corresponding-sources/stringtie/stringtie-3.0.3.tar.gz': stream.getvalue()}
        source = mock.Mock()
        source.namelist.side_effect = lambda: list(data)
        source.read.side_effect = data.__getitem__
        originals = {'scripts/build_stringtie_native.py': recipe}
        def check():
            data[prefix + 'flag-layout-check.json'] = json.dumps(diagnostic).encode()
            data['corresponding-sources/stringtie/build-provenance.json'] = json.dumps(build).encode()
            with mock.patch.dict(audit.UPSTREAM_PINS, {'stringtie': {'stringtie-3.0.3.tar.gz': audit.digest(stream.getvalue())}}):
                return audit.stringtie_layout_diagnostic(source, originals)
        self.assertFalse(check()['nativeExecutionVerified'])
        data[prefix + 'flag-layout-check.cpp'] += b'changed probe with newly calculated hash\n'
        diagnostic['sourceSha256'] = audit.digest(data[prefix + 'flag-layout-check.cpp'])
        with self.assertRaisesRegex(ValueError, 'exact flag-union generator'):
            check()
        diagnostic['patchedHeaderSha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'patched header differs'):
            check()

    @staticmethod
    def dependency_catalog():
        tools = {}
        for operation in ('assemble-guided', 'estimate-reference'):
            tools['stringtie/' + operation] = {'id': 'stringtie/' + operation,
                'packId': 'stringtie', 'packVersion': '1.0.0', 'manifestSha256': 'a' * 64,
                'packFolder': 'packs/stringtie-1.0.0', 'executables': [],
                'ports': [{'type': 'bam-rna', 'requiredState': {'sort': 'coordinate'}}]}
        tools[gate.SAMTOOLS['operation']] = {'id': gate.SAMTOOLS['operation'],
            **{key: gate.SAMTOOLS[key] for key in ('packId', 'packVersion', 'manifestSha256')},
            'packFolder': 'packs/bam-0.4.0',
            'executables': [{key: gate.SAMTOOLS[key] for key in ('id', 'version', 'sha256', 'path')}]}
        tools['unrelated/check'] = {'id': 'unrelated/check', 'packId': 'unrelated', 'packVersion': '2.0.0',
                                    'manifestSha256': 'b' * 64, 'executables': []}
        return {'tools': tools, 'toolVersions': {key: [value] for key, value in tools.items()},
                'packs': [{'id': name, 'version': version} for name, version in
                          [('stringtie', '1.0.0'), ('bam', '0.4.0'), ('unrelated', '2.0.0')]]}

    def test_candidate_checks_keep_real_samtools_preflight_and_exclude_unrelated_tools(self):
        # Exercise the actual engine selector: the historical one-pack filter
        # reproduces the observed failure even though Starter has the helper.
        before = list(sys.path)
        try:
            sys.path.insert(0, str(ROOT))
            from workspace.engine import Engine
        finally:
            sys.path[:] = before
        catalog = self.dependency_catalog()
        original = copy.deepcopy(catalog)
        selected, dependency = gate.candidate_check_catalog(catalog, 'stringtie', '1.0.0')
        self.assertEqual(catalog, original)
        self.assertEqual(set(selected['tools']), {'stringtie/assemble-guided', 'stringtie/estimate-reference', 'bam/flagstat'})
        engine = Engine.__new__(Engine)
        engine.catalog, engine.tools = selected, selected['tools']
        owner = selected['tools']['stringtie/assemble-guided']
        self.assertEqual(len(engine._alignment_ports(owner)), 1)
        helper = engine._samtools_selection(owner)
        self.assertEqual(helper['operation'], gate.SAMTOOLS['operation'])
        self.assertEqual(helper['pin']['manifestSha256'], gate.SAMTOOLS['manifestSha256'])
        self.assertEqual(helper['executable']['sha256'], gate.SAMTOOLS['sha256'])
        broken = copy.deepcopy(selected)
        del broken['toolVersions'][dependency['id']]
        del broken['tools'][dependency['id']]
        engine.catalog, engine.tools = broken, broken['tools']
        with self.assertRaisesRegex(ValueError, 'Install a SAMtools pack'):
            engine._samtools_selection(owner)

    def test_candidate_checks_reject_absent_or_changed_samtools_dependencies(self):
        for mutation in ('absent', 'manifest', 'binary', 'version'):
            with self.subTest(mutation=mutation):
                catalog = self.dependency_catalog()
                dependency = catalog['toolVersions'][gate.SAMTOOLS['operation']][0]
                if mutation == 'absent':
                    del catalog['toolVersions'][gate.SAMTOOLS['operation']]
                elif mutation == 'manifest':
                    dependency['manifestSha256'] = '0' * 64
                elif mutation == 'binary':
                    dependency['executables'][0]['sha256'] = '0' * 64
                else:
                    dependency['executables'][0]['version'] = '1.25'
                with self.assertRaisesRegex(ValueError, 'Exact Starter SAMtools .* absent or changed'):
                    gate.candidate_check_catalog(catalog, 'stringtie', '1.0.0')

    def test_installation_deadline_cancels_backend_and_preserves_partial_failure(self):
        backend = mock.Mock()
        report = {}
        results = self.root / 'check evidence with spaces'
        def blocked_runner(root, catalog, folder, *, backend, cancel, event):
            event({'type': 'log', 'message': 'Child started; waiting for cancellation.'})
            (folder / 'partial-child.log').write_text('retained child stderr\n')
            self.assertTrue(cancel.wait(1), 'Deadline did not deliver the ordinary cancellation event.')
            return {'success': True, 'cancelled': True, 'checks': [{'status': 'failed', 'message': 'cancelled'}]}
        with self.assertRaisesRegex(ValueError, 'exceeded the .* deadline'):
            gate.timed_installation_checks(self.root, {}, results, backend, blocked_runner, report, seconds=.02)
        backend.shutdown.assert_called_once()
        self.assertTrue(report['scientificDeadline']['exceeded'])
        self.assertTrue(report['scientificDeadline']['cancellationRequested'])
        self.assertTrue(report['scientificChecks']['cancelled'])
        self.assertEqual((results / 'partial-child.log').read_text(), 'retained child stderr\n')
        self.assertIn('validation deadline', (results / 'installation-events.jsonl').read_text())

    def test_installation_timer_is_cancelled_after_runner_failure(self):
        backend = mock.Mock()
        report = {}
        with mock.patch.object(gate.threading, 'Timer') as timer:
            with self.assertRaisesRegex(RuntimeError, 'early failure'):
                gate.timed_installation_checks(self.root, {}, self.root / 'early-failure', backend,
                    mock.Mock(side_effect=RuntimeError('early failure')), report)
            timer.return_value.start.assert_called_once()
            timer.return_value.cancel.assert_called_once()
        backend.shutdown.assert_not_called()
        self.assertFalse(report['scientificDeadline']['exceeded'])

    def test_deadline_starting_during_timer_cleanup_cannot_be_reported_as_success(self):
        report, backend = {}, mock.Mock()
        with mock.patch.object(gate.threading, 'Timer') as timer:
            # Reproduce the boundary where the runner has just returned but a
            # deadline callback starts before cancel() can prevent it.
            timer.return_value.cancel.side_effect = lambda: timer.call_args.args[1]()
            with self.assertRaisesRegex(ValueError, 'exceeded the .* deadline'):
                gate.timed_installation_checks(self.root, {}, self.root / 'deadline-race', backend,
                    mock.Mock(return_value={'success': True}), report)
            timer.return_value.join.assert_called_once()
        backend.shutdown.assert_called_once()
        self.assertTrue(report['scientificDeadline']['exceeded'])

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
            if identity == 'stringtie':
                originals['tools/stringtie/workbench1.patch'] = patch
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
        with mock.patch.dict(audit.UPSTREAM_PINS, {identity: pins}), mock.patch.dict(audit.PATCH_SHA256, {identity: build['_fixtureReviewedPatchSha256']}):
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
                with self.assertRaisesRegex(ValueError, '(Pinned|Unreviewed) compatibility patch|retained source differs from Git'):
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
