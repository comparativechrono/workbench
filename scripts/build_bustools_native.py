#!/usr/bin/env python3
"""Build pinned bustools CLI with narrow COFF linkage portability edits and its bounded I/O adapter on x86-64.

This compiles the complete pinned upstream CMake CLI source list with static zlib. No system Python, CMake, shell or network is needed at analysis time.
Building/PE inspection alone does not establish native Windows execution.
"""
import argparse
import concurrent.futures
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_VERSION = '0.45.1'
VERSION = UPSTREAM_VERSION + '-workbench1'
SOURCE_COMMIT = 'd4d7a283dbe9d34d2106e9ba31e2566413be6a70'
SOURCE_NAME = 'bustools-0.45.1.tar.gz'
SOURCE_URL = 'https://codeload.github.com/BUStools/bustools/tar.gz/' + SOURCE_COMMIT
SOURCE_SHA256 = 'b014317ea4501c3314ac358eb074dbbe3a10ed6daec53587f17a897e670e40df'
ZLIB_NAME = 'zlib-1.3.2.tar.gz'
ZLIB_URL = 'https://zlib.net/fossils/zlib-1.3.2.tar.gz'
ZLIB_SHA256 = 'bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16'
SOURCES = {SOURCE_NAME: {'url': SOURCE_URL, 'sha256': SOURCE_SHA256}, ZLIB_NAME: {'url': ZLIB_URL, 'sha256': ZLIB_SHA256}}
TC_NAME = 'llvm-mingw-20260922-ucrt-ubuntu-22.04-x86_64'
WINDOWS_STACK_RESERVE = 8 * 1024 * 1024
WINDOWS_STACK_COMMIT = 64 * 1024


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def prepare(cache, fetch=False, upstream=False):
    cache.mkdir(parents=True, exist_ok=True)
    source = cache / ('source-pristine' if upstream else 'source-workbench')
    if source.exists():
        shutil.rmtree(source)
    source.mkdir()
    for name, pin in SOURCES.items():
        archive = cache / name
        if not archive.exists() and fetch:
            with urllib.request.urlopen(pin['url'], timeout=120) as response:
                archive.write_bytes(response.read())
        if not archive.is_file() or sha(archive) != pin['sha256']:
            raise ValueError('Missing/changed pinned source: ' + name + '; use --fetch')
        with tarfile.open(archive) as stream:
            for member in stream.getmembers():
                parts = Path(member.name).parts
                if not parts or Path(member.name).is_absolute() or '..' in parts or not (member.isfile() or member.isdir()):
                    raise ValueError('Unsafe source archive')
                if member.isfile():
                    relative = Path(*parts[1:])
                    destination = source / (relative if name == SOURCE_NAME else Path('zlib') / relative)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(stream.extractfile(member).read())
    patches = []
    if not upstream:
        changes = [
            ('src/Common.hpp', '#define BUSTOOLS_VERSION "0.45.1"', '#define BUSTOOLS_VERSION "' + VERSION + '"'),
            ('src/roaring.h', 'inline bool roaring_bitmap_contains(const roaring_bitmap_t *r, uint32_t val)', '/* Native Workbench, 2026-10-13: private inline linkage for COFF; body unchanged. */\nstatic inline bool roaring_bitmap_contains(const roaring_bitmap_t *r, uint32_t val)'),
            ('src/roaring.c', 'extern inline bool roaring_bitmap_contains(const roaring_bitmap_t *r,\n                                           uint32_t val);', '/* Native Workbench, 2026-10-13: header supplies private inline COFF linkage; function body unchanged. */')]
        for relative, old, new in changes:
            path = source / relative
            before = path.read_text()
            if before.count(old) != 1:
                raise ValueError('Pinned patch context differs: ' + relative)
            after = before.replace(old, new)
            path.write_text(after)
            patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + relative, tofile='b/' + relative))
        (cache / 'workbench1.patch').write_text(''.join(patches))
    return source


def source_files(source, linux):
    # Exact source glob used by upstream src/CMakeLists.txt, plus pinned zlib.
    zfiles = 'adler32 compress crc32 deflate gzclose gzlib gzread gzwrite infback inffast inflate inftrees trees uncompr zutil'.split()
    return sorted((source / 'src').glob('*.cpp')) + sorted((source / 'src').glob('*.c')) + [source / 'zlib' / (name + '.c') for name in zfiles]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / 'build/bustools-cache')
    parser.add_argument('--build', type=Path)
    parser.add_argument('--toolchain', type=Path, default=ROOT / 'build/toolchains' / TC_NAME)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--linux', action='store_true')
    parser.add_argument('--upstream', action='store_true', help='Pristine Linux CLI reference only')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--without-guard', action='store_true', help='Development science build; cannot prepare a pack')
    args = parser.parse_args()
    if args.upstream and not args.linux:
        parser.error('--upstream is the pristine Linux reference only')
    cache = args.cache.resolve()
    source = prepare(cache, args.fetch, args.upstream)
    target = 'reference-linux' if args.upstream else ('linux' if args.linux else 'windows')
    out = (args.build or ROOT / ('build/bustools-' + target)).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'tmp').mkdir(exist_ok=True)
    tc = args.toolchain.resolve()
    env = dict(os.environ, TMPDIR=str(out / 'tmp'))
    if args.linux:
        cc, cxx = shutil.which('gcc'), shutil.which('g++')
    else:
        suffix = '.exe' if os.name == 'nt' else ''
        cc, cxx = (str(tc / ('bin/x86_64-w64-mingw32-clang' + suffix)), str(tc / ('bin/x86_64-w64-mingw32-clang++' + suffix)))
        env['LD_LIBRARY_PATH'] = str(tc / 'lib')
        env['PATH'] = str(tc / 'bin') + os.pathsep + env.get('PATH', '')
    if not cc or not cxx:
        raise ValueError('GCC/G++ or the pinned LLVM/MinGW toolchain is required')
    version = UPSTREAM_VERSION if args.upstream else VERSION
    flags = ['-O2', '-march=x86-64', '-mtune=generic', '-mno-avx', '-mno-avx2', '-fno-fast-math', '-I' + str(source / 'src'), '-I' + str(source / 'zlib'), '-I' + str(source / 'dependencies/CppNumericalSolvers-v1/include'), '-I' + str(source / 'dependencies/eigen-3.3.7'), '-I' + str(source / 'dependencies/LBFGSpp-2020-03-06/include'), '-DNDEBUG', '-DEIGEN_DONT_VECTORIZE']
    commands = []

    def compile_one(path):
        obj = out / (path.stem + '.o')
        cmd = [cxx if path.suffix in ('.cpp', '.cc') else cc, *flags, '-std=c++11' if path.suffix in ('.cpp', '.cc') else '-std=gnu11', '-c', str(path), '-o', str(obj)]
        result = subprocess.run(cmd, cwd=out, env=env, text=True, capture_output=True)
        (out / (path.stem + '.compile.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Compile failed for ' + path.name + ':\n' + result.stderr)
        return obj, cmd

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        built = list(pool.map(compile_one, source_files(source, args.linux)))
    commands.extend(item[1] for item in built)
    suffix = '' if args.linux else '.exe'
    binary = out / ('bustools' + suffix)
    link = [] if args.linux else ['-static', '-Wl,--no-insert-timestamp', '-Xlinker', '--stack', '-Xlinker', str(WINDOWS_STACK_RESERVE) + ',' + str(WINDOWS_STACK_COMMIT)]
    cmd = [cxx, *[str(item[0]) for item in built], '-lm', '-pthread', *link, '-o', str(binary)]
    subprocess.run(cmd, cwd=out, env=env, check=True)
    commands.append(cmd)
    files = [binary]
    guard = ROOT / 'tools/bustools/guard.cpp'
    if not args.upstream and not args.without_guard:
        output = out / ('bustools-guard' + suffix)
        cmd = [cxx, '-O2', '-std=c++17', '-march=x86-64', '-mtune=generic', '-mno-avx', '-mno-avx2', '-Wall', '-Wextra', '-Werror', str(guard), *link, '-o', str(output)]
        subprocess.run(cmd, cwd=out, env=env, check=True)
        commands.append(cmd)
        files.append(output)
    record = {'schema': 1, 'tool': 'bustools', 'version': version, 'upstreamVersion': UPSTREAM_VERSION, 'sourceCommit': SOURCE_COMMIT, 'upstreamCommit': SOURCE_COMMIT, 'sources': SOURCES, 'platform': 'linux-x86_64' if args.linux else 'windows-x86_64', 'sortThreads': 1, 'openmp': False, 'cpuBaseline': 'baseline x86-64; no SSE4.1/AVX/AVX2 required', 'upstreamScientificAlgorithmsUnmodified': True, 'upstreamSourceUnmodified': args.upstream, 'patchSha256': None if args.upstream else sha(cache / 'workbench1.patch'), 'executionTestsPerformedByBuild': False, 'builderSha256': sha(Path(__file__)), 'compiler': subprocess.check_output([cc, '--version'], env=env, text=True).splitlines()[0], 'compilerSha256': sha(cc), 'commands': commands, 'files': {}, 'buildRoute': 'Direct compilation of complete pinned upstream CMake source glob and static zlib; upstream MinGW conditionals; version marker and private Roaring inline COFF linkage only'}
    if len(files) == 2:
        record.update(guardSourceSha256=sha(guard), guardCompiler=subprocess.check_output([cxx, '--version'], env=env, text=True).splitlines()[0], guardCompilerSha256=sha(cxx))
    for file in files:
        info = {'bytes': file.stat().st_size, 'sha256': sha(file)}
        if not args.linux:
            pe = file.read_bytes()
            pe_offset = struct.unpack_from('<I', pe, 60)[0]
            optional_offset = pe_offset + 24
            if pe[:2] != b'MZ' or pe[pe_offset:pe_offset + 4] != b'PE\0\0' or struct.unpack_from('<H', pe, optional_offset)[0] != 0x20b:
                raise ValueError('Expected PE32+ executable')
            reserve, commit = struct.unpack_from('<QQ', pe, optional_offset + 72)
            if (reserve, commit) != (WINDOWS_STACK_RESERVE, WINDOWS_STACK_COMMIT):
                raise ValueError('Unexpected native stack configuration')
            info.update(stackReserveBytes=reserve, stackCommitBytes=commit)
            inspect = tc / ('bin/llvm-readobj' + ('.exe' if os.name == 'nt' else ''))
            data = subprocess.check_output([str(inspect), '--coff-imports', str(file)], env=env, text=True)
            (out / (file.stem + '.imports.txt')).write_text(data)
            imports = re.findall(r'^\s*Name:\s*(\S+)\s*$', data, re.M)
            if not imports or any(name.lower() not in {'kernel32.dll', 'msvcrt.dll', 'ucrtbase.dll', 'advapi32.dll', 'user32.dll'} and not name.lower().startswith('api-ms-win-crt-') for name in imports):
                raise ValueError('Unexpected Windows runtime dependency: ' + repr(imports))
            info['imports'] = sorted(imports)
        record['files'][file.name] = info
    notices = out / 'compiler-notices'
    notices.mkdir(exist_ok=True)
    if not args.linux:
        candidates = [tc / 'LICENSE.TXT', *sorted((tc / 'x86_64-w64-mingw32/share/mingw32').glob('COPYING*'))]
        if not all(path.is_file() for path in candidates) or len(candidates) < 2:
            raise ValueError('Pinned compiler/runtime licensing notices missing')
        for path in candidates:
            shutil.copyfile(path, notices / path.name)
        record['toolchainFiles'] = {str(path.relative_to(tc)): sha(path) for path in (tc / 'bin/clang', tc / 'bin/lld', tc / 'LICENSE.TXT') if path.is_file()}
    record['compilerNotices'] = {path.name: sha(path) for path in sorted(notices.iterdir()) if path.is_file()}
    (out / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'build': str(out), 'files': record['files']}, indent=2))


if __name__ == '__main__':
    main()
