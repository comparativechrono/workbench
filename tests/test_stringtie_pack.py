#!/usr/bin/env python3
"""Independent splice/coverage truth, pristine upstream parity and native boundary tests."""
import argparse,configparser,csv,gzip,hashlib,importlib.util,json,math,os,re,shutil,struct,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACK=None;BUILD=ROOT/'build/stringtie-linux';REFERENCE_BINARY=ROOT/'build/stringtie-reference-linux/stringtie';EXECUTIONS=[];REFERENCE_CASES=[]
DEFAULT=['200','1','1','0.01','4.75','1']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
GEN=module('stringtie_fixture_factory',ROOT/'tools/stringtie/fixtures.py')
def inventory(path):return {p.relative_to(path).as_posix():sha(p) for p in path.rglob('*') if p.is_file()}
def parse_gtf(path):
    txs={}
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith('#'):continue
        c=line.split('\t');assert len(c)==9,c
        a=dict(re.findall(r'(\w+) "([^\"]*)"',c[8]));tid=a['transcript_id'];row=txs.setdefault(tid,{'id':tid,'reference':a.get('reference_id',tid),'gene':a.get('ref_gene_id',a['gene_id']),'chrom':c[0],'strand':c[6],'exons0':[]})
        if c[2]=='exon':row['exons0'].append([int(c[3])-1,int(c[4])])
        if c[2]=='transcript':
            for k in ('cov','FPKM','TPM'):
                row[k]=float(a[k]);assert math.isfinite(row[k]) and row[k]>=0
    return txs

def validate_hisat_graph(run,fixture):
    """Import-safe integration oracle; no app module imports or path rewriting."""
    truth=json.loads((Path(fixture)/'truth.json').read_text())['integration'];outputs=run['outputs']
    def output(port,name):return Path(outputs[port]['files'][name])
    sam=output('step-1::aligned-sam','aligned-sam');rows=[l.split('\t') for l in sam.read_text().splitlines() if l and not l.startswith('@')];assert len(rows)==truth['records'];pairs={}
    for row in rows:
        flag=int(row[1]);mate=1 if flag&64 else 2;expected=truth['expectedAlignments'][mate-1];assert flag==expected['flag'];assert int(row[3])==expected['position1'];assert row[5]==expected['cigar'];assert row[2]==truth['reference']['name'];assert 'NH:i:1' in row[11:]
        if mate==1:assert 'XS:A:+' in row[11:]
        pairs.setdefault(row[0],set()).add(mate)
    assert len(pairs)==truth['pairs'] and all(v=={1,2} for v in pairs.values())
    txs=parse_gtf(output('step-2::transcripts','transcripts'));settings=json.loads(output('step-2::settings','settings').read_text());summary=json.loads(output('step-2::summary','summary').read_text());assert settings['minimumTranscriptLength']==100;assert summary['mappedRecords']==24 and summary['splicedRecords']==12
    expected=[x for x in txs.values() if x['reference']==truth['transcript']];assert len(expected)==1,txs;tx=expected[0];assert tx['exons0']==truth['exons0'] and tx['strand']=='+';assert abs(tx['cov']-truth['meanAlignedBaseCoverage'])<1e-5;assert abs(tx['TPM']-1000000)<1e-4
    return {'success':True,'pairedFragments':len(pairs),'alignmentRecords':len(rows),'splicedRecords':12,'operation':settings['operation'],'transcriptExons0':tx['exons0'],'coverage':tx['cov'],'tpm':tx['TPM'],'knownCoverageGapBases':60,'interpretation':'Guide-supported transcript and abundance from exact paired splice alignments; not de novo reconstruction proof'}

class SourceTests(unittest.TestCase):
    def test_01_deterministic_fixtures_and_independent_truth(self):
        with tempfile.TemporaryDirectory() as d:
            GEN.fixtures(d)
            for p in (ROOT/'tools/stringtie/fixtures').iterdir():
                if p.is_file():self.assertEqual(p.read_bytes(),(Path(d)/p.name).read_bytes())
            truth=json.loads((Path(d)/'truth.json').read_text());rows=GEN.alignment_rows();self.assertEqual(len(rows),123);self.assertEqual(sum(len(r['sequence']) for r in rows),12300);self.assertEqual(sum(any(op=='N' for n,op in r['cigar']) for r in rows),27);self.assertEqual([t['meanAlignedBaseCoverage'] for t in truth['transcripts']],[8.2,16.4,0])
    def test_02_pack_contract_is_typed_and_explicit(self):
        # These imports affect no application module path; preparation definitions only.
        before=list(sys.path)
        try:
            sys.path.insert(0,str(ROOT/'scripts'));p=module('stringtie_pack_preparer',ROOT/'scripts/prepare_stringtie_pack.py');items,schema=p.definitions()
        finally:sys.path[:]=before
        self.assertEqual([v['id'] for v in items],['assemble-guided','estimate-reference'])
        for v in schema['workflows'].values():self.assertEqual(v['ports'][0]['type'],'bam-rna');self.assertEqual(v['ports'][0]['requiredState'],{'sort':'coordinate'});self.assertEqual(v['ports'][1]['type'],'text')
        for item in items:
            strand=next(x for x in item['inputs'] if x['id']=='strandness');self.assertNotIn('default',strand);self.assertIn('false',str(next(v for v in item['outputs'] if v['id']=='transcripts')['nonempty']).lower())

class ScientificTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindir=PACK/'bin' if PACK else BUILD;cls.guard=cls.bindir/('stringtie-guard.exe' if os.name=='nt' else 'stringtie-guard');cls.binary=cls.bindir/('stringtie.exe' if os.name=='nt' else 'stringtie');cls.fixturetemp=tempfile.TemporaryDirectory(prefix='stringtie-fixtures-');GEN.fixtures(cls.fixturetemp.name);cls.fixtures=PACK/'fixtures' if PACK else Path(cls.fixturetemp.name);cls.truth=json.loads((cls.fixtures/'truth.json').read_text());cls.before=inventory(PACK if PACK else cls.bindir)
    @classmethod
    def tearDownClass(cls):
        assert inventory(PACK if PACK else cls.bindir)==cls.before,'Installed bytes changed';cls.fixturetemp.cleanup()
    def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='stringtie-science-');self.root=Path(self.temp.name);self.counter=0
    def tearDown(self):self.temp.cleanup()
    def run_tool(self,mode='estimate-reference',bam=None,gtf=None,strand='unstranded',settings=None,success=True,guard=None):
        self.counter+=1;out=self.root/('run with spaces '+str(self.counter));out.mkdir();bam=Path(bam or self.fixtures/'spliced.bam');gtf=Path(gtf or self.fixtures/'guide.gtf');before=(sha(bam),sha(gtf));args=[str(guard or self.guard),mode,str(bam),str(gtf),str(out),strand,*(settings or DEFAULT)];r=subprocess.run(args,capture_output=True,text=True,timeout=120);EXECUTIONS.append({'case':self.id(),'operation':mode,'guardSha256':sha(guard or self.guard),'bamSha256':before[0],'gtfSha256':before[1],'returncode':r.returncode,'expectedSuccess':success});self.assertEqual(before,(sha(bam),sha(gtf)))
        if success:self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        else:self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
        return out,r
    def bam(self,rows=None,data=None):
        p=self.root/('input'+str(self.counter)+'.bam');p.write_bytes(data if data is not None else GEN.bam_bytes(rows));return p
    def annotation(self,text):p=self.root/('annotation'+str(self.counter)+'.gtf');p.write_text(text);return p
    def assert_truth(self,out,mode,empty=False):
        txs=parse_gtf(out/'transcripts.gtf');byid={r['reference']:r for r in txs.values()};expected=self.truth['transcripts'] if mode=='estimate-reference' else ([] if empty else self.truth['transcripts'][:2]);self.assertEqual(set(byid),{t['id'] for t in expected})
        for t in expected:
            row=byid[t['id']];self.assertEqual(row['exons0'],t['exons0']);self.assertEqual(row['strand'],t['strand']);self.assertEqual(row['gene'],t['gene']);self.assertAlmostEqual(row['cov'],0 if empty else t['meanAlignedBaseCoverage'],delta=1e-6);self.assertAlmostEqual(row['TPM'],0 if empty else t['idealEqualLengthTpm'],delta=1e-5)
            expected_fpkm=0 if empty else t['alignedReads']/(t['length']/1000)/(123/1000000);self.assertAlmostEqual(row['FPKM'],expected_fpkm,delta=1e-5)
        return byid
    def test_03_two_modes_exact_splice_geometry_coverage_and_abundance(self):
        for mode in ('assemble-guided','estimate-reference'):
            out,_=self.run_tool(mode);self.assert_truth(out,mode);s=json.loads((out/'stringtie-summary.json').read_text());self.assertEqual(s['bamRecords'],123);self.assertEqual(s['splicedRecords'],27);self.assertFalse(s['integerReadCountsProduced']);self.assertFalse(s['assemblyIdentityEstablishedByContigBounds'])
    def test_04_zero_data_is_success_for_both_modes(self):
        for mode in ('assemble-guided','estimate-reference'):
            out,_=self.run_tool(mode,bam=self.fixtures/'empty.bam');self.assert_truth(out,mode,True)
    def test_05_strandedness_recorded_and_scientifically_effective(self):
        # XS takes priority upstream. Remove it only from an unspliced single-exon
        # fixture to measure the explicit library option without overriding tags.
        rows=GEN.alignment_rows()[:16]
        for r in rows:r['strand']=None
        bam=self.bam(rows);gtf=self.annotation('chrSynthetic\tx\texon\t101\t350\t.\t+\t.\tgene_id "one"; transcript_id "one";\n')
        out,_=self.run_tool(bam=bam,gtf=gtf,strand='fr');self.assertGreater(parse_gtf(out/'transcripts.gtf')['one']['cov'],0);self.assertEqual(json.loads((out/'analysis-settings.json').read_text())['strandness'],'fr')
        out,_=self.run_tool(bam=bam,gtf=gtf,strand='rf');self.assertEqual(parse_gtf(out/'transcripts.gtf')['one']['cov'],0)
        # Existing spliced XS tags still describe transcript orientation.
        out,_=self.run_tool(strand='rf');self.assert_truth(out,'estimate-reference')
    def test_06_exact_decimal_settings_are_valid_json(self):
        values=['0200','01','1.','.010000001','4.750001','1.'];out,_=self.run_tool(settings=values);s=json.loads((out/'analysis-settings.json').read_text());self.assertEqual(s['minimumIsoformFraction'],float(values[3]));self.assertEqual(s['minimumSingleExonCoverage'],float(values[4]));self.assertIn(values[3],s['arguments'])
    def test_07_invalid_settings_and_missing_strandedness(self):
        for idx,value in [(0,'29'),(0,'200.5'),(1,'0'),(1,'nan'),(2,'-1'),(3,'1'),(3,'inf'),(4,'0'),(5,'1.1')]:
            v=list(DEFAULT);v[idx]=value;out,_=self.run_tool(settings=v,success=False);self.assertEqual(list(out.iterdir()),[])
        for strand in ('','unknown','--rf'):out,_=self.run_tool(strand=strand,success=False);self.assertEqual(list(out.iterdir()),[])
    def test_08_actual_sort_order_and_header_required(self):
        rows=GEN.alignment_rows();rows[0],rows[-1]=rows[-1],rows[0];out,r=self.run_tool(bam=self.bam(rows),success=False);self.assertIn('coordinate sorted',r.stderr)
        out,r=self.run_tool(bam=self.bam(data=GEN.bam_bytes(GEN.alignment_rows(),sort='queryname')),success=False);self.assertIn('SO:coordinate',r.stderr)
    def test_09_spliced_xs_and_positive_nh_required(self):
        rows=GEN.alignment_rows();rows[20]['strand']=None;out,r=self.run_tool(bam=self.bam(rows),success=False);self.assertIn('XS:A',r.stderr)
        raw=gzip.decompress((self.fixtures/'spliced.bam').read_bytes()).replace(b'NHi\x01\0\0\0',b'NHi\0\0\0\0');out,r=self.run_tool(bam=self.bam(data=GEN._bgzf(raw)+GEN.BGZF_EOF),success=False);self.assertIn('positive integer NH',r.stderr)
    def test_10_unplaced_mapped_supplementary_and_pairing_rejected(self):
        for mutation in ('unplaced','supplementary','mixed','pair-missing-end'):
            rows=GEN.alignment_rows()
            if mutation=='unplaced':rows[0]['ref_id']=-1
            if mutation=='supplementary':rows[0]['flag']|=2048
            if mutation=='mixed':rows[0]['flag']|=65
            if mutation=='pair-missing-end':rows[0]['flag']|=1
            out,_=self.run_tool(bam=self.bam(rows),success=False);self.assertEqual(list(out.iterdir()),[])
    def test_11_truncated_wrongformat_and_reference_bounds(self):
        for data in ((self.fixtures/'spliced.bam').read_bytes()[:-28],b'@HD\tSO:coordinate\n',b'CRAM\x03\0'):
            out,_=self.run_tool(bam=self.bam(data=data),success=False);self.assertEqual(list(out.iterdir()),[])
        rows=GEN.alignment_rows();rows[-1]['pos']=4999;out,r=self.run_tool(bam=self.bam(rows),success=False);self.assertIn('bounds',r.stderr)
    def test_12_annotation_bounds_roles_and_ambiguous_ids(self):
        text=(self.fixtures/'guide.gtf').read_text();cases=[text.replace('chrSynthetic','chrWrong'),text.replace('\t350\t','\t6000\t'),text.replace('transcript_id','missing_id'),text.replace('gene_id "gene_plus";','gene_id "gene_plus"; gene_id "other";'),text.replace('transcript_id "tx_plus";','transcript_id "tx_plus"; transcript_id "other";'),text.replace('gene_minus','gene_plus'),text+'chrSynthetic\tx\texon\t101\t350\t.\t+\t.\tgene_id "gene_plus"; transcript_id "tx_plus";\n']
        for text in cases:out,_=self.run_tool(gtf=self.annotation(text),success=False);self.assertEqual(list(out.iterdir()),[])
    def test_13_paths_spaces_ascii_missing_binary_and_no_overwrite(self):
        bam=self.root/'RNA data with spaces.bam';gtf=self.root/'RNA annotation with spaces.gtf';shutil.copyfile(self.fixtures/'spliced.bam',bam);shutil.copyfile(self.fixtures/'guide.gtf',gtf);out,_=self.run_tool(bam=bam,gtf=gtf);self.assert_truth(out,'estimate-reference')
        if os.name=='nt':
            recorded=json.loads((out/'analysis-settings.json').read_text())['arguments']
            for value in [recorded[1],*[recorded[recorded.index(flag)+1] for flag in ('-G','-o','-A')]]:self.assertNotIn('\\',value)
        nonascii=self.root/'é.bam';shutil.copyfile(bam,nonascii);_,r=self.run_tool(bam=nonascii,success=False);self.assertIn('ASCII',r.stderr)
        before=inventory(out);r=subprocess.run([str(self.guard),'estimate-reference',str(bam),str(gtf),str(out),'unstranded',*DEFAULT],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual(inventory(out),before)
        isolated=self.root/'missing';isolated.mkdir();guard=isolated/self.guard.name;shutil.copyfile(self.guard,guard);guard.chmod(0o755);_,r=self.run_tool(guard=guard,success=False);self.assertIn('reinstall',r.stderr)
    def test_14_repeated_execution_and_exact_pinned_version(self):
        a,_=self.run_tool();b,_=self.run_tool();self.assertEqual(parse_gtf(a/'transcripts.gtf'),parse_gtf(b/'transcripts.gtf'));self.assertEqual((a/'gene-abundance.tsv').read_bytes(),(b/'gene-abundance.tsv').read_bytes());r=subprocess.run([str(self.binary),'--version'],capture_output=True,text=True);self.assertEqual(r.returncode,0);self.assertEqual(r.stdout.strip(),'3.0.3-workbench1')
    def test_17_guided_assembly_recovers_unannotated_opposite_strand_model(self):
        annotation=self.annotation('\n'.join(l for l in (self.fixtures/'guide.gtf').read_text().splitlines() if 'gene_minus' not in l)+'\n')
        out,_=self.run_tool('assemble-guided',gtf=annotation);rows=parse_gtf(out/'transcripts.gtf');novel=[r for r in rows.values() if r['strand']=='-'];self.assertEqual(len(novel),1);self.assertEqual(novel[0]['exons0'],[[1500,1750],[1850,2100]]);self.assertEqual(novel[0]['reference'],novel[0]['id'])
        out,_=self.run_tool('estimate-reference',gtf=annotation);rows=parse_gtf(out/'transcripts.gtf');self.assertEqual(set(rows),{'tx_plus','tx_unexpressed'});self.assertTrue(all(r['strand']=='+' for r in rows.values()))
    def test_18_multimapping_weighting_uses_nh(self):
        raw=gzip.decompress((self.fixtures/'spliced.bam').read_bytes()).replace(b'NHi\x01\0\0\0',b'NHi\x02\0\0\0');bam=self.bam(data=GEN._bgzf(raw)+GEN.BGZF_EOF);out,_=self.run_tool(bam=bam);rows=parse_gtf(out/'transcripts.gtf');self.assertAlmostEqual(rows['tx_plus']['cov'],4.1,delta=1e-6);self.assertAlmostEqual(rows['tx_minus']['cov'],8.2,delta=1e-6)
    def test_19_native_fatal_output_path_exits_without_modal_dialog(self):
        blocker=self.root/'file blocks output directory';blocker.write_text('existing file, not a directory')
        args=[str(self.binary),str(self.fixtures/'spliced.bam'),'-G',str(self.fixtures/'guide.gtf'),'-o',(blocker/'transcripts.gtf').as_posix(),'-p','1']
        started=time.monotonic();r=subprocess.run(args,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertIn('Error creating',r.stderr);self.assertEqual(blocker.read_text(),'existing file, not a directory')
        EXECUTIONS.append({'case':self.id(),'scientificBinarySha256':sha(self.binary),'expectedSuccess':False,'returncode':r.returncode,'directUpstreamFatalPath':True,'deadlineSeconds':10,'seconds':round(time.monotonic()-started,3)})
    def test_15_installed_source_and_binary_identity(self):
        record=json.loads((PACK/'licenses/build-provenance.json' if PACK else BUILD/'build.json').read_text());self.assertFalse(record['upstreamSourceUnmodified']);self.assertEqual(record['patchSha256'],sha(ROOT/'tools/stringtie/workbench1.patch'));self.assertTrue(record['upstreamScientificAlgorithmsUnmodified']);self.assertEqual(record['upstreamCommit'],'3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19');self.assertEqual(sha(self.binary),record['files'][self.binary.name]['sha256']);self.assertEqual(sha(self.guard),record['files'][self.guard.name]['sha256'])
        if PACK:
            cfg=configparser.ConfigParser(interpolation=None);cfg.read(PACK/'pack.ini',encoding='utf-8')
            for section in cfg.sections():
                if section.startswith(('asset:','tool:')):self.assertEqual(sha(PACK/cfg[section]['path']),cfg[section]['sha256'])

class LinuxReferenceTests(unittest.TestCase):
    def test_16_fresh_unmodified_upstream_comparison(self):
        record=json.loads((REFERENCE_BINARY.parent/'build.json').read_text());self.assertTrue(record['upstreamSourceUnmodified']);self.assertEqual(record['upstreamCommit'],'3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19');self.assertEqual(sha(REFERENCE_BINARY),record['files']['stringtie']['sha256'])
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);fixtures=d/'fixtures';GEN.fixtures(fixtures)
            for mode,empty in [('assemble-guided',False),('estimate-reference',False),('estimate-reference',True),('assemble-guided',True)]:
                out=d/(mode+str(empty));out.mkdir();bam=fixtures/('empty.bam' if empty else 'spliced.bam');args=[str(BUILD/'stringtie-guard'),mode,str(bam),str(fixtures/'guide.gtf'),str(out),'unstranded',*DEFAULT];subprocess.run(args,check=True,capture_output=True)
                expected=d/(mode+str(empty)+'.gtf');args=json.loads((out/'analysis-settings.json').read_text())['arguments'];args[0]=str(REFERENCE_BINARY);args[args.index('-o')+1]=str(expected);args[args.index('-A')+1]=str(expected)+'.tsv';subprocess.run(args,check=True,capture_output=True);self.assertEqual(parse_gtf(out/'transcripts.gtf'),parse_gtf(expected));self.assertEqual((out/'gene-abundance.tsv').read_bytes(),Path(str(expected)+'.tsv').read_bytes());REFERENCE_CASES.append({'operation':mode,'empty':empty,'bamSha256':sha(bam),'referenceBinarySha256':sha(REFERENCE_BINARY),'exactParsedOutputMatch':True})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path);p.add_argument('--build',type=Path,default=BUILD);p.add_argument('--reference-binary',type=Path,default=REFERENCE_BINARY);p.add_argument('--report',type=Path);a=p.parse_args();PACK=a.pack.resolve() if a.pack else None;BUILD=a.build.resolve();REFERENCE_BINARY=a.reference_binary.resolve();selected=(PACK/'bin' if PACK else BUILD)/('stringtie-guard.exe' if os.name=='nt' else 'stringtie-guard');binary=selected.parent/('stringtie.exe' if os.name=='nt' else 'stringtie')
    if not selected.is_file() or not binary.is_file():p.error('Matching built/installed StringTie binaries required')
    if os.name!='nt' and not REFERENCE_BINARY.is_file():p.error('Fresh pinned pristine reference binary required')
    classes=[SourceTests,ScientificTests]+([LinuxReferenceTests] if os.name!='nt' else []);started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in classes));evidence={'schema':1,'packId':'stringtie','packVersion':'1.0.0','upstreamVersion':'3.0.3','toolVersion':'3.0.3-workbench1','platform':sys.platform,'nativeWindowsExecuted':os.name=='nt','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':[{'test':str(t),'reason':r} for t,r in result.skipped],'success':result.wasSuccessful(),'seconds':round(time.monotonic()-started,3),'testSourceSha256':sha(__file__),'guardExecutableSha256':sha(selected),'scientificBinarySha256':sha(binary),'packManifestSha256':sha(PACK/'pack.ini') if PACK else None,'upstreamSourceCommit':'3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19','upstreamSourceArchiveSha256':'52a5d94b0e85404d740d2c7a0c7cc698d373a1b8888e9a2a395ae294032d95c0','livePinnedLinuxReferenceCases':len(REFERENCE_CASES),'referenceCases':REFERENCE_CASES,'executions':EXECUTIONS,'scope':'Independent exon/strand/coverage and 1:2 expression truth, zero expression, explicit strandedness, pristine parity, bounded malformed-input rejection, immutability and path semantics; no benchmark/DE/clinical claim.'}
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(evidence,indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
