#!/usr/bin/env python3
"""Build the 0.7.0 reference candidate with the established application recipes.

This creates new artifacts only. It does not publish or claim native Windows
acceptance; the release workflow runs that separate gate on downloaded bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
VERSION = '0.7.0'
ARCHIVE_NAMES = (
    f'native-workbench-{VERSION}-source.zip',
    f'native-workbench-{VERSION}-starter-windows.zip',
    f'native-workbench-{VERSION}-update-from-0.6.0.zip',
)
REPORT_NAME = 'reference-build-report.json'
README_NAME = 'REFERENCE-CANDIDATE-README.md'
CHECKSUM_NAME = 'SHA256SUMS.txt'
ASSET_NAMES = (*ARCHIVE_NAMES, REPORT_NAME, README_NAME, CHECKSUM_NAME)
INPUTS = {
    'native-workbench-0.6.0-starter-windows.zip':
        '16fa802304c734b5721d838ff38b7e90ed36ccfc185a22239859cc3762af695a',
    'native-workbench-0.6.0-source.zip':
        '427a9b42f2528984350479e8b0155e4ef4f0159fa6f240cc1aa84a5ec2e0e60a',
    'llvm-mingw-20260922-ucrt-ubuntu-22.04-x86_64.tar.xz':
        'bb7bb7654b33d5aa8712acb837c963b2e0c56352560c76105270a3268c665c21',
}
SUITES = [
    ('workspace/tests/test_reference_provider.py', []),
    ('workspace/tests/test_reference_manager.py', []),
    ('workspace/tests/test_reference_service.py', []),
    ('workspace/tests/test_reference_provenance.py', []),
    ('workspace/tests/test_desktop_host.py', []),
    ('workspace/tests/test_pack_service.py', []),
    ('workspace/tests/test_pack_versions.py', []),
    ('workspace/tests/test_pack_schema.py', []),
    ('tests/test_split_release.py', []),
    ('tests/test_core_update.py', []),
    ('tests/test_reference_release.py', []),
    ('tests/test_core_checks.py', [
        'CoreChecksTests.test_only_explicit_download_clients_can_import_network_and_never_listener',
        'CoreChecksTests.test_real_catalogue_citation_parser_passes_frontend_client_boundary',
    ]),
]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def record(path):
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def exact_files(folder, expected):
    members = list(folder.iterdir())
    actual = {path.name for path in members}
    if actual != set(expected):
        raise RuntimeError('Release file set differs: extra=' + repr(sorted(actual - set(expected))) +
                           ', missing=' + repr(sorted(set(expected) - actual)))
    if any(path.is_symlink() or not path.is_file() for path in members):
        raise RuntimeError('Release assets must be ordinary files, without links or directories.')


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not members or len(members) != len({item.filename for item in members}):
            raise RuntimeError('Archive is empty or has duplicate members: ' + path.name)
        if archive.testzip() is not None:
            raise RuntimeError('Archive CRC failed: ' + path.name)
    return {'file': path.name, 'members': len(members), 'crc': 'passed'}


def verify_release(output):
    """Fail closed on extra assets, stale checksums or changed archive members."""
    exact_files(output, ASSET_NAMES)
    expected_lines = [sha(output / name) + '  ' + name for name in sorted(ASSET_NAMES)
                      if name != CHECKSUM_NAME]
    if (output / CHECKSUM_NAME).read_text(encoding='utf-8').splitlines() != expected_lines:
        raise RuntimeError('Checksums must identify exactly the five intended payload assets.')
    report = json.loads((output / REPORT_NAME).read_text(encoding='utf-8'))
    artifacts = {item['file']: item for item in report['artifacts']}
    if len(artifacts) != len(report['artifacts']) or set(artifacts) != set(ARCHIVE_NAMES):
        raise RuntimeError('Build report archive set differs.')
    for name, expected in artifacts.items():
        if record(output / name) != expected:
            raise RuntimeError('Build report archive size/hash differs: ' + name)
    checks = [verify_archive(output / name) for name in ARCHIVE_NAMES]
    # Repeat the set check after reads: a new partial file is a failure even if
    # all intended archives individually verified successfully.
    exact_files(output, ASSET_NAMES)
    return {'schema': 1, 'success': True, 'scope': 'Publication asset integrity only; native acceptance is separate',
            'source_commit': report['source_commit'], 'assets': [record(output / name) for name in ASSET_NAMES],
            'archives': checks, 'final_release': False}


def diagnostic(path, output, error):
    value = {'schema': 1, 'success': False, 'scope': 'Publication readiness',
             'error': type(error).__name__ + ': ' + str(error), 'final_release': False}
    if output.is_dir():
        value['observed_files'] = [record(member) if member.is_file() and not member.is_symlink()
                                   else {'file': member.name, 'ordinary_file': False}
                                   for member in sorted(output.iterdir())]
    write_json(path, value)


def run_suite(path, report, selectors):
    # Each suite gets a fresh interpreter, avoiding cross-suite import caches.
    path = path.resolve()
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    loader = unittest.TestLoader()
    suite = (loader.loadTestsFromNames(selectors, module) if selectors
             else loader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    value = {'suite': str(path.relative_to(SOURCE)), 'tests': result.testsRun,
             'failures': len(result.failures), 'errors': len(result.errors),
             'skipped': len(result.skipped), 'unexpected_successes': len(result.unexpectedSuccesses),
             'expected_failures': len(result.expectedFailures),
             'success': result.wasSuccessful() and result.testsRun > 0 and not result.skipped
                        and not result.expectedFailures}
    write_json(report, value)
    return 0 if value['success'] else 1


def build(args):
    output = args.output.resolve()
    work = args.work.resolve()
    if output.exists() or work.exists():
        raise RuntimeError('Choose new output and working directories; artifacts are immutable.')
    output.mkdir(parents=True)
    work.mkdir(parents=True)
    evidence = work / 'evidence'
    evidence.mkdir()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    if commit != args.source_commit:
        raise RuntimeError('Checkout differs from the requested source commit.')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'],
                               cwd=SOURCE, text=True).strip():
        raise RuntimeError('All source changes must be committed before a candidate build.')
    toolchain = Path(os.environ['BW_MINGW_ROOT']).resolve()
    os.environ['LD_LIBRARY_PATH'] = str(toolchain / 'lib') + (
        os.pathsep + os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')

    inputs = []
    for name, expected in INPUTS.items():
        path = args.inputs / name
        item = record(path)
        if item['sha256'] != expected:
            raise RuntimeError('Pinned build input differs: ' + name)
        inputs.append(item)
    with zipfile.ZipFile(args.inputs / 'native-workbench-0.6.0-starter-windows.zip') as archive:
        archive.extractall(work / 'baseline')
    baseline = work / 'baseline/native-workbench'
    sys.path.insert(0, str(SOURCE / 'scripts'))
    from apply_core_update import core_inventory
    from apply_desktop_update import inside, read_json, verify
    from package_split import VERSION as actual_version
    if actual_version != VERSION:
        raise RuntimeError('This release recipe requires application ' + VERSION)
    inventory = core_inventory(read_json(baseline / 'manifest.json'))
    for name, item in inventory.items():
        verify(inside(baseline, name), item['sha256'], item['bytes'])

    suites = []
    for number, (name, selectors) in enumerate(SUITES):
        report = evidence / f'suite-{number:02d}.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--run-suite',
                   str(SOURCE / name), '--suite-report', str(report), *selectors]
        result = subprocess.run(command, cwd=SOURCE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        (evidence / f'suite-{number:02d}.log').write_text(result.stdout, encoding='utf-8')
        print(result.stdout, end='', flush=True)
        if report.exists():
            suites.append(json.loads(report.read_text(encoding='utf-8')))
        write_json(evidence / 'source-checks.json', {'scope': 'Linux source contracts only',
                   'source_commit': commit, 'suites': suites})
        if result.returncode:
            raise RuntimeError('Source check failed: ' + name)

    totals = {key: sum(suite[key] for suite in suites) for key in
              ('tests', 'failures', 'errors', 'skipped', 'unexpected_successes', 'expected_failures')}
    totals['passed'] = totals['tests'] - sum(totals[key] for key in
        ('failures', 'errors', 'skipped', 'unexpected_successes', 'expected_failures'))
    totals['success'] = all(suite['success'] for suite in suites)
    write_json(evidence / 'source-checks.json', {'scope': 'Linux source contracts only',
               'source_commit': commit, **totals, 'suites': suites})

    def command(name, argv):
        with (evidence / (name + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run(argv, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, check=True)

    for name in ('build_desktop_workspace', 'build_bridge', 'build_workspace_update_launcher'):
        command(name, ['bash', 'desktop/' + name + '.sh'])
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'],
                               cwd=SOURCE, text=True).strip():
        raise RuntimeError('Source changed during validation or compilation; refusing to package.')
    source = output / f'native-workbench-{VERSION}-source.zip'
    starter = output / f'native-workbench-{VERSION}-starter-windows.zip'
    updater = output / f'native-workbench-{VERSION}-update-from-0.6.0.zip'
    metadata = evidence / 'source-metadata.json'
    app = work / 'stage/native-workbench'
    command('package-sources', [sys.executable, 'scripts/package_split.py', 'sources',
            '--base-root', str(baseline), '--base-source-archive',
            str(args.inputs / 'native-workbench-0.6.0-source.zip'),
            '--output', str(source), '--metadata', str(metadata)])
    command('package-stage', [sys.executable, 'scripts/package_split.py', 'stage',
            '--base-root', str(baseline), '--app-root', str(app), '--source-metadata', str(metadata)])
    command('package-starter', [sys.executable, 'scripts/package_split.py', 'starter',
            '--app-root', str(app), '--output', str(starter)])
    command('package-updater', [sys.executable, 'scripts/make_core_update.py',
            '--base-root', str(baseline), '--app-root', str(app),
            '--output', str(work / 'update'), '--launcher',
            str(SOURCE / 'build/desktop/UpdateWorkbench.exe'), '--zip', str(updater)])
    exact_files(output, ARCHIVE_NAMES)
    with zipfile.ZipFile(source) as archive:
        source_inventory = json.loads(archive.read('SOURCE-RECOVERY.json'))['current_source_files']
    archive_checks = [verify_archive(output / name) for name in ARCHIVE_NAMES]
    compiler = toolchain / 'bin/x86_64-w64-mingw32-clang++'
    report = {'schema': 1, 'app_version': VERSION, 'candidate_tag': args.release_tag,
              'source_commit': commit, 'source_tree': subprocess.check_output(
                  ['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip(),
              'workflow_run': os.environ.get('GITHUB_SERVER_URL', 'https://github.com') + '/' +
                  os.environ.get('GITHUB_REPOSITORY', 'comparativechrono/workbench') + '/actions/runs/' +
                  os.environ.get('GITHUB_RUN_ID', ''),
              'platform': platform.platform(), 'python': sys.version,
              'compiler': subprocess.check_output([str(compiler), '--version'], text=True),
              'build_inputs': inputs, 'baseline_core_files_verified': len(inventory),
              'source_checks': {'totals': totals, 'suites': suites}, 'source_files': source_inventory,
              'native_binaries': [record(SOURCE / 'build/desktop' / name) for name in
                  ('DesktopWorkbench.exe', 'WorkbenchBridge.exe', 'UpdateWorkbench.exe')],
              'artifacts': [record(path) for path in (source, starter, updater)],
              'archive_checks': archive_checks,
              'publication_readiness': 'Separate final six-file and checksum gate required before upload',
              'native_windows_validation': 'Pending separate exact-byte Windows gate and capture review',
              'final_release': False}
    write_json(output / REPORT_NAME, report)
    (output / README_NAME).write_text(
        '# Native Workbench 0.7.0 reference candidate\n\n'
        'This is an immutable validation candidate, not the final application release.\n'
        'Native Windows validation and review of the References window captures are pending.\n\n'
        'The feature adds explicit Ensembl archive discovery, local reference downloads and offline reuse.\n'
        'The updater upgrades the exact published 0.6.0 application to 0.7.0 while preserving user data.\n'
        'It does not refer to the historical 0.5.4-to-0.6.0 update.\n\n'
        f'Source commit: `{commit}`. Candidate tag: `{args.release_tag}`.\n'
        'See reference-build-report.json for input, source and output hashes and source checks.\n'
        'No optional pack version or published candidate is replaced.\n', encoding='utf-8')
    exact_files(output, (*ARCHIVE_NAMES, REPORT_NAME, README_NAME))
    (output / CHECKSUM_NAME).write_text(''.join(
        sha(output / name) + '  ' + name + '\n' for name in sorted(ASSET_NAMES) if name != CHECKSUM_NAME),
        encoding='utf-8')
    write_json(evidence / 'publication-readiness.json', verify_release(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--release-tag', default='app-v0.7.0-rc2')
    parser.add_argument('--run-suite', type=Path)
    parser.add_argument('--suite-report', type=Path)
    parser.add_argument('--verify-release', type=Path)
    parser.add_argument('--verification-report', type=Path)
    parser.add_argument('selectors', nargs='*')
    args = parser.parse_args()
    if args.run_suite:
        return run_suite(args.run_suite, args.suite_report, args.selectors)
    if args.verify_release:
        try:
            result = verify_release(args.verify_release)
        except Exception as error:
            if args.verification_report:
                diagnostic(args.verification_report, args.verify_release, error)
            raise
        if args.verification_report:
            write_json(args.verification_report, result)
        print(json.dumps(result, indent=2))
        return 0
    if not all((args.inputs, args.output, args.work, args.source_commit)):
        parser.error('--inputs, --output, --work and --source-commit are required')
    new_work = not args.work.exists()
    try:
        build(args)
    except Exception as error:
        evidence = args.work.resolve() / 'evidence'
        if new_work and evidence.is_dir():
            diagnostic(evidence / 'publication-readiness.json', args.output.resolve(), error)
        raise
    return 0


if __name__ == '__main__':
    sys.exit(main())
