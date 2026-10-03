"""Core-update transaction tests with deliberately synthetic small installations."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import apply_core_update as update
import make_core_update as builder


def put(root,name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path


def manifest(root,version,content,core=True):
    value={'schema_version':2 if core else 1,'version':version,'interface':'native-win32',
           'requires_browser':False,'transport':'anonymous-pipes','manifest_includes_itself':False,
           'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(content.items())]}
    if core:value.update(ownership='core',pack_management='independent')
    put(root,'manifest.json',(json.dumps(value,indent=2)+'\n').encode());return value


class CoreUpdate(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.parent=Path(self.temp.name)
        self.base=self.parent/'app';self.target=self.parent/'target';self.output=self.parent/'updater'
        self.old={'NativeWorkbench.exe':b'old-ui','WorkbenchBridge.exe':b'bridge',
                  'workspace/desktop_host.py':b'old-host','workspace/legacy.py':b'old-unmanaged',
                  'packs/optional-1.0.0/bin/tool.exe':b'science','source/original.zip':b'original-source',
                  'validation/original.json':b'original-evidence'}
        self.new={'NativeWorkbench.exe':b'new-ui','WorkbenchBridge.exe':b'bridge',
                  'workspace/desktop_host.py':b'new-host','workspace/pack_manager.py':b'new-manager'}
        for name,data in self.old.items():put(self.base,name,data)
        for name,data in self.new.items():put(self.target,name,data)
        manifest(self.base,'0.5.4',self.old,False);manifest(self.target,'0.6.0',self.new)
        put(self.base,'user-data/settings.json',b'personal-settings');put(self.base,'results/result.txt',b'personal-result')
        self.old_manifest=(self.base/'manifest.json').read_bytes()
        builder.make(self.base,self.target,self.output)
        self.update=self.output/'update'

    def tearDown(self):self.temp.cleanup()

    def recipe(self):return json.loads((self.update/'update-manifest.json').read_text())

    def write_recipe(self,value):put(self.update,'update-manifest.json',json.dumps(value).encode())

    def assert_original_core(self):
        for name in ('NativeWorkbench.exe','WorkbenchBridge.exe','workspace/desktop_host.py'):
            self.assertEqual((self.base/name).read_bytes(),self.old[name])
        self.assertEqual((self.base/'manifest.json').read_bytes(),self.old_manifest)

    def assert_personal(self):
        self.assertEqual((self.base/'user-data/settings.json').read_bytes(),b'personal-settings')
        self.assertEqual((self.base/'results/result.txt').read_bytes(),b'personal-result')

    def test_migration_preserves_packs_source_evidence_and_unknown_files(self):
        put(self.base,'personal-notes.txt',b'notes')
        result=update.apply(self.base,self.update)
        self.assertEqual(result['status'],'installed');self.assertTrue(result['migration'])
        for name,data in self.new.items():self.assertEqual((self.base/name).read_bytes(),data)
        for name,data in self.old.items():
            if name not in self.new:self.assertEqual((self.base/name).read_bytes(),data)
        self.assertEqual((self.base/'personal-notes.txt').read_bytes(),b'notes');self.assert_personal()
        self.assertEqual((Path(result['backup'])/'manifest.json').read_bytes(),self.old_manifest)

    def test_modified_or_removed_optional_pack_and_source_do_not_gate_core_update(self):
        (self.base/'packs/optional-1.0.0/bin/tool.exe').unlink()
        put(self.base,'source/original.zip',b'locally-managed-source')
        self.assertEqual(update.apply(self.base,self.update)['status'],'installed')
        self.assertFalse((self.base/'packs/optional-1.0.0/bin/tool.exe').exists())
        self.assertEqual((self.base/'source/original.zip').read_bytes(),b'locally-managed-source')

    def test_repeat_is_idempotent_despite_unrelated_packs(self):
        update.apply(self.base,self.update);put(self.base,'packs/new/pack.ini',b'new-independent-pack')
        self.assertEqual(update.apply(self.base,self.update)['status'],'already-installed')

    def test_changed_core_rejected_before_update_area_created(self):
        put(self.base,'NativeWorkbench.exe',b'personal-ui')
        with self.assertRaises(ValueError):update.apply(self.base,self.update)
        self.assertFalse((self.base/'updates').exists());self.assert_personal()

    def test_unknown_existing_new_destination_preserved(self):
        put(self.base,'workspace/pack_manager.py',b'personal-module')
        with self.assertRaises(ValueError):update.apply(self.base,self.update)
        self.assertEqual((self.base/'workspace/pack_manager.py').read_bytes(),b'personal-module')
        self.assert_original_core()

    def test_corrupted_download_rolls_back_without_touching_packs(self):
        recipe=self.recipe();put(self.update,'blobs/'+recipe['operations'][0]['blob'],b'corrupt')
        with self.assertRaises(RuntimeError):update.apply(self.base,self.update)
        self.assert_original_core();self.assert_personal()

    def test_midcommit_error_restores_baseline_and_unknown_files(self):
        original_replace=update.os.replace;failed=False
        def replace(source,destination):
            nonlocal failed
            if not failed and Path(destination)==self.base/'workspace/desktop_host.py' and 'stage' in Path(source).parts:
                failed=True;raise OSError('injected commit failure')
            return original_replace(source,destination)
        with mock.patch.object(update.os,'replace',side_effect=replace):
            with self.assertRaises(RuntimeError):update.apply(self.base,self.update)
        self.assertTrue(failed);self.assert_original_core();self.assert_personal()
        report=next((self.base/'updates').glob('*/update-result.json'))
        self.assertTrue(json.loads(report.read_text())['baseline_restored'])

    def test_pack_or_data_destinations_rejected_by_manifest(self):
        for name in ('packs/tool.exe','user-data/settings.json','results/result.txt','source/archive.zip',
                     'validation/report.json','workspace/../packs/evil.exe','workspace/CON.txt'):
            value=json.loads((self.target/'manifest.json').read_text())
            value['files'].append({'path':name,'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()})
            with self.subTest(name=name),self.assertRaises(ValueError):update.core_inventory(value)

    def test_extra_or_incomplete_operations_rejected(self):
        recipe=self.recipe();recipe['operations'].pop();self.write_recipe(recipe)
        with self.assertRaises(ValueError):update.apply(self.base,self.update)
        self.assert_original_core()

    def test_migration_cannot_delete_legacy_noncore_files(self):
        recipe=self.recipe();recipe['obsolete']=['packs/optional-1.0.0/bin/tool.exe'];self.write_recipe(recipe)
        with self.assertRaises(ValueError):update.apply(self.base,self.update)
        self.assert_original_core()

    def test_lock_prevents_concurrent_update(self):
        with update.update_lock(self.base):
            with self.assertRaises(ValueError):update.apply(self.base,self.update)
        self.assert_original_core()

    def test_linked_destination_or_root_rejected(self):
        external=self.parent/'elsewhere';external.mkdir()
        (self.base/'workspace/pack_manager.py').symlink_to(external/'missing')
        with self.assertRaises(ValueError):update.apply(self.base,self.update)
        (self.base/'workspace/pack_manager.py').unlink()
        linked=self.parent/'linked-app';linked.symlink_to(self.base,target_is_directory=True)
        with self.assertRaises(ValueError):update.apply(linked,self.update)
        self.assert_original_core()

    def test_future_core_update_retires_only_owned_files(self):
        update.apply(self.base,self.update)
        future=self.parent/'future';content={**self.new,'NativeWorkbench.exe':b'future-ui'}
        del content['workspace/pack_manager.py']
        for name,data in content.items():put(future,name,data)
        manifest(future,'0.6.1',content)
        output=self.parent/'future-update';builder.make(self.base,future,output)
        result=update.apply(self.base,output/'update')
        self.assertFalse(result['migration']);self.assertEqual(result['removed_files'],1)
        self.assertFalse((self.base/'workspace/pack_manager.py').exists())
        self.assertTrue((self.base/'workspace/legacy.py').exists())
        self.assertTrue((self.base/'packs/optional-1.0.0/bin/tool.exe').exists());self.assert_personal()

    def test_native_updater_bundles_independent_runtime_for_runtime_replacements(self):
        content={**self.new,'runtime/python/python.exe':b'new-private-interpreter',
                 'runtime/python/python313.dll':b'new-private-library','runtime/python/LICENSE.txt':b'python-notices',
                 'LICENSE':b'application-license'}
        content.update({'runtime/licenses/native/'+name:('native-license-'+name).encode() for name in update.NATIVE_NOTICE_FILES})
        for name,data in content.items():put(self.target,name,data)
        manifest(self.target,'0.6.0',content)
        output=self.parent/'with-runtime';launcher=put(self.parent,'UpdateWorkbench.exe',b'synthetic-launcher')
        builder.make(self.base,self.target,output,launcher)
        self.assertEqual((output/'runtime/python/python.exe').read_bytes(),b'new-private-interpreter')
        self.assertEqual((output/'runtime/python/python313.dll').read_bytes(),b'new-private-library')
        self.assertEqual((output/'LICENSE').read_bytes(),b'application-license')
        for name in update.NATIVE_NOTICE_FILES:
            path='runtime/licenses/native/'+name
            self.assertEqual((output/path).read_bytes(),content[path])
        inventory=json.loads((output/'update-inventory.json').read_text())
        self.assertTrue(any(i['path']=='runtime/python/LICENSE.txt' for i in inventory['files']))
        indexed={i['path']:i for i in inventory['files']}
        for path in ['LICENSE',*('runtime/licenses/native/'+name for name in update.NATIVE_NOTICE_FILES)]:
            self.assertEqual(indexed[path]['sha256'],hashlib.sha256(content[path]).hexdigest())
        update.apply(self.base,output/'update')
        self.assertEqual((self.base/'runtime/python/python.exe').read_bytes(),b'new-private-interpreter')
        self.assertEqual((output/'runtime/python/python.exe').read_bytes(),b'new-private-interpreter')


if __name__=='__main__':unittest.main()
