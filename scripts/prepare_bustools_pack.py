#!/usr/bin/env python3
"""Prepare independent bustools 1.0.0 from exact native outputs and matching sources."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tarfile

from build_bustools_native import ROOT, VERSION as TOOL_VERSION, SOURCE_COMMIT, SOURCE_NAME, SOURCES, sha
sys.path.insert(0, str(ROOT / 'desktop'))
from prepare_modular_packs import artifact, execute, field, workflow
VERSION = '1.0.0'
CITATION = {'text': 'Melsted P, Ntranos V, Pachter L (2019). The barcode, UMI, set format and BUStools. Bioinformatics 35:4472-4473.', 'url': 'https://doi.org/10.1093/bioinformatics/btz279'}
CROARING_LICENSE_URL = 'https://github.com/RoaringBitmap/CRoaring/blob/86de9b526c05cbd59deedc101c4f3aee99ddd905/LICENSE'
CROARING_LICENSE_SHA256 = '5b223235c64f595576d15ba2d983ef14f8e9e3ec45aafcad689dc40008e1b29e'
INPUTS = ['bus', 'transcripts', 'equivalence-classes', 'genes', 'allowlist']


def definitions():
    inputs = [
        field('bus', 'Uncompressed kallisto BUS file', filter='Uncompressed BUS|*.bus|All files|*.*', help='Select output.bus from one kallisto bus run, with that same run\'s matrix.ec and transcript order below. The existing kallisto bulk pack does not generate BUS. BUS v1 only; at most 2000000 records / 64 MiB, barcode length 1–16, UMI length 1–31, no flags, padding or pooled/split metadata. ASCII paths required; spaces supported. Single sort thread and 64 MiB sort buffer; this is not a process memory cap or time prediction.'),
        field('transcripts', 'Matching transcript order', filter='Transcript list|*.txt|All files|*.*', help='Select transcripts.txt from the same kallisto bus run/index, in its original order. Unique IDs, one per line; at most 250000. Structural checks cannot establish that separately selected files have the same biological origin.'),
        field('equivalence-classes', 'Matching equivalence classes', filter='Equivalence classes|*.ec|All files|*.*', help='Select matrix.ec from that exact BUS run. Consecutive zero-based EC IDs and sorted unique transcript indices; at most 500000 classes / 5000000 memberships. Do not substitute an EC map from another sample or index.'),
        field('genes', 'Complete transcript-to-gene mapping', filter='Transcript-to-gene table|*.tsv;*.txt|All files|*.*', help='Reviewed mapping from the same annotation used to build the kallisto index: two tab-separated columns (transcript ID, gene ID), optionally a third gene-name column which is ignored. Every listed transcript must map once. IDs: 1–128 ASCII letters, digits, dots, underscores or hyphens.'),
        field('allowlist', 'Assay barcode allowlist', filter='Barcode allowlist|*.txt|All files|*.*', help='Reviewed assay/chemistry allowlist, not inferred cell calls. Plain uppercase A/C/G/T sequences, one per line, matching BUS barcode length; at most 4000000 unique barcodes / 128 MiB. Compressed lists or sample suffixes such as -1 are rejected; obtain the assay\'s original sequence-only allowlist. Exact matches are kept, uniquely correctable Hamming-distance-1 barcodes corrected; ambiguous/unmatched barcodes discarded.')]
    outputs = [artifact('matrix', 'Barcode-by-gene UMI count matrix', 'counts.mtx'),
               artifact('gene-labels', 'Matrix gene column labels', 'counts.genes.txt'),
               artifact('barcode-labels', 'Matrix barcode row labels (not called cells)', 'counts.barcodes.txt', nonempty=False),
               artifact('corrected-bus', 'Barcode-corrected BUS', 'corrected.bus', final=False),
               artifact('sorted-bus', 'Sorted corrected BUS', 'sorted.bus', final=False),
               artifact('summary', 'Recorded BUS count measurements', 'summary.json'),
               artifact('settings', 'Analysis settings and commands', 'settings.json'),
               artifact('adapter-log', 'Execution guidance', 'adapter.log'),
               artifact('correct-log', 'Barcode correction log', 'correct.log'),
               artifact('sort-log', 'BUS sorting log', 'sort.log'),
               artifact('count-log', 'Gene counting log', 'count.log', nonempty=False)]
    steps = [execute('version', 'Record bundled bustools version', 'bustools', ['version']),
             execute('count', 'Correct barcodes, sort BUS and count exact UMIs', 'bustools-adapter', ['{input:' + k + '}' for k in INPUTS] + ['{run}'], produces=[o['id'] for o in outputs])]
    workflows = [workflow('count-bus', 'bustools: count a matched BUS bundle', 'Correct reviewed assay barcodes, sort BUS records and produce a barcode-by-gene matrix of unambiguous exact-UMI counts. No cell calling or QC pass thresholds.', inputs, outputs, steps)]
    schema = {'schema': 1, 'category': 'RNA-seq', 'citations': [CITATION], 'workflows': {'count-bus': {
        'ports': [{'id': 'bundle', 'label': 'Matched kallisto BUS and annotation/assay bundle', 'type': 'file', 'manifestInputs': INPUTS, 'min': 1, 'max': 1}],
        'outputs': [{'id': o['id'], 'label': o['label'], 'type': 'file' if o['id'].endswith('-bus') else ('text' if o['id'].endswith('-log') else 'metrics'), 'manifestOutputs': [o['id']]} for o in outputs],
        'pathPolicy': {'asciiOnly': True},
        'methods': 'bustools 0.45.1-workbench1 (upstream 0.45.1 with native COFF linkage/version-marker edits only) processed a user-reviewed coherent kallisto BUS v1 bundle. The same run/index transcript order and equivalence-class mapping, complete annotation transcript-to-gene map and assay barcode allowlist were required; structural validation does not prove common biological origin. bustools correct retained exact allowlist matches and uniquely corrected Hamming-distance-1 barcodes, discarding ambiguous/unmatched barcodes. bustools sort used one thread and a 64 MiB sort buffer (not a whole-process memory limit). bustools count --genecounts grouped identical barcode-plus-UMI values, intersected gene sets across their equivalence classes and counted a molecule only when the intersection contained exactly one gene. Multigene ambiguity and disjoint-gene UMI collisions were excluded; --umi-gene collision rescue, UMI edit-distance correction, multiplicity counting and fractional multimapping were not requested. For zero retained records the adapter preserves the exact BUS header omitted by upstream sort, adding no records. Matrix rows are retained barcodes, including zero-count rows, and columns are genes. Read multiplicities and molecule counts are distinct recorded measurements. A zero matrix is a valid result requiring review of assay/mapping associations; it is not a QC pass or evidence of no expression. No cell calling, normalization, differential expression or clinical inference was performed. The pack does not generate BUS from FASTQ.'}}}
    return workflows, schema


def checks():
    return {'schema': 1, 'checks': [{'id': 'independent-bus-truth', 'workflow': 'count-bus',
       'inputs': {'bundle': [{k: 'fixture-' + k for k in INPUTS}]}, 'params': {},
       'expect': [{'output': 'summary', 'kind': 'text', 'contains': ['"inputRecords": 14', '"inputReadMultiplicity": 24', '"retainedRecords": 12', '"retainedReadMultiplicity": 19', '"countedMolecules": 5', '"barcodes": 3', '"nonzeroEntries": 3', '"cellCallingPerformed": false']},
                  {'output': 'matrix', 'kind': 'text', 'contains': ['3 3 3', '1 1 3', '2 2 1', '2 3 1']},
                  {'output': 'barcode-labels', 'kind': 'text', 'contains': ['AAAA', 'CCCC', 'TTTT']},
                  {'output': 'settings', 'kind': 'text', 'contains': ['"umiErrorCorrection": false', '"sortBufferIsProcessMemoryCap": false']}]}]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, default=ROOT / 'build/bustools-cache')
    p.add_argument('--build', type=Path, default=ROOT / 'build/bustools-windows')
    p.add_argument('--destination', type=Path, default=ROOT / 'packs/bustools-1.0.0')
    a = p.parse_args()
    cache, build, destination = a.cache.resolve(), a.build.resolve(), a.destination.resolve()
    record = json.loads((build / 'build.json').read_text())
    for key, expected in {'platform': 'windows-x86_64', 'version': TOOL_VERSION, 'upstreamCommit': SOURCE_COMMIT,
                         'builderSha256': sha(ROOT / 'scripts/build_bustools_native.py'), 'guardSourceSha256': sha(ROOT / 'tools/bustools/guard.cpp'),
                         'upstreamScientificAlgorithmsUnmodified': True, 'upstreamSourceUnmodified': False,
                         'patchSha256': sha(cache / 'workbench1.patch'), 'sources': SOURCES}.items():
        if record.get(key) != expected:
            raise ValueError('Build/source correspondence failed: ' + key)
    for name, source in SOURCES.items():
        if sha(cache / name) != source['sha256']:
            raise ValueError('Changed source archive: ' + name)
    if sha(ROOT / 'tools/bustools/CRoaring-LICENSE') != CROARING_LICENSE_SHA256:
        raise ValueError('Changed exact CRoaring 0.2.65 notice')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be new/empty')
    for name in ('bin', 'fixtures', 'licenses'):
        (destination / name).mkdir(parents=True, exist_ok=True)
    sections = []
    def section(name, values):
        sections.append('[' + name + ']\n' + '\n'.join(key + '=' + str(value) for key, value in values.items() if key != 'id' or name == 'pack') + '\n')
    section('pack', dict(format=2, id='bustools', version=VERSION, name='bustools BUS molecule counting', platform='windows-x86_64', description='Barcode correction, sorting and exact-UMI gene counts from a reviewed coherent BUS bundle.', color='#597C8A'))
    for name in ('bustools', 'bustools-guard'):
        path = build / (name + '.exe')
        if sha(path) != record['files'][path.name]['sha256'] or path.read_bytes()[:2] != b'MZ':
            raise ValueError('Changed/non-Windows executable: ' + name)
        shutil.copyfile(path, destination / 'bin' / path.name)
        section('tool:' + ('bustools-adapter' if name.endswith('-guard') else name), dict(path='bin/' + path.name, version=VERSION if name.endswith('-guard') else TOOL_VERSION, sha256=sha(path)))
    workflows, schema = definitions()
    for name, value in [('workbench-schema.json', schema), ('workbench-checks.json', checks())]:
        (destination / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    assets = {'workbench-schema': 'workbench-schema.json', 'workbench-checks': 'workbench-checks.json'}
    spec = importlib.util.spec_from_file_location('bustools_fixture', ROOT / 'tools/bustools/fixtures.py')
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    files = fixture.build_fixture(destination / 'fixtures')
    for identity, path in files.items():
        assets['fixture-' + identity] = path.relative_to(destination).as_posix()
    assets['fixture-expected'] = 'fixtures/expected.json'
    for identity, relative in assets.items():
        section('asset:' + identity, dict(path=relative, sha256=sha(destination / relative)))
    for item in workflows:
        section('workflow:' + item['id'], dict(name=item['name'], description=item['description'], inputs=','.join(v['id'] for v in item['inputs']), outputs=','.join(v['id'] for v in item['outputs']), steps=','.join(v['id'] for v in item['steps'])))
        for kind in ('input', 'output', 'step'):
            for value in item[kind + 's']:
                section(kind + ':' + item['id'] + ':' + value['id'], value)
    (destination / 'pack.ini').write_text('\n'.join(sections), encoding='utf-8')
    licenses = destination / 'licenses'
    for path in [*[cache / name for name in SOURCES], cache / 'workbench1.patch', ROOT / 'tools/bustools/guard.cpp', ROOT / 'tools/bustools/fixtures.py', ROOT / 'tools/bustools/CRoaring-LICENSE', ROOT / 'scripts/build_bustools_native.py', Path(__file__), ROOT / 'LICENSE']:
        shutil.copyfile(path, licenses / ('Workbench-LICENSE.txt' if path.name == 'LICENSE' else path.name))
    with tarfile.open(cache / SOURCE_NAME) as archive:
        notices = [('LICENSE', 'bustools-BSD2.txt'), ('dependencies/LBFGSpp-2020-03-06/LICENSE.md', 'LBFGSpp-MIT.txt'), ('dependencies/CppNumericalSolvers-v1/LICENSE', 'CppNumericalSolvers-MIT.txt')]
        notices += [('dependencies/eigen-3.3.7/' + name, 'Eigen-' + name) for name in ['COPYING.README','COPYING.MPL2','COPYING.BSD','COPYING.GPL','COPYING.LGPL','COPYING.MINPACK']]
        for relative, name in notices:
            (licenses / name).write_bytes(archive.extractfile('bustools-' + SOURCE_COMMIT + '/' + relative).read())
    with tarfile.open(cache / 'zlib-1.3.2.tar.gz') as archive:
        (licenses / 'zlib-LICENSE.txt').write_bytes(archive.extractfile('zlib-1.3.2/LICENSE').read())
    shutil.copyfile(build / 'build.json', licenses / 'build-provenance.json')
    for name, digest in record['compilerNotices'].items():
        if sha(build / 'compiler-notices' / name) != digest:
            raise ValueError('Changed compiler/runtime notice')
        shutil.copyfile(build / 'compiler-notices' / name, licenses / ('compiler-' + name))
    (licenses / 'NOTICE.txt').write_text('bustools 0.45.1-workbench1, upstream Copyright (c) 2018 BUStools, BSD 2-Clause.\nThis is a Native Workbench source build, not an official upstream binary.\nScientific algorithms are unchanged; workbench1.patch marks the version and makes Roaring inline linkage private for COFF.\nComplete upstream and zlib 1.3.2 sources, patch, recipes, guard and compiler/runtime notices are included.\nBundled Eigen 3.3.7 is primarily MPL2 (all COPYING notices included); LBFGSpp and CppNumericalSolvers carry MIT notices.\nBundled CRoaring 0.2.65 carries Apache2: exact upstream licence from ' + CROARING_LICENSE_URL + '\nSHA256 ' + CROARING_LICENSE_SHA256 + '\nEmbedded dependency notices including public-domain MurmurHash remain in complete source.\nThe separate MIT Workbench adapter validates bounded input/output structure and invokes real bustools shell-free.\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/BUSTOOLS-PACK.md', destination / 'PACK-README.md')
    sys.path.insert(0, str(ROOT / 'workspace'))
    from catalog import load_pack
    pack = load_pack(destination / 'pack.ini')
    print(json.dumps({'pack': str(destination), 'manifestSha256': sha(destination / 'pack.ini'), 'workflows': list(pack['workflows']), 'checks': len(checks()['checks'])}, indent=2))


if __name__ == '__main__':
    main()
