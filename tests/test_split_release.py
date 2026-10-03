"""Portable-release boundaries and pack archive contract; no scientific execution."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import package_split as package


def put(root,name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path


def fake_pack(root,identity='example',version='1.0.0'):
    executable=b'synthetic bytes, not executable';identity_sha=hashlib.sha256(executable).hexdigest()
    text=f'''[pack]
format=2
id={identity}
version={version}
name=Example
platform=windows-x86_64
[tool:example]
path=bin/example.exe
version=1.0
sha256={identity_sha}
[workflow:run]
name=Run example
inputs=
outputs=result
steps=run
[output:run:result]
label=Result
path=result.txt
[step:run:run]
label=Run
kind=exec
tool=example
stdout=result
'''
    put(root,'pack.ini',text.encode());put(root,'bin/example.exe',executable)
    put(root,'licenses/LICENSE.txt',b'complete license notice')
    put(root,'licenses/source.tar.gz',b'exact corresponding source fixture')
    return text.encode()


class SplitRelease(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.pack=self.root/'example-1.0.0';self.raw=fake_pack(self.pack)
    def tearDown(self):self.temp.cleanup()

    def test_pack_archive_envelope_matches_all_bytes_and_preserves_manifest(self):
        output=self.root/'pack.zip';result=package.build_pack(self.pack,output)
        self.assertEqual((self.pack/'pack.ini').read_bytes(),self.raw)
        self.assertEqual(result['sha256'],hashlib.sha256(output.read_bytes()).hexdigest())
        with zipfile.ZipFile(output) as zipped:
            self.assertEqual(zipped.read('pack/pack.ini'),self.raw)
            envelope=json.loads(zipped.read('workbench-pack.json'))
            self.assertEqual(set(envelope),{'schema','id','version','packApi','minAppVersion','platform','manifestSha256','files'})
            self.assertEqual(envelope['manifestSha256'],hashlib.sha256(self.raw).hexdigest())
            expected={'workbench-pack.json'}
            for entry in envelope['files']:
                path='pack/'+entry['path'];data=zipped.read(path);expected.add(path)
                self.assertEqual(entry['size'],len(data));self.assertEqual(entry['sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(set(zipped.namelist()),expected)
            self.assertIn('pack/licenses/source.tar.gz',expected)

    def test_pack_publisher_rejects_undeclared_runtime_and_links(self):
        put(self.pack,'bin/extra.dll',b'undeclared')
        with self.assertRaises(ValueError):package.build_pack(self.pack,self.root/'bad.zip')
        (self.pack/'bin/extra.dll').unlink();(self.pack/'licenses/link').symlink_to(self.pack/'pack.ini')
        with self.assertRaises(ValueError):package.build_pack(self.pack,self.root/'bad.zip')
        self.assertFalse((self.root/'bad.zip').exists())

    def test_pack_publisher_rejects_modified_executable_and_never_overwrites(self):
        put(self.pack,'bin/example.exe',b'changed')
        with self.assertRaises(ValueError):package.build_pack(self.pack,self.root/'bad.zip')
        fake_pack(self.pack);existing=put(self.root,'exists.zip',b'keep')
        with self.assertRaises(ValueError):package.build_pack(self.pack,existing)
        self.assertEqual(existing.read_bytes(),b'keep')

    def test_source_companions_verify_exact_legacy_source_bytes(self):
        base=self.root/'base';folder=base/'packs/example-1.0.0';fake_pack(folder)
        source=folder/'licenses/source.tar.gz'
        value={'restore_from_runtime':[{'source_path':'vendor/example.tar.gz','runtime_path':'packs/example-1.0.0/licenses/source.tar.gz',
                 'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}
        put(base,'docs/SOURCE-CONTENTS-0.5.4.json',json.dumps(value).encode())
        contents,companions=package.source_companions(base)
        self.assertEqual(contents,value);self.assertEqual(companions[0]['file'],'native-workbench-pack-example-1.0.0.zip')
        source.write_bytes(b'changed source')
        with self.assertRaises(ValueError):package.source_companions(base)

    def test_runtime_inventory_contains_new_independent_manager_and_checks(self):
        self.assertTrue({'pack_manager.py','pack_security.py','core_checks.py'}<=set(package.RUNTIME_MODULES))
        self.assertNotIn('server.py',package.RUNTIME_MODULES)
        self.assertEqual(package.STARTER,('align-0.4.0','bam-0.4.0','variants-0.4.0'))

    def test_core_inventory_rejects_nested_packs_and_case_collisions(self):
        value={'schema_version':2,'version':'0.6.0','ownership':'core','pack_management':'independent',
               'interface':'native-win32','requires_browser':False,'transport':'anonymous-pipes','manifest_includes_itself':False,
               'files':[{'path':name,'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()} for name in
                        ('NativeWorkbench.exe','WorkbenchBridge.exe','workspace/desktop_host.py')]}
        package.core_inventory(value)
        value['files'].append({**value['files'][0],'path':'workspace/Desktop_Host.py'})
        with self.assertRaises(ValueError):package.core_inventory(value)

    def test_starter_stage_preserves_packs_and_archive_rejects_accidental_user_data(self):
        source=self.root/'source';base=self.root/'base';app=self.root/'starter'
        put(source,'build/desktop/DesktopWorkbench.exe',b'new-ui')
        put(source,'build/desktop/WorkbenchBridge.exe',b'new-bridge')
        put(source,'LICENSE',b'core-license')
        for name in package.NATIVE_NOTICE_FILES:put(source,'desktop/licenses/'+name,('native-notice-'+name).encode())
        for name in (*package.RUNTIME_MODULES,*package.RUNTIME_METADATA):put(source,'workspace/'+name,b'fixture module')
        put(source,'workspace/release-split/README.txt',b'starter instructions')
        put(source,'examples/starter/reference.fa',b'>starter\nACGT\n')
        put(base,'runtime/python/python.exe',b'private-runtime')
        for folder in package.STARTER:
            identity,version=folder.rsplit('-',1);fake_pack(base/'packs'/folder,identity,version)
        old={'version':'0.5.4','files':[package.item(p,p.relative_to(base).as_posix()) for p in package.files(base)]}
        put(base,'manifest.json',json.dumps(old).encode())
        artifact={'file':'source.zip','bytes':1,'sha256':hashlib.sha256(b'x').hexdigest(),'packCompanions':[]}
        with mock.patch.object(package,'SOURCE',source):package.stage(base,app,artifact)
        result=json.loads((app/'manifest.json').read_text())
        self.assertTrue(all(not i['path'].startswith('packs/') for i in result['files']))
        indexed={i['path']:i for i in result['files']}
        for name in package.NATIVE_NOTICE_FILES:
            path='runtime/licenses/native/'+name
            self.assertEqual((app/path).read_bytes(),(source/'desktop/licenses'/name).read_bytes())
            self.assertEqual(indexed[path]['sha256'],hashlib.sha256((app/path).read_bytes()).hexdigest())
        for folder in package.STARTER:
            self.assertEqual((base/'packs'/folder/'pack.ini').read_bytes(),(app/'packs'/folder/'pack.ini').read_bytes())
        output=self.root/'starter.zip';package.starter_archive(app,output)
        with zipfile.ZipFile(output) as zipped:
            self.assertIn('native-workbench/SOURCE-AVAILABILITY.json',zipped.namelist())
            for name in package.NATIVE_NOTICE_FILES:self.assertIn('native-workbench/runtime/licenses/native/'+name,zipped.namelist())
            self.assertEqual(len([n for n in zipped.namelist() if n.endswith('/pack.ini')]),3)
        put(app,'results/private-patient-data.txt',b'never release this')
        with self.assertRaises(ValueError):package.starter_archive(app,self.root/'rejected.zip')
        self.assertFalse((self.root/'rejected.zip').exists())


if __name__=='__main__':unittest.main()
