#!/usr/bin/env python3
"""Independent synthetic BUS truth, bounded invalid bundles and exact native pack checks."""
import argparse
import configparser
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
PACK = None
BUILD = ROOT / 'build/bustools-linux'
REFERENCE = None
EXECUTIONS = []
VERSION = '0.45.1-workbench1'
SOURCE_COMMIT = 'd4d7a283dbe9d34d2106e9ba31e2566413be6a70'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024),b''):
            digest.update(data)
    return digest.hexdigest()

def inventory(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in Path(path).rglob('*') if p.is_file()}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded

FIXTURE=module('bustools_independent_fixture', ROOT/'tools/bustools/fixtures.py')
FIELDS=['bus','transcripts','equivalence-classes','genes','allowlist']

def read_matrix(directory):
    directory=Path(directory)
    barcodes=(directory/'counts.barcodes.txt').read_text().splitlines()
    genes=(directory/'counts.genes.txt').read_text().splitlines()
    lines=[line for line in (directory/'counts.mtx').read_text().splitlines() if line and not line.startswith('%')]
    rows,cols,n=map(int,lines[0].split())
    assert (rows,cols,n)==(len(barcodes),len(genes),len(lines)-1)
    result={bc:{} for bc in barcodes}
    for line in lines[1:]:
        r,c,value=line.split();r=int(r)-1;c=int(c)-1
        result[barcodes[r]][genes[c]]=int(value)
    return result

class SourceTests(unittest.TestCase):
    def test_01_metadata_uses_coherent_group_and_no_global_type(self):
        import prepare_bustools_pack as prep
        workflows,schema=prep.definitions()
        item=schema['workflows']['count-bus']
        self.assertEqual(item['ports'][0]['manifestInputs'],FIELDS)
        self.assertEqual(item['ports'][0]['type'],'file')
        self.assertTrue(item['pathPolicy']['asciiOnly'])
        self.assertEqual([w['id'] for w in workflows],['count-bus'])
        self.assertIn('same run/index',item['methods'])
        self.assertIn('not a whole-process memory limit',item['methods'])
        labels=next(o for o in workflows[0]['outputs'] if o['id']=='barcode-labels')
        self.assertEqual(labels['nonempty'],'false')
    def test_02_source_pins_patch_and_licence(self):
        import build_bustools_native as builder
        import prepare_bustools_pack as prep
        self.assertEqual(builder.SOURCE_COMMIT,SOURCE_COMMIT)
        self.assertEqual(builder.VERSION,VERSION)
        self.assertEqual(sha(ROOT/'tools/bustools/CRoaring-LICENSE'),prep.CROARING_LICENSE_SHA256)
        self.assertEqual(builder.SOURCE_SHA256,'b014317ea4501c3314ac358eb074dbbe3a10ed6daec53587f17a897e670e40df')
        self.assertEqual(FIXTURE.TRUTH['inputReadMultiplicity'],sum(row[3] for row in FIXTURE.RECORDS))
    def test_03_declared_installed_assets_and_checks(self):
        import prepare_bustools_pack as prep
        checks=prep.checks()
        if PACK:
            config=configparser.ConfigParser(interpolation=None);config.read(PACK/'pack.ini',encoding='utf-8')
            self.assertEqual(config['pack']['version'],'1.0.0')
            for section in config.sections():
                if section.startswith(('tool:','asset:')):
                    self.assertEqual(sha(PACK/config[section]['path']),config[section]['sha256'])
            checks=json.loads((PACK/'workbench-checks.json').read_text())
        self.assertEqual(checks['checks'][0]['inputs']['bundle'][0],{k:'fixture-'+k for k in FIELDS})

class ScientificTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='bustools science ')
        self.directory=Path(self.temporary.name)
        self.files=FIXTURE.build_fixture(self.directory/'input bundle')
        self.guard=(PACK/'bin' if PACK else BUILD)/('bustools-guard.exe' if os.name=='nt' else 'bustools-guard')
        self.binary=self.guard.parent/('bustools.exe' if os.name=='nt' else 'bustools')
        self.counter=0
        self.before=inventory(self.guard.parent)
    def tearDown(self):
        self.assertEqual(inventory(self.guard.parent),self.before)
        self.temporary.cleanup()
    def command(self,args,cwd=None,timeout=120):
        child=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=timeout)
        EXECUTIONS.append({'command':[str(v) for v in args],'returncode':child.returncode,'stdout':child.stdout,'stderr':child.stderr})
        return child
    def run_tool(self,success=True,files=None,guard=None):
        self.counter+=1
        out=self.directory/('results with spaces '+str(self.counter));out.mkdir()
        paths=files or self.files
        before={str(p):sha(p) for p in paths.values()}
        child=self.command([guard or self.guard,*[paths[k] for k in FIELDS],out])
        self.assertEqual(child.returncode==0,success,child.stdout+'\n'+child.stderr)
        self.assertEqual({str(p):sha(p) for p in paths.values()},before)
        if not success:self.assertFalse((out/'summary.json').exists())
        return out,child
    def truth(self,out):
        self.assertEqual(read_matrix(out),FIXTURE.TRUTH['matrix'])
        summary=json.loads((out/'summary.json').read_text())
        for key in ['inputRecords','inputReadMultiplicity','retainedRecords','retainedReadMultiplicity','countedMolecules','barcodes','genes','nonzeroEntries']:
            self.assertEqual(summary[key],FIXTURE.TRUTH[key],key)
        self.assertEqual(summary['sortedRecords'],11)
        self.assertFalse(summary['cellCallingPerformed']);self.assertFalse(summary['qcThresholdsApplied'])
    def test_01_independent_correction_aggregation_and_ambiguity_truth(self):
        out,_=self.run_tool();self.truth(out)
        version=self.command([self.binary,'version'])
        self.assertEqual(version.returncode,0);self.assertIn(VERSION,version.stdout+version.stderr)
    def test_02_header_only_bus_is_successful_empty_matrix(self):
        self.files['bus'].write_bytes(FIXTURE.bus_bytes([]))
        out,_=self.run_tool()
        self.assertEqual(read_matrix(out),{})
        summary=json.loads((out/'summary.json').read_text())
        self.assertEqual((summary['barcodes'],summary['genes'],summary['countedMolecules']),(0,3,0))
        self.assertIn('valid result',(out/'adapter.log').read_text())
    def test_03_all_barcodes_dropped_is_successful_empty_matrix(self):
        self.files['allowlist'].write_text('AGTA\n')
        out,_=self.run_tool();self.assertEqual(read_matrix(out),{})
        self.assertEqual(json.loads((out/'summary.json').read_text())['discardedBarcodeRecords'],14)
    def test_04_ambiguous_umi_can_retain_zero_barcode_row(self):
        self.files['bus'].write_bytes(FIXTURE.bus_bytes([('AAAA','AAAA',4,9)]))
        out,_=self.run_tool();self.assertEqual(read_matrix(out),{'AAAA':{}})
    def test_05_lf_crlf_and_optional_gene_name_are_equivalent(self):
        # Fixture text-mode writes use the host newline convention. Establish
        # exact LF bytes first, avoiding CR-CR-LF when running on Windows.
        for key,path in self.files.items():
            if key!='bus':
                lf=path.read_bytes().replace(b'\r\n',b'\n')
                self.assertNotIn(b'\r',lf)
                self.assertIn(b'\n',lf)
                path.write_bytes(lf)
        first,_=self.run_tool();self.truth(first)
        for key,path in self.files.items():
            if key!='bus':
                crlf=path.read_bytes().replace(b'\n',b'\r\n')
                self.assertIn(b'\r\n',crlf)
                self.assertNotIn(b'\r\r\n',crlf)
                self.assertNotIn(b'\n',crlf.replace(b'\r\n',b''))
                path.write_bytes(crlf)
        self.files['genes'].write_bytes(b''.join((tx+'\t'+gene+'\tGene label\r\n').encode() for tx,gene in zip(FIXTURE.TRANSCRIPTS,FIXTURE.GENES)))
        second,_=self.run_tool();self.truth(second)
        self.assertEqual((first/'summary.json').read_bytes(),(second/'summary.json').read_bytes())
        # The originally failing test generated this malformed sequence.
        # It must remain a rejected input, not become accepted by the adapter.
        path=self.files['transcripts']
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\r\r\n'))
        _,child=self.run_tool(False)
        self.assertIn('Plain ASCII text required',child.stderr)
    def test_06_corrupt_magic_version_truncation_and_header_reject(self):
        good=FIXTURE.bus_bytes()
        variants=[b'BUS\1'+good[4:],good[:4]+struct.pack('<I',2)+good[8:],good[:19],good[:-1],good[:16]+struct.pack('<I',5000)+good[20:]]
        for data in variants:
            with self.subTest(data=data[:20]):self.files['bus'].write_bytes(data);self.run_tool(False)
    def test_07_unsupported_lengths_metadata_zero_or_overflow_count_reject(self):
        good=FIXTURE.bus_bytes();pos=20+struct.unpack_from('<I',good,16)[0]
        cases=[]
        for offset,value in [(8,0),(8,17),(8,32),(12,0),(12,32),(pos+24,1),(pos+28,1),(pos+20,0)]:
            data=bytearray(good);struct.pack_into('<I',data,offset,value);cases.append(data)
        for offset in [pos,pos+8]:
            data=bytearray(good);struct.pack_into('<Q',data,offset,1<<20);cases.append(data)
        data=bytearray(good);struct.pack_into('<I',data,pos+20,2**32-1);cases.append(data)
        for data in cases:
            with self.subTest(data=data[:20]):self.files['bus'].write_bytes(data);self.run_tool(False)
    def test_08_absent_ec_and_mismatched_transcript_association_reject(self):
        good=FIXTURE.bus_bytes();pos=20+struct.unpack_from('<I',good,16)[0]
        for value in [-1,99]:
            data=bytearray(good);struct.pack_into('<i',data,pos+16,value);self.files['bus'].write_bytes(data);self.run_tool(False)
        self.files['bus'].write_bytes(good)
        for text in ['0\t0\n2\t1\n','0\t99\n','0\t0,0\n','0\t2,1\n','0\t\n','18446744073709551616\t0\n']:
            self.files['equivalence-classes'].write_text(text);self.run_tool(False)
    def test_09_incomplete_duplicate_unknown_mappings_reject(self):
        for text in ['txA1\tgeneA\n','txA1\tgeneA\ntxA1\tgeneB\n','absent\tgeneA\n','txA1 geneA\n']:
            self.files['genes'].write_text(text);self.run_tool(False)
    def test_10_wrong_or_ambiguous_allowlist_format_reject(self):
        for text in ['','AAAA\nAAAA\n','AAAA-1\n','AAA\n','AAAN\n','aaaa\n']:
            self.files['allowlist'].write_text(text);self.run_tool(False)
        self.files['allowlist'].write_bytes(b'\x1f\x8bcompressed');self.run_tool(False)
    def test_11_space_paths_and_nonascii_path_reject(self):
        out,_=self.run_tool();self.truth(out)
        other=self.directory/'input \u00e9.bus';shutil.copyfile(self.files['bus'],other)
        self.files['bus']=other
        _,child=self.run_tool(False);self.assertIn('ASCII',child.stderr)
    def test_12_existing_outputs_and_temporary_files_are_preserved(self):
        out,_=self.run_tool();before=inventory(out)
        child=self.command([self.guard,*[self.files[k] for k in FIELDS],out]);self.assertNotEqual(child.returncode,0)
        self.assertEqual(inventory(out),before)
    def test_13_missing_child_and_aliased_inputs_fail_clearly(self):
        isolated=self.directory/'incomplete pack';isolated.mkdir();guard=isolated/self.guard.name;shutil.copyfile(self.guard,guard);guard.chmod(0o755)
        _,child=self.run_tool(False,guard=guard);self.assertIn('reinstall this pack',child.stderr)
        self.files['allowlist']=self.files['transcripts'];_,child=self.run_tool(False);self.assertIn('distinct',child.stderr)
    def test_14_byte_and_record_bounds_reject_before_execution(self):
        with self.files['bus'].open('wb') as stream:stream.truncate(64*1024*1024+4117)
        self.run_tool(False)
        header=FIXTURE.bus_bytes([]);record=struct.pack('<QQiIII',0,0,0,1,0,0)
        with self.files['bus'].open('wb') as stream:stream.write(header);stream.write(record*2000001)
        self.run_tool(False)
    def test_15_repeated_execution_and_upper_supported_lengths(self):
        first,_=self.run_tool();second,_=self.run_tool()
        for name in ['counts.mtx','counts.genes.txt','counts.barcodes.txt','summary.json','sorted.bus']:
            self.assertEqual((first/name).read_bytes(),(second/name).read_bytes())
        bc='A'*16;umi='T'*31
        self.files['bus'].write_bytes(FIXTURE.bus_bytes([(bc,umi,0,1)],16,31));self.files['allowlist'].write_text(bc+'\n')
        out,_=self.run_tool();self.assertEqual(read_matrix(out),{bc:{'geneA':1}})
    def test_16_upstream_external_sort_spills_in_space_path(self):
        # This isolates the bundled sort's disk merge above the guard's 2M-record
        # interface limit; it is not a claim that the pack accepts larger bundles.
        source=self.directory/'external sort input.bus'
        count=2100000;header=FIXTURE.bus_bytes([]);record=struct.pack('<QQiIII',0,0,0,1,0,0)
        with source.open('wb') as stream:
            stream.write(header)
            for _ in range(21):stream.write(record*100000)
        out=self.directory/'external sorted.bus';temp=self.directory/'sort temporary';temp.mkdir()
        child=self.command([self.binary,'sort','-t','1','-m','64M','-T',temp,'-o',out,source],timeout=180)
        self.assertEqual(child.returncode,0,child.stderr)
        data=out.read_bytes();offset=20+struct.unpack_from('<I',data,16)[0]
        self.assertEqual(len(data)-offset,32)
        self.assertEqual(struct.unpack_from('<QQiIII',data,offset),(0,0,0,count,0,0))
        self.assertNotIn('all fits in buffer',child.stderr)
        self.assertIn('2100000 BUS records',child.stderr)

class ReferenceTests(ScientificTests):
    # Keep only explicit independent pristine comparisons below.
    def reference(self,records):
        self.files['bus'].write_bytes(FIXTURE.bus_bytes(records))
        out,_=self.run_tool();reference=self.directory/'pristine reference';reference.mkdir()
        commands=[[REFERENCE,'correct','-w',self.files['allowlist'],'-o',reference/'corrected.bus',self.files['bus']],
                  [REFERENCE,'sort','-t','1','-m','64M','-T',reference,'-o',reference/'sorted.bus',reference/'corrected.bus'],
                  [REFERENCE,'count','-o',reference/'counts','-g',self.files['genes'],'-e',self.files['equivalence-classes'],'-t',self.files['transcripts'],'--genecounts',reference/'sorted.bus']]
        for command in commands:
            result=self.command(command);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(read_matrix(out),read_matrix(reference))
        if records:
            self.assertEqual((out/'sorted.bus').read_bytes(),(reference/'sorted.bus').read_bytes())
        else:
            self.assertEqual((reference/'sorted.bus').stat().st_size,0)
            self.assertEqual((out/'sorted.bus').read_bytes(),(out/'corrected.bus').read_bytes())
            self.assertTrue(json.loads((out/'settings.json').read_text())['emptySortedBusHeaderPreserved'])
    def test_reference_01_truth(self):self.reference(FIXTURE.RECORDS)
    def test_reference_02_empty(self):self.reference([])
    def test_reference_03_ambiguity(self):self.reference([('AAAA','AAAA',4,7),('AAAA','AAAC',0,1),('AAAA','AAAC',2,1)])

# Prevent inherited normal tests duplicating reference counts.
for name in list(ScientificTests.__dict__):
    if name.startswith('test_'):setattr(ReferenceTests,name,None)

class BoundaryFaultTests(ScientificTests):
    def fault(self, records, exit_code):
        isolated=self.directory/'injected boundary';isolated.mkdir()
        guard=isolated/self.guard.name;shutil.copyfile(self.guard,guard);guard.chmod(0o755)
        stub=isolated/'bustools'
        stub.write_text('#!' + sys.executable + '\nimport pathlib,subprocess,sys\n'
                        + 'args=sys.argv[1:]\n'
                        + 'if args[0]=="sort":\n'
                        + ' pathlib.Path(args[args.index("-o")+1]).write_bytes(b"")\n'
                        + ' sys.exit(' + str(exit_code) + ')\n'
                        + 'sys.exit(subprocess.call([' + repr(str(self.binary)) + ']+args))\n')
        stub.chmod(0o755)
        self.files['bus'].write_bytes(FIXTURE.bus_bytes(records))
        out,child=self.run_tool(False,guard=guard)
        self.assertFalse((out/'counts.mtx').exists())
        return child
    def test_fault_01_nonzero_input_empty_sorted_output_is_failure(self):
        self.assertIn('BUS version 1',self.fault(FIXTURE.RECORDS,0).stderr)
    def test_fault_02_empty_input_failed_sort_exit_is_failure(self):
        self.assertIn('sort failed (exit 7)',self.fault([],7).stderr)

for name in list(ScientificTests.__dict__):
    if name.startswith('test_'):setattr(BoundaryFaultTests,name,None)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path);parser.add_argument('--build',type=Path,default=BUILD)
    parser.add_argument('--reference-binary',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args();PACK=args.pack.resolve() if args.pack else None;BUILD=args.build.resolve()
    REFERENCE=args.reference_binary.resolve() if args.reference_binary else None
    if os.name=='nt' and not PACK:parser.error('Exact installed --pack required for native Windows tests')
    selected=(PACK/'bin' if PACK else BUILD)/('bustools-guard.exe' if os.name=='nt' else 'bustools-guard')
    binary=selected.parent/('bustools.exe' if os.name=='nt' else 'bustools')
    if not selected.is_file() or not binary.is_file():parser.error('Compiled bustools and guard are required')
    if REFERENCE and (os.name=='nt' or not REFERENCE.is_file()):parser.error('Pristine reference comparison requires an existing Linux binary')
    classes=[SourceTests,ScientificTests]+([BoundaryFaultTests] if os.name!='nt' else [])+([ReferenceTests] if REFERENCE else [])
    started=time.monotonic();suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    evidence={'schema':1,'packId':'bustools','packVersion':'1.0.0','toolVersion':VERSION,'platform':sys.platform,'nativeWindowsExecuted':os.name=='nt',
              'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':[{'test':str(t),'reason':r} for t,r in result.skipped],
              'success':result.wasSuccessful(),'seconds':round(time.monotonic()-started,3),'testSourceSha256':sha(__file__),
              'guardExecutableSha256':sha(selected),'scientificBinarySha256':sha(binary),'packManifestSha256':sha(PACK/'pack.ini') if PACK else None,
              'upstreamSourceCommit':SOURCE_COMMIT,'referenceBinarySha256':sha(REFERENCE) if REFERENCE else None,'pristineReferenceCases':3 if REFERENCE else 0,'linuxBoundaryFaultCases':2 if os.name!='nt' else 0,
              'executions':EXECUTIONS,'scope':'Independent synthetic correction, exact-UMI gene-intersection counts and measured empty outcomes; strict coherent-bundle structure, immutability and paths. Direct upstream sort disk-merge test uses 2.1M records outside the guarded 2M interface. No FASTQ pipeline, cell calling, biological association proof, QC thresholds, benchmark or clinical claim.'}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    sys.exit(not result.wasSuccessful())
