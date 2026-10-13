#!/usr/bin/env python3
"""Read-only audit of downloaded bustools/StringTie packs against an exact Git commit.

This verifies bytes and corresponding source, not native execution or publisher
trust. Run it on the downloaded Actions candidate, not a local preparation tree.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
import tempfile
import types
import zipfile

from validate_pack_release import inspect_release

ROOT = Path(__file__).resolve().parents[1]



def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def members(archive):
    names = archive.namelist()
    require(len(names) == len({name.casefold() for name in names}), 'Duplicate ZIP members')
    for name in names:
        path = PurePosixPath(name)
        require(name and not path.is_absolute() and '\\' not in name and ':' not in name
                and all(part not in ('', '.', '..') for part in name.split('/')),
                'Unsafe ZIP member: ' + name)
    require(archive.testzip() is None, 'ZIP CRC failed')
    return set(names)


def verify_file(root, record):
    name = record['file']
    require(Path(name).name == name, 'Artifact must be an immediate filename')
    path = root / name
    require(path.is_file() and not path.is_symlink(), 'Missing regular artifact: ' + name)
    require(path.stat().st_size == record['bytes'] and file_hash(path) == record['sha256'],
            'Artifact identity mismatch: ' + name)
    return path


def git_files(commit):
    require(re.fullmatch(r'[a-f0-9]{40}', commit), 'Expected full Git commit')
    data = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=ROOT)
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            if member.isdir():
                continue
            require(member.isfile(), 'Unexpected nonregular Git source: ' + member.name)
            result[member.name] = archive.extractfile(member).read()
    return result


def pe_x64(data):
    require(len(data) > 64 and data[:2] == b'MZ', 'Tool is not a PE executable')
    offset = struct.unpack_from('<I', data, 60)[0]
    require(offset + 6 <= len(data) and data[offset:offset + 4] == b'PE\0\0'
            and struct.unpack_from('<H', data, offset + 4)[0] == 0x8664,
            'Tool is not a Windows x86-64 PE')


UPSTREAM_PINS = {
    'bustools': {'bustools-0.45.1.tar.gz': 'b014317ea4501c3314ac358eb074dbbe3a10ed6daec53587f17a897e670e40df',
                'zlib-1.3.2.tar.gz': 'bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16'},
    'stringtie': {'stringtie-3.0.3.tar.gz': '52a5d94b0e85404d740d2c7a0c7cc698d373a1b8888e9a2a395ae294032d95c0',
                 'zlib-1.3.2.tar.gz': 'bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16',
                 'tre-0.9.0.tar.gz': '5b7e5a730f041c6b0dab8f66576cda917577ec06bb393f156b169c51bca170d1'},
}
UPSTREAM_IDENTITIES = {
    'bustools': ('0.45.1', 'd4d7a283dbe9d34d2106e9ba31e2566413be6a70'),
    'stringtie': ('3.0.3', '3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19'),
}
# Review the exact changed source boundary and all compiled component notices.
PATCH_PATHS = {'bustools': {'src/Common.hpp', 'src/roaring.h', 'src/roaring.c'},
               'stringtie': {'gclib/GBase.cpp', 'stringtie.cpp'}}
PATCH_SHA256 = {'bustools': '889fea401c52db2b748c1d5645dc63ccae8844c74cbdfef0af153d1580d261f4',
                'stringtie': '253fb7891604783bbe87e60947435dd68f447d7cb6449d9f074b5969441b2d42'}
NOTICE_PATHS = {
    'bustools': {
        'bustools-0.45.1.tar.gz': {
            'bustools-d4d7a283dbe9d34d2106e9ba31e2566413be6a70/LICENSE': 'bustools-BSD2.txt',
            'bustools-d4d7a283dbe9d34d2106e9ba31e2566413be6a70/dependencies/LBFGSpp-2020-03-06/LICENSE.md': 'LBFGSpp-MIT.txt',
            'bustools-d4d7a283dbe9d34d2106e9ba31e2566413be6a70/dependencies/CppNumericalSolvers-v1/LICENSE': 'CppNumericalSolvers-MIT.txt',
            **{'bustools-d4d7a283dbe9d34d2106e9ba31e2566413be6a70/dependencies/eigen-3.3.7/' + name: 'Eigen-' + name
               for name in ('COPYING.README', 'COPYING.MPL2', 'COPYING.BSD', 'COPYING.GPL', 'COPYING.LGPL', 'COPYING.MINPACK')},
        },
        'zlib-1.3.2.tar.gz': {'zlib-1.3.2/LICENSE': 'zlib-LICENSE.txt'},
    },
    'stringtie': {
        'stringtie-3.0.3.tar.gz': {
            'stringtie-3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19/LICENSE': 'StringTie-MIT.txt',
            'stringtie-3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19/htslib/htscodecs/LICENSE.md': 'HTSCodecs-LICENSE.md',
            'stringtie-3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19/htslib/Makefile': 'HTSlib-source-notice.txt',
            'stringtie-3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19/gclib/GThreads.cpp': 'GThreads-source-notice.cpp',
        },
        'zlib-1.3.2.tar.gz': {'zlib-1.3.2/LICENSE': 'zlib-LICENSE.txt'},
        'tre-0.9.0.tar.gz': {'tre-0.9.0/LICENSE': 'TRE-LICENSE.txt'},
    },
}
EXTERNAL_NOTICE_PINS = {'tools/bustools/CRoaring-LICENSE': '5b223235c64f595576d15ba2d983ef14f8e9e3ec45aafcad689dc40008e1b29e'}


STRINGTIE_CONFIGURATION = {
    'config/config.h': b'#define HAVE_WINDOWS_H 1\n#define HAVE_IO_H 1\n#define HAVE_FSEEKO 1\n#define HAVE_FTELLO 1\n#define HAVE_GMTIME_R 1\n#define HAVE_DECL___CPUID_COUNT 1\n#define HAVE_DECL___GET_CPUID_MAX 1\n',
    'config/version.h': b'#define HTS_VERSION_TEXT "1.21-stringtie-bundled"\n#define HTSCODECS_VERSION_TEXT "1.4.0-stringtie-bundled"\n',
    'config/config_vars.h': b'#define HTS_CC "source-bound-build"\n#define HTS_CPPFLAGS ""\n#define HTS_CFLAGS "baseline x86-64"\n#define HTS_LDFLAGS ""\n#define HTS_LIBS "zlib; no remote plugins"\n',
    'config/regex.h': b'#include "tre.h"\n#define regcomp tre_regcomp\n#define regexec tre_regexec\n#define regerror tre_regerror\n#define regfree tre_regfree\n',
}


def stringtie_configuration(pack, build):
    expected = dict(STRINGTIE_CONFIGURATION)
    with tarfile.open(fileobj=io.BytesIO(pack.read('pack/licenses/tre-0.9.0.tar.gz'))) as source:
        for name in ('config.h', 'tre-config.h'):
            expected['tre-config/' + name] = source.extractfile('tre-0.9.0/win32/' + name).read()
    prefix = 'pack/licenses/configuration/'
    require(set(build['generatedConfiguration']) == set(expected) and
            {name.removeprefix(prefix) for name in pack.namelist() if name.startswith(prefix)} == set(expected),
            'Generated native configuration file set differs')
    for name, data in expected.items():
        require(pack.read(prefix + name) == data and build['generatedConfiguration'][name] == digest(data),
                'Generated native configuration differs: ' + name)
    return len(expected)


def expected_generated_fixtures(identity, originals):
    """Regenerate synthetic bytes only from the exact committed pure factory."""
    name = 'tools/' + identity + '/fixtures.py'
    module = types.ModuleType('audited_' + identity + '_fixtures')
    module.__file__ = str(ROOT / name)
    exec(compile(originals[name], name, 'exec'), module.__dict__)
    with tempfile.TemporaryDirectory(prefix=identity + '-source-audit-') as directory:
        factory = module.build_fixture if identity == 'bustools' else module.fixtures
        factory(Path(directory))
        return {path.relative_to(directory).as_posix(): path.read_bytes()
                for path in Path(directory).rglob('*') if path.is_file()}


def fixture_correspondence(identity, pack, originals):
    fixtures = expected_generated_fixtures(identity, originals)
    prefix = 'tools/' + identity + '/fixtures/'
    for name, data in originals.items():
        if name.startswith(prefix):
            require(fixtures[name.removeprefix(prefix)] == data, 'Committed text fixture differs from committed factory: ' + name)
    require({name.removeprefix('pack/fixtures/') for name in pack.namelist() if name.startswith('pack/fixtures/')} == set(fixtures),
            'Fixture file sets differ')
    for name, data in fixtures.items():
        # The BAM factory uses stored DEFLATE blocks, so even the complete BGZF
        # bytes are deterministic across Python/zlib versions.
        require(pack.read('pack/fixtures/' + name) == data, 'Fixture differs from Git factory: ' + name)
    return len(fixtures)


def source_correspondence(identity, pack, originals):
    """Bind native bytes, recipes, compatibility changes and upstream notices."""
    require(identity in UPSTREAM_PINS and UPSTREAM_PINS[identity], 'Upstream pins not established')
    paths = {
        'pack/licenses/guard.cpp': 'tools/' + identity + '/guard.cpp',
        'pack/licenses/fixtures.py': 'tools/' + identity + '/fixtures.py',
        'pack/licenses/build_' + identity + '_native.py': 'scripts/build_' + identity + '_native.py',
        'pack/licenses/prepare_' + identity + '_pack.py': 'scripts/prepare_' + identity + '_pack.py',
        'pack/PACK-README.md': 'docs/' + identity.upper() + '-PACK.md',
        'pack/licenses/Workbench-LICENSE.txt': 'LICENSE',
    }
    for name in ('record_reference.py', 'upstream_windows_compat.h', 'workbench1.patch'):
        original = 'tools/' + identity + '/' + name
        if original in originals:
            paths['pack/licenses/' + name] = original
    for original, checksum in EXTERNAL_NOTICE_PINS.items():
        if original.startswith('tools/' + identity + '/'):
            paths['pack/licenses/' + original.rsplit('/', 1)[1]] = original
            require(digest(originals[original]) == checksum, 'Pinned external component notice differs: ' + original)
    for retained, original in paths.items():
        require(pack.read(retained) == originals[original], 'Pack retained source differs from Git: ' + original)
    build = json.loads(pack.read('pack/licenses/build-provenance.json'))
    require(build['platform'] == 'windows-x86_64' and build['executionTestsPerformedByBuild'] is False,
            'Unexpected binary build platform or execution claim')
    require(build['upstreamScientificAlgorithmsUnmodified'] is True, 'Scientific source modification not reviewed')
    if identity == 'bustools':
        require(build['sortThreads'] == 1 and build['openmp'] is False, 'Unexpected bustools execution scope')
    else:
        require(build['threadsExposed'] == 1, 'Unexpected StringTie processing thread scope')
    version, commit = UPSTREAM_IDENTITIES[identity]
    require(build['version'] == version + ('-workbench1' if identity in PATCH_PATHS else '') and build['upstreamVersion'] == version and
            build['sourceCommit'] == commit and build['upstreamCommit'] == commit and
            build['upstreamSourceUnmodified'] is (identity not in PATCH_PATHS), 'Unexpected upstream identity or modification')
    require(build['builderSha256'] == digest(originals['scripts/build_' + identity + '_native.py']),
            'Compiled recipe provenance differs from committed source')
    require(build['guardSourceSha256'] == digest(originals['tools/' + identity + '/guard.cpp']),
            'Compiled guard provenance differs from committed source')
    if identity in PATCH_PATHS:
        patch = pack.read('pack/licenses/workbench1.patch')
        require(build['patchSha256'] == digest(patch), 'Build compatibility patch identity differs')
        require(digest(patch) == PATCH_SHA256[identity], 'Pinned compatibility patch changed')
        old_paths = re.findall(rb'^--- a/(.+)$', patch, re.M)
        new_paths = re.findall(rb'^\+\+\+ b/(.+)$', patch, re.M)
        require(PATCH_PATHS[identity] and set(old_paths) == set(new_paths) ==
                {name.encode() for name in PATCH_PATHS[identity]}, 'Unreviewed compatibility patch paths')
    else:
        require(not build.get('patchSha256') and 'pack/licenses/workbench1.patch' not in pack.namelist(),
                'Unreviewed compatibility patch for unmodified upstream')
    if 'windowsCompatibilityHeaderSha256' in build:
        require(build['windowsCompatibilityHeaderSha256'] ==
                digest(originals['tools/' + identity + '/upstream_windows_compat.h']),
                'Compiled compatibility header differs from Git')
    require(set(build['files']) == {identity + '.exe', identity + '-guard.exe'}, 'Unexpected build binary set')
    for name, record in build['files'].items():
        data = pack.read('pack/bin/' + name)
        require(len(data) == record['bytes'] and digest(data) == record['sha256'], 'Pack executable differs from build: ' + name)
        pe_x64(data)
        optional = struct.unpack_from('<I', data, 60)[0] + 24
        require(struct.unpack_from('<H', data, optional)[0] == 0x20b and
                struct.unpack_from('<QQ', data, optional + 72) == (8388608, 65536),
                'Unexpected PE stack reserve/commit: ' + name)
    for name, checksum in UPSTREAM_PINS[identity].items():
        require(digest(pack.read('pack/licenses/' + name)) == checksum and build['sources'][name]['sha256'] == checksum,
                'Pinned corresponding source changed: ' + name)
    require(set(build['sources']) == set(UPSTREAM_PINS[identity]), 'Unreviewed upstream dependency')
    require(build['compilerNotices'], 'Compiler/runtime notices missing')
    for name, checksum in build['compilerNotices'].items():
        require(digest(pack.read('pack/licenses/compiler-' + name)) == checksum, 'Compiler/runtime notice differs')
    require(NOTICE_PATHS[identity], 'Upstream component notices not established')
    notice_count = 0
    for source_name, mappings in NOTICE_PATHS[identity].items():
        with tarfile.open(fileobj=io.BytesIO(pack.read('pack/licenses/' + source_name))) as source:
            for original, retained in mappings.items():
                require(pack.read('pack/licenses/' + retained) == source.extractfile(original).read(),
                        'Upstream component notice differs: ' + retained)
                notice_count += 1
    configuration_count = stringtie_configuration(pack, build) if identity == 'stringtie' else 0
    fixture_count = fixture_correspondence(identity, pack, originals)
    return {'retainedRecipeFilesMatchedToGit': len(paths), 'guardSourceBoundToBuild': True,
            'builderSourceBoundToBuild': True, 'compatibilityPatchBoundToBuild': identity in PATCH_PATHS,
            'binaryHashesMatchedToBuild': len(build['files']), 'upstreamSourceHashesVerified': UPSTREAM_PINS[identity],
            'fixturesMatchedToGitFactory': fixture_count, 'generatedFixturesExactBytesVerified': True,
            'upstreamEmbeddedNoticesVerified': notice_count,
            'generatedConfigurationFilesVerified': configuration_count,
            'scope': 'Byte and provenance correspondence; not independent bit-identical recompilation.'}


def audit(candidate, commit):
    record = json.loads((candidate / 'BUILD-PROVENANCE.json').read_text(encoding='utf-8'))
    require(record['sourceCommit'] == commit, 'Build record refers to another commit')
    tree = subprocess.check_output(['git', 'rev-parse', commit + '^{tree}'], cwd=ROOT, text=True).strip()
    require(record['sourceTree'] == tree, 'Build tree differs from Git')
    require(record['published'] is False and record['nativeWindowsExecuted'] is False,
            'Freeze must remain unpublished build-time evidence')
    require(set(record['packs']) == {'bustools', 'stringtie'}, 'Unexpected pack set')
    companion = verify_file(candidate, record['sourceCompanion'])
    originals = git_files(commit)
    result = {'schema': 1, 'kind': 'downloaded-pack-source-audit', 'sourceCommit': commit,
              'sourceTree': tree, 'nativeWindowsExecuted': False, 'published': False,
              'success': False, 'packs': {}, 'sourceCompanion': record['sourceCompanion']}
    with zipfile.ZipFile(companion) as source:
        names = members(source)
        inventory = json.loads(source.read('SOURCE-INVENTORY.json'))
        require(inventory['sourceCommit'] == commit and inventory['schema'] == 1,
                'Source inventory identity differs')
        indexed = {item['path']: item for item in inventory['files']}
        require(len(indexed) == len(inventory['files']), 'Duplicate source inventory entries')
        require(names == set(indexed) | {'SOURCE-INVENTORY.json', 'BUILD-PROVENANCE.json'},
                'Source companion contains missing or undeclared files')
        for name, item in indexed.items():
            data = source.read(name)
            require(len(data) == item['bytes'] and digest(data) == item['sha256'],
                    'Source inventory mismatch: ' + name)
        embedded = json.loads(source.read('BUILD-PROVENANCE.json'))
        require(embedded == {key: value for key, value in record.items() if key != 'sourceCompanion'},
                'Embedded and external build records differ')
        require({name[7:] for name in names if name.startswith('source/')} == set(originals),
                'Git and companion source file sets differ')
        for name, data in originals.items():
            require(source.read('source/' + name) == data, 'Source differs from committed Git bytes: ' + name)
        result['gitSourceFilesVerified'] = len(originals)
        result['companionInventoryFilesVerified'] = len(indexed)
        for identity, pack_record in record['packs'].items():
            pack_path = verify_file(candidate, pack_record)
            inspected = inspect_release(pack_path)
            require(inspected == pack_record['staticValidation'], 'Static pack audit differs')
            require((inspected['id'], inspected['version']) == (identity, '1.0.0'), 'Wrong pack identity')
            with zipfile.ZipFile(pack_path) as pack:
                pack_names = members(pack)
                licence_names = {name for name in pack_names if name.startswith('pack/licenses/')}
                prefix = 'corresponding-sources/' + identity + '/'
                require({prefix + name[len('pack/licenses/'):] for name in licence_names}
                        == {name for name in names if name.startswith(prefix)},
                        'Pack and companion corresponding-source inventories differ')
                for name in licence_names:
                    require(pack.read(name) == source.read(prefix + name[len('pack/licenses/'):]),
                            'Corresponding source differs from pack: ' + name)
                executables = [name for name in pack_names if name.startswith('pack/bin/') and name.endswith('.exe')]
                require(len(executables) == 2, 'Expected upstream tool and native guard')
                for name in executables:
                    pe_x64(pack.read(name))
                correspondence = source_correspondence(identity, pack, originals)
                result['packs'][identity] = {**pack_record, 'licenceSourceFilesMatched': len(licence_names),
                                             'x64ExecutablesVerified': executables,
                                             'sourceCorrespondence': correspondence}
    expected_sums = {item['file']: item['sha256'] for item in [*record['packs'].values(), record['sourceCompanion']]}
    lines = (candidate / 'SHA256SUMS.txt').read_text(encoding='ascii').splitlines()
    pairs = [line.split('  ', 1) for line in lines]
    require(len(pairs) == len(expected_sums) and all(len(pair) == 2 for pair in pairs)
            and {name: checksum for checksum, name in pairs} == expected_sums,
            'Checksum manifest differs from frozen artifacts')
    result['success'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.candidate.resolve(), args.source_commit)
    except Exception as exc:
        result = {'schema': 1, 'success': False, 'sourceCommit': args.source_commit, 'error': str(exc),
                  'nativeWindowsExecuted': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'success': result['success'], 'report': str(args.report)}))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
