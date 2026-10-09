#!/usr/bin/env python3
"""Exact 0.16.1 native keyboard/layout and 0.16.0 updater regression gate.

Uses unchanged packaged candidate bytes and real Windows input. The existing
published deployment gate remains separate and unchanged. No policy changes.
"""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_update_090 import extract
from build_update_0160 import verify_inventory
from check_references_windows import PrivateHost, require, sha256, write_json
from check_update_090_windows import read_json, preserved_files, synthetic_reference
from check_update_0160_windows import local_reference_run
from check_workspace_ui_windows import NativeUI
from check_deployment_ui_windows import (Keyboard, capture, passed, failed,
    finalize_report, focus_observation, observe_close, tree_hashes,
    tree_difference, verify_extracted, verify_preserved, unique_button,
    validate_destinations, updater_scenario, utc)

BASELINE_SHA = 'f96e03e43cac92ba8ca9a0a3807eb671f9924d5e624cadbba94d1a5ca1309073'
TARGET_VERSION = '0.16.1'
LIMITS = [
    'Exact published 0.16.0 to candidate 0.16.1 update only.',
    'Synthetic local reference and saved-state fixtures, not clinical or realistic-workload acceptance.',
    'Observed hosted desktop sizes and DPI only; no high-DPI/transition, multiple-monitor or physical-trackpad acceptance.',
    'Representative PCs and institutional security/approval remain external checks.',
    'Scientific hosts deny Python socket operations, not OS-level network access.'
]


def validate_identities(args):
    for name in ('source_commit', 'gate_commit'):
        require(re.fullmatch('[0-9a-f]{40}', getattr(args, name)), 'Exact source/gate commit required.')
    for name in ('starter_sha256', 'update_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', getattr(args, name)), 'Exact candidate archive SHA-256 required.')
    require(args.starter_sha256 != BASELINE_SHA, 'Candidate must differ from the published baseline.')


def inside(inner, outer):
    return (outer[0] <= inner[0] < inner[2] <= outer[2] and
            outer[1] <= inner[1] < inner[3] <= outer[3])


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def pointer_click(ui, control):
    left, top, right, bottom = ui.bounds(control)
    ui.click_at((left + right) // 2, (top + bottom) // 2, expected=control)


class PatchUI(NativeUI):
    def fit_window(self, width, height):
        # NativeUI normally resizes immediately. Record real startup geometry
        # before any driver repositioning, so a driver cannot repair the defect.
        if not hasattr(self, 'initial_bounds'):
            self.initial_bounds = self.bounds(self.main)
            self.initial_work_area = self.work_area()
            return
        super().fit_window(width, height)


def seed_baseline(base, evidence, external):
    record = synthetic_reference(base, external)
    host = PrivateHost(base, evidence, 'baseline-fixtures', offline=True)
    try:
        require(host.call('init')['app_version'] == '0.16.0', 'Fixture host is not the exact published baseline.')
        run = local_reference_run(host, base, evidence, record, 'preserved-reference-result')
        run_id = host.call('history')['runs'][0]['run_id']
        state = host.call('workspace/tool', {'toolId': 'align/paired-end'})
        node = state['graph']['nodes'][0]
        state = host.call('model', {'action': 'apply_fields', 'payload': {
            'nodeId': node['id'], 'params': {'threads': '3'}}})
        node = state['graph']['nodes'][0]
        host.call('save', {'kind': 'preset', 'name': 'UI patch preservation settings', 'nodeId': node['id']})
        host.call('workspace/mode', {'mode': 'workflow'})
        first = host.call('model', {'action': 'add_tool', 'payload': {'toolId': 'bam/reference-index'}})['selected']
        second = host.call('model', {'action': 'add_tool', 'payload': {'toolId': 'bam/reference-index'}})['selected']
        source = host.call('model', {'action': 'add_input', 'payload': {'inputType': 'reference'}})['selected']
        host.call('model', {'action': 'connect', 'payload': {'nodeId': first, 'portId': 'reference', 'refs': [source]}})
        host.call('model', {'action': 'connect', 'payload': {'nodeId': second, 'portId': 'reference', 'refs': [first + '::reference']}})
        host.call('save', {'kind': 'pipeline', 'name': 'UI patch preservation pipeline'})
    finally:
        host.close()
    saved = read_json(base / 'user-data/saved.json')
    require(len(saved['presets']) == len(saved['pipelines']) == 1 and
            saved['presets'][0]['pin'] == node['pin'] and saved['presets'][0]['params']['threads'] == '3',
            'Separate nondefault settings and exact pipeline pins were not saved.')
    return {'reference': record, 'saved': saved, 'run': run, 'runId': run_id}



def seed_fresh_result(root, evidence, external, report):
    record = synthetic_reference(root, external)
    host = PrivateHost(root, evidence, 'fresh-result-fixture', offline=True)
    try:
        require(host.call('init')['app_version'] == TARGET_VERSION, 'Wrong fresh candidate version.')
        result = local_reference_run(host, root, evidence, record, 'fresh-search-reference-result')
        require(len(host.call('results/search', {'query': 'SAMtools'})['runs']) == 1,
                'Fresh search fixture must contain one actual completed SAMtools result.')
        report['freshResultFixture'] = result
    finally:
        host.close()
    passed(report, 'fresh-result-fixture', 'Candidate private host creates one real native SAMtools result for populated keyboard search.')


def fixed_layout(ui, mode):
    bounds, area = ui.bounds(ui.main), ui.work_area()
    require(inside(bounds, area), 'Native window clips outside the actual monitor work area.')
    identities = [102, 104, 402, 410, 411, 417, 424, 425, 114, 116, 415, 416]
    if mode == 'workflow':
        identities += [419, 105, 412, 107, 108, 418, 420, 421, 422]
    measured = []
    for identity in identities:
        handle = ui.child(identity)
        require(handle and ui.user.IsWindowVisible(handle), 'Missing fixed control: ' + str(identity))
        rect = ui.bounds(handle)
        require(inside(rect, bounds) and inside(rect, area), 'Fixed control clips: ' + str(identity))
        measured.append({'id': identity, 'class': ui.label(handle, True), 'bounds': rect})
    buttons = [row for row in measured if row['class'] == 'Button']
    for index, a in enumerate(buttons):
        for b in buttons[index + 1:]:
            require(not overlaps(a['bounds'], b['bounds']),
                    'Fixed buttons overlap: ' + str((a['id'], b['id'])))
    return {'windowBounds': bounds, 'workArea': area, 'controls': measured,
            'horizontalClipping': False, 'verticalClipping': False}


def desktop_scenarios(root, evidence, report, label):
    ui = PatchUI(root, evidence)
    keys = Keyboard(ui)
    try:
        require(inside(ui.initial_bounds, ui.initial_work_area), 'Unmodified startup window clips outside work area.')
        report.setdefault('startupBounds', {})[label] = {
            'windowBounds': ui.initial_bounds, 'workArea': ui.initial_work_area,
            'capturedBeforeDriverResize': True}
        passed(report, label + '-startup-bounds', label + ': real initial window fits the work area before driver repositioning.')
        ui.wait('desktop ready', lambda: ui.user.IsWindowEnabled(ui.child(410)) and ui.library().tools())
        setup_window = lambda: next((h for h in ui.windows() if ui.label(h) == 'Tool setup · Native Workbench'), None)
        if label == 'fresh':
            ui.wait('fresh native tool setup', setup_window)
        else:
            ui.wait('upgraded startup requests complete', lambda: ui.user.IsWindowEnabled(ui.child(417)))
        setup = setup_window()
        report.setdefault('startupSetup', {})[label] = {'observed': bool(setup)}
        if setup:
            pack_snapshot = tree_hashes(root / 'packs')
            starter = unique_button(ui, setup, 'Starter')
            pointer_click(ui, starter)
            ui.wait('Starter selected', lambda: ui.send(starter, 0x00F0) == 1)
            require(inside(ui.bounds(setup), ui.work_area()), 'First-open setup clips outside the work area.')
            capture(ui, report, label + '-first-open-starter.bmp', setup)
            pointer_click(ui, unique_button(ui, setup, 'Use Workbench'))
            state_path = root / 'user-data/tool-setup.json'
            ui.wait('setup dismissal recorded', lambda:
                    not setup_window() and state_path.is_file() and read_json(state_path)['dismissed'])
            state = read_json(state_path)
            require(not state['queue'] and not state['operation']['active'] and
                    state['operation']['status'] == 'idle' and tree_hashes(root / 'packs') == pack_snapshot,
                    'Offline Starter selection changed packs or queued work.')
            report['startupSetup'][label].update(starterSelected=True, dismissed=True,
                                                queuedInstalls=0, unchangedPackFiles=len(pack_snapshot))
            passed(report, label + '-starter-setup', label + ': real offline Starter setup fits and dismisses without pack changes or installs.')
        if label == 'fresh':
            # Any result/reference record marks an installation as an existing
            # user. Exercise pristine first-open setup before creating the
            # scientific search fixture, then reopen the same installation.
            ui.close()
            ui = None
            seed_fresh_result(root, evidence, evidence / 'fresh external reference', report)
            ui = PatchUI(root, evidence)
            keys = Keyboard(ui)
            require(inside(ui.initial_bounds, ui.initial_work_area), 'Reopened fresh window clips outside work area.')
            report['startupBounds'][label]['reopenedAfterFixture'] = ui.initial_bounds
        ui.wait('desktop unobscured', lambda: ui.user.IsWindowEnabled(ui.child(417)))
        search = ui.child(102)
        pointer_click(ui, search)
        ui.wait('library keyboard focus', lambda: keys.focus() == search)
        keys.key(0x41, 0x11)
        keys.text('reference')
        ui.wait('keyboard library filter', lambda: ui.label(search) == 'reference' and ui.library().tools())
        keys.key(0x09)
        ui.wait('Tab advances from library search', lambda: keys.focus() not in (None, search))
        next_focus = keys.focus()
        require(ui.user.IsChild(ui.main, next_focus) and ui.user.IsWindowVisible(next_focus) and
                ui.user.IsWindowEnabled(next_focus), 'Tab reached an unavailable or foreign control.')
        keys.key(0x09, 0x10)
        ui.wait('Shift+Tab restores search', lambda: keys.focus() == search)
        keys.key(0x41, 0x11)
        keys.key(0x08)
        ui.wait('keyboard filter cleared', lambda: not ui.label(search) and ui.library().tools())
        passed(report, label + '-library-keyboard', label + ': library filtering and Tab/Shift+Tab preserve real enabled focus.')
        layouts = []
        for mode, button in [('tool', 410), ('workflow', 411)]:
            ui.click_button(button)
            ui.wait(mode + ' controls ready', lambda: ui.user.IsWindowEnabled(ui.child(417)) and
                    (mode != 'workflow' or ui.user.IsWindowVisible(ui.child(420))))
            for width, height in [(960, 680), (1024, 728), (1280, 900)]:
                ui.fit_window(width, height)
                row = fixed_layout(ui, mode)
                row.update(mode=mode, requestedSize=[width, height])
                layouts.append(row)
                capture(ui, report, label + '-' + mode + '-%dx%d.bmp' % (width, height))
                if width == 960:
                    frame, _ = ui.screen_capture(label + '-' + mode + '-960-visible.bmp', ui.bounds(ui.main))
                    frame['dpi'] = ui.user.GetDpiForWindow(ui.main)
                    report['captures'].append(frame)
        report.setdefault('layouts', {})[label] = layouts
        passed(report, label + '-layout', label + ': both three-pane modes, navigation and fixed footer controls fit actual work-area bounds without button overlap at every observed size.')
        for case, query_text, expected_count in [('empty', 'patch-no-matching-result', 0), ('populated', 'SAMtools', 1)]:
            ui.click_button(417)
            title = 'Recorded results · Native Workbench'
            window = lambda: next((h for h in ui.windows() if ui.label(h) == title), None)
            ui.wait('Results opened', window)
            owner = window()
            query = ui.child(1501, owner)
            ui.wait('native initial Results query focus', lambda: keys.focus() == query and
                    ui.user.IsWindowEnabled(ui.child(1502, owner)))
            require(inside(ui.bounds(owner), ui.work_area()), 'Results dialog clips outside work area.')
            # No pointer/refocus/SetFocus intervention is allowed after opening.
            keys.key(0x41, 0x11)
            keys.text(query_text)
            ui.wait('query entered by keyboard', lambda: ui.label(query) == query_text)
            keys.key(0x09)
            ui.wait('Tab reaches Search', lambda: keys.focus() == ui.child(1502, owner))
            keys.key(0x09, 0x10)
            ui.wait('Shift+Tab restores query', lambda: keys.focus() == query)
            keys.key(0x09)
            ui.wait('Tab returns to Search', lambda: keys.focus() == ui.child(1502, owner))
            keys.key(0x20)
            ui.wait('keyboard Search returns with retained query focus', lambda:
                    keys.focus() == query and ui.user.IsWindowEnabled(ui.child(1502, owner)) and
                    ui.send(ui.child(1503, owner), 0x1004) == expected_count and
                    (('Execution status: completed' in ui.label(ui.child(1504, owner))) if expected_count else
                     ui.label(ui.child(1504, owner)) == 'No matching recorded analyses. Clear the search and press Search to show recent runs.'))
            require(bool(ui.user.IsWindowEnabled(ui.child(1505, owner))) == bool(expected_count),
                    'View availability differs from actual selected results.')
            observation = {'query': query_text, 'resultCount': expected_count,
                           'beforeEscape': focus_observation(ui, keys, owner),
                           'pointerInterventionAfterOpen': False}
            capture(ui, report, label + '-results-' + case + '.bmp', owner)
            report.setdefault('resultsKeyboard', {}).setdefault(label, {})[case] = observation
            keys.key(0x1B)
            observation['closedImmediatelyAfterSearch'] = observe_close(ui, window)
            observation['afterEscape'] = focus_observation(ui, keys, owner)
            require(observation['closedImmediatelyAfterSearch'], 'Escape after keyboard Search did not close Results.')
            passed(report, label + '-results-' + case, label + ': ' + case + ' Search retains query focus; immediate Escape closes only Results without pointer intervention.')
    except Exception:
        if ui is not None:
            for number, owner in enumerate(ui.windows()):
                capture(ui, report, label + '-failure-%d.bmp' % number, owner)
        raise
    finally:
        if ui is not None:
            ui.close()

def run(args, report):
    require(os.name == 'nt', 'Native Windows is unavailable; this gate cannot pass.')
    validate_identities(args)
    target, update_input, work, evidence = args.app_root.resolve(), args.update_root.resolve(), args.work.resolve(), args.report.resolve().parent
    require(Path(sys.executable).resolve() == (target / 'runtime/python/python.exe').resolve(), 'Use the exact Starter private interpreter.')
    require(not work.exists() and all(not work.is_relative_to(root) and not root.is_relative_to(work)
                                    for root in (target, update_input)), 'Use a new, separate disposable work directory.')
    for role, path, expected in [('starter', args.starter_archive, args.starter_sha256), ('baseline', args.baseline_archive, BASELINE_SHA), ('update', args.update_archive, args.update_sha256)]:
        require(sha256(path) == expected, 'Wrong exact ' + role + ' archive.')
        report['archives'][role] = {'name': path.name, 'bytes': path.stat().st_size, 'sha256': expected}
    report['archiveFilesVerified'] = {'starter': verify_extracted(args.starter_archive, target), 'update': verify_extracted(args.update_archive, update_input)}
    work.mkdir(parents=True)
    update = work / 'updater'
    shutil.copytree(update_input, update)
    updater_snapshot = tree_hashes(update_input)
    require(tree_hashes(update) == updater_snapshot, 'Disposable updater copy differs from verified bundle input.')
    extract(args.baseline_archive, work / 'baseline')
    base, external = work / 'baseline/native-workbench', work / 'external references'
    report['archiveFilesVerified']['baseline'] = verify_extracted(args.baseline_archive, base)
    pack_snapshots = {'fresh': tree_hashes(target / 'packs'), 'upgraded': tree_hashes(base / 'packs')}
    invalid = work / 'not a Workbench installation'
    invalid.mkdir()
    # Explicit bytes prevent Windows text-mode CRLF translation from making
    # the preservation oracle disagree with its own freshly created fixture.
    (invalid / 'keep.txt').write_bytes(b'Invalid folder must remain unchanged.\n')
    target_manifest = read_json(target / 'manifest.json')
    require(target_manifest['version'] == TARGET_VERSION and len(target_manifest['files']) == 87, 'Unexpected candidate target manifest.')
    verify_inventory(target, target_manifest['files'])
    verify_inventory(base, read_json(base / 'manifest.json')['files'])
    verify_inventory(update, read_json(update / 'update-inventory.json')['files'])
    report['updaterLauncherSha256'] = sha256(update / 'UpdateWorkbench.exe')
    passed(report, 'candidate-input-identities', 'Every extracted candidate Starter and updater file matches its exact archive; the packaged launcher is exercised unchanged.')
    fixtures = seed_baseline(base, evidence, external)
    report['nativeWindowsExecuted'] = True
    report['baselineFixtures'] = fixtures
    saved_bytes = (base / 'user-data/saved.json').read_bytes()
    preserved = preserved_files(base, external)
    write_json(evidence / 'picker-preservation-before.json', preserved)
    passed(report, 'baseline-fixtures', 'Published 0.16.0 executes a local native SAMtools reference result and saves independent settings plus connected pipeline pins.')
    baseline_snapshot = tree_hashes(base)
    external_snapshot = tree_hashes(external)
    invalid_snapshot = tree_hashes(invalid)
    report['unchangedScenarioEvidence'] = {}
    for scenario in ('cancel', 'invalid'):
        updater_scenario(update, evidence, report, scenario, base, invalid)
        differences = {name: tree_difference(before, tree_hashes(folder)) for name, folder, before in
                       [('installation', base, baseline_snapshot), ('externalReference', external, external_snapshot),
                        ('invalidSelection', invalid, invalid_snapshot)]}
        report['unchangedScenarioEvidence'][scenario] = differences
        require(not any(differences.values()),
                'Cancellation or invalid-folder handling changed fixture files: ' + json.dumps(differences))
        passed(report, 'updater-' + scenario, 'Packaged folder picker ' + ('cancels with Escape' if scenario == 'cancel' else 'rejects a real non-installation folder, explains the required files, reopens for retry and allows Escape') + ' with every baseline/reference/invalid-folder file unchanged.')
    updater_scenario(update, evidence, report, 'install', base, invalid)
    verify_inventory(base, target_manifest['files'])
    require((base / 'manifest.json').read_bytes() == (target / 'manifest.json').read_bytes(), 'Updated manifest differs from accepted Starter.')
    after = preserved_files(base, external)
    report['preservation'] = verify_preserved(preserved, after)
    write_json(evidence / 'picker-preservation-after.json', after)
    require((base / 'user-data/saved.json').read_bytes() == saved_bytes, 'Folder-picker update changed saved settings or pins.')
    transactions = list((base / 'updates').glob('core-*/update-result.json'))
    require(len(transactions) == 1, 'Expected one real committed updater transaction.')
    transaction = read_json(transactions[0])
    require(transaction['status'] == 'installed' and transaction['version'] == TARGET_VERSION and
            transaction['files_verified'] == 87 and transaction['packs_changed'] is False,
            'Packaged launcher did not finish a verified core update.')
    report['transaction'] = transaction
    report['coreFilesVerified'] = 87
    report['preservedFiles'] = len(preserved)
    passed(report, 'updater-install', 'Selecting the actual baseline through the published folder picker displays success, commits all 87 exact Starter core files, and preserves every recorded pack/user/result/reference file.')
    installed_snapshot = tree_hashes(base)
    updater_scenario(update, evidence, report, 'repeat', base, invalid)
    differences = {'installation': tree_difference(installed_snapshot, tree_hashes(base)),
                   'externalReference': tree_difference(external_snapshot, tree_hashes(external))}
    report['unchangedScenarioEvidence']['repeat'] = differences
    require(not any(differences.values()),
            'Repeating through the folder picker changed the installed state: ' + json.dumps(differences))
    passed(report, 'updater-repeat', 'Repeating the update through the same real picker displays success and leaves all installation/reference files and the single transaction unchanged.')
    host = PrivateHost(base, evidence, 'updated-fixture-readback', offline=True)
    try:
        require(host.call('init')['app_version'] == TARGET_VERSION, 'Updated host version differs.')
        saved = fixtures['saved']
        state = host.call('workspace/tool', {'toolId': saved['presets'][0]['tool']})
        host.call('load', {'kind': 'preset', 'id': saved['presets'][0]['id'], 'node_id': state['graph']['nodes'][0]['id']})
        loaded_preset = host.call('state')['graph']['nodes'][0]
        require(loaded_preset['pin'] == saved['presets'][0]['pin'] and loaded_preset['params']['threads'] == '3',
                'Saved nondefault settings or exact pin changed.')
        loaded = host.call('load', {'kind': 'pipeline', 'id': saved['pipelines'][0]['id']})['graph']
        original = saved['pipelines'][0]['graph']
        require(loaded['nodes'] == original['nodes'] and
                [(row['id'], row['type']) for row in loaded['sources']] ==
                [(row['id'], row['type']) for row in original['sources']], 'Saved connected pipeline or exact pins changed.')
        require(any(row['run_id'] == fixtures['runId'] for row in host.call('results/search', {'query': 'SAMtools'})['runs']), 'Updated host lost the actual baseline result.')
        require(any(row['id'] == fixtures['reference']['id'] and row['available'] and
                    row['receipt_sha256'] == fixtures['reference']['receipt_sha256']
                    for row in host.call('references/list')['local']), 'Updated host lost the preserved local reference.')
    finally:
        host.close()
    passed(report, 'upgraded-fixture-readback', 'Updated private host reloads the unchanged settings and connected pipeline, finds the actual baseline result, and resolves its preserved exact reference receipt offline.')
    for label, root in [('fresh', target), ('upgraded', base)]:
        try:
            desktop_scenarios(root, evidence, report, label)
        except Exception as error:
            failed(report, label + '-desktop-incomplete', str(error))
            report.setdefault('desktopErrors', {})[label] = traceback.format_exc()
    verify_inventory(target, target_manifest['files'])
    verify_inventory(base, target_manifest['files'])
    require(tree_hashes(target / 'packs') == pack_snapshots['fresh'] and
            tree_hashes(base / 'packs') == pack_snapshots['upgraded'], 'Native checks changed installed packs.')
    require(tree_hashes(update_input) == updater_snapshot, 'Immutable original updater input changed.')
    report['observedDpi'] = sorted({row['dpi'] for row in report['captures']})
    report['nativeWindowsExecuted'] = True
    report['nativeGUIObservationsCompleted'] = not report.get('desktopErrors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('app-root', 'baseline-archive', 'update-root', 'starter-archive', 'update-archive', 'work', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('source-commit', 'gate-commit', 'starter-sha256', 'update-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    args.bundle_root = None
    validate_identities(args)
    validate_destinations(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'kind': 'native-ui-patch', 'appVersion': TARGET_VERSION, 'baselineVersion': '0.16.0',
              'sourceCommit': args.source_commit, 'gateCommit': args.gate_commit, 'gateSha256': sha256(__file__),
              'platform': platform.platform(), 'startedUtc': utc(), 'archives': {}, 'checks': [],
              'scenarios': [], 'captures': [], 'skips': [], 'limits': list(LIMITS),
              'nativeWindowsExecuted': False, 'nativeGUILaunched': False, 'nativeGUIValidated': False,
              'nativeGUIObservationsCompleted': False, 'success': False}
    try:
        run(args, report)
    except Exception as error:
        report['failure'] = str(error)
        report['traceback'] = traceback.format_exc()
        report['scenarios'].append({'id': 'gate-completion', 'status': 'blocked' if os.name != 'nt' else 'failed',
                                    'observedAt': utc(), 'note': 'Native gate did not complete; retained diagnostics describe the failure.'})
    finally:
        report['finishedUtc'] = utc()
        finalize_report(report)
        write_json(args.report, report)
    print(json.dumps({'success': report['success'], 'passed': report['passed'], 'failed': report['failed'],
                      'report': str(args.report)}), flush=True)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
