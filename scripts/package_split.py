#!/usr/bin/env python3
"""Package the 0.6 core/starter release and independently installable tool packs.

No frozen input is modified. Source delivery is a separate, hash-pinned companion
with the exact legacy source archive and explicit pack-source recovery references.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

sys.dont_write_bytecode=True
SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE/'workspace'))
sys.path.insert(0,str(SOURCE/'scripts'))
from catalog import load_pack
from apply_core_update import NATIVE_NOTICE_FILES, core_inventory, core_path, ordinary_root
from apply_desktop_update import digest, inside, read_json, require, sha, verify

VERSION='0.6.0'
STARTER=('align-0.4.0','bam-0.4.0','variants-0.4.0')
RUNTIME_MODULES=('app_version.py','catalog.py','engine.py','example.py','desktop_host.py','desktop_model.py',
                 'service.py','verify_installation.py','pack_checks.py','pack_manager.py',
                 'pack_security.py','core_checks.py')
RUNTIME_METADATA=('starter-check-profile.json',)
FIXED_DATE=(2026,10,3,0,0,0)


def item(path,relative):
    return {'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)}


def files(root):
    root=ordinary_root(root);result=[]
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and not (hasattr(path,'is_junction') and path.is_junction()),
                'Release inputs cannot contain links: '+str(path))
        if path.is_file():result.append(path)
    return result


def copy_tree(source,destination):
    for path in files(source):
        target=destination/path.relative_to(source)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)


def _write_member(archive,path,name,stored=False):
    info=zipfile.ZipInfo(name,FIXED_DATE)
    info.compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    info.external_attr=(0o100644<<16)
    with path.open('rb') as source,archive.open(info,'w',force_zip64=True) as destination:
        shutil.copyfileobj(source,destination,1024*1024)


def _archive(output,members,metadata=()):
    output=Path(output).absolute();require(not output.exists(),'Release archive already exists: '+str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    partial=output.with_name(output.name+'.partial');require(not partial.exists(),'Partial release archive already exists')
    with zipfile.ZipFile(partial,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as zipped:
        for path,name,stored in members:_write_member(zipped,path,name,stored)
        for name,value in metadata:
            info=zipfile.ZipInfo(name,FIXED_DATE);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100644<<16)
            zipped.writestr(info,json.dumps(value,indent=2)+'\n')
    with zipfile.ZipFile(partial) as zipped:require(zipped.testzip() is None,'Release archive CRC failure')
    os.replace(partial,output)
    return {'file':output.name,'bytes':output.stat().st_size,'sha256':sha(output)}


def pack_inventory(folder):
    folder=ordinary_root(folder);pack=load_pack(folder/'pack.ini')
    declared={'pack.ini','pack-readme.md','pack-readme.txt','readme.txt'}
    for entry in [*pack['tools'].values(),*pack['assets'].values()]:
        path=inside(folder,entry['path']);verify(path,entry['sha256'])
        require(path.stat().st_size<=512*1024*1024,'Runtime file exceeds pack import limit')
        declared.add(entry['path'].lower())
    members=files(folder)
    require(len(list(folder.rglob('*')))<=2000,'Pack exceeds file/folder count limit')
    total=0;inventory=[]
    for path in members:
        relative=path.relative_to(folder).as_posix();lower=relative.lower()
        require(lower in declared or lower.startswith('licenses/'),'Undeclared pack runtime file: '+relative)
        size=path.stat().st_size;total+=size
        inventory.append({'path':relative,'size':size,'sha256':sha(path)})
    require(total<=1024*1024*1024,'Pack exceeds 1 GiB expanded import limit')
    return pack,members,inventory


def build_pack(folder,output):
    folder=ordinary_root(folder);pack,members,inventory=pack_inventory(folder)
    envelope={'schema':1,'id':pack['id'],'version':pack['version'],'packApi':1,
              'minAppVersion':VERSION,'platform':'windows-x86_64',
              'manifestSha256':pack['manifestSha256'],'files':inventory}
    archive=_archive(output,[(p,'pack/'+p.relative_to(folder).as_posix(),False) for p in members],
                     [('workbench-pack.json',envelope)])
    return {'id':pack['id'],'name':pack['name'],'version':pack['version'],
            'description':pack['description'],'toolVersions':{key:value['version'] for key,value in pack['tools'].items()},
            'platform':'windows-x86_64','packApi':1,'minAppVersion':VERSION,
            'manifestSha256':pack['manifestSha256'],'size':archive['bytes'],
            'sha256':archive['sha256'],'file':archive['file'],'expandedBytes':sum(i['size'] for i in inventory)}


def source_companions(base):
    contents=read_json(base/'docs/SOURCE-CONTENTS-0.5.4.json')
    aliases=contents.get('restore_from_runtime')
    require(isinstance(aliases,list),'Legacy source recovery references are missing')
    companions={}
    for reference in aliases:
        runtime=reference['runtime_path'];parts=runtime.split('/')
        require(len(parts)>=4 and parts[0]=='packs' and parts[2]=='licenses','Unexpected source companion path')
        verify(inside(base,runtime),reference['sha256'],reference['bytes'])
        folder=parts[1]
        if folder not in companions:
            pack=load_pack(base/'packs'/folder/'pack.ini')
            companions[folder]={'id':pack['id'],'version':pack['version'],'manifestSha256':pack['manifestSha256'],
                                'file':'native-workbench-pack-'+pack['id']+'-'+pack['version']+'.zip'}
    return contents,list(companions.values())


def build_sources(base,output):
    base=ordinary_root(base)
    contents,companions=source_companions(base)
    legacy=base/'source/native-workbench-source.zip'
    manifest=read_json(base/'manifest.json')
    original=next(i for i in manifest['files'] if i['path']=='source/native-workbench-source.zip')
    verify(legacy,original['sha256'],original['bytes'])
    selected=[]
    roots=('desktop','workspace','scripts','tests','tools','src','include','platform_windows','pack-examples')
    excluded={'__pycache__','node_modules','.git','build','tmp'}
    suffixes={'.py','.cpp','.c','.h','.hpp','.sh','.cmd','.json','.ini','.md','.txt','.patch','.rc','.manifest',
              '.yml','.yaml','.toml','.svg','.ps1','.fa','.fasta','.fna','.fq','.fastq','.tsv','.csv','.bed','.vcf','.in'}
    for folder in roots:
        for path in files(SOURCE/folder):
            relative=path.relative_to(SOURCE)
            if set(relative.parts)&excluded or any(p.startswith('.') for p in relative.parts):continue
            if path.suffix.lower() not in suffixes and path.name not in {'LICENSE','NOTICE','COPYING','Makefile'}:continue
            selected.append((path,'current/'+relative.as_posix(),False))
    for name in ('LICENSE','build_variant.py','variant-protocol.txt','variant-provenance.json'):
        path=SOURCE/name
        if path.is_file():selected.append((path,'current/'+name,False))
    for path in sorted(SOURCE.glob('README*')):
        if path.is_file():selected.append((path,'current/'+path.name,False))
    for path in sorted((SOURCE/'docs').glob('*')):
        if path.is_file() and path.suffix.lower() in suffixes:selected.append((path,'current/docs/'+path.name,False))
    starter=SOURCE/'examples/starter'
    require(starter.is_dir(),'Create the starter scientific fixture before packaging source')
    selected.extend((p,'current/examples/starter/'+p.relative_to(starter).as_posix(),False) for p in files(starter))
    selected.append((legacy,'legacy/native-workbench-0.5.4-source.zip',True))
    current_inventory=[item(path,name) for path,name,_ in selected if name.startswith('current/')]
    recovery={'schema':1,'release':VERSION,'legacy_source':original,'pack_companions':companions,
              'instructions':'Extract legacy/native-workbench-0.5.4-source.zip into a separate legacy-source folder. Obtain the listed exact pack companions, place each ZIP pack/ tree at packs/<id>-<version>/ in a separate runtime root, and run legacy-source/native-workbench/scripts/restore_source_archives.py with that source root and runtime root. The current/ folder contains the actual 0.6 application/build/test sources, not the old versions.',
              'source_aliases':contents['restore_from_runtime'],'current_source_files':current_inventory}
    result=_archive(output,selected,[('SOURCE-RECOVERY.json',recovery),('legacy/SOURCE-CONTENTS-0.5.4.json',contents)])
    return {**result,'packCompanions':companions,'legacySourceSha256':original['sha256'],
            'legacySourceAliases':len(contents['restore_from_runtime'])}


def stage(base,app,source_artifact):
    base=ordinary_root(base);app=Path(app).absolute()
    require(not app.exists(),'Select an empty new application staging folder')
    require(not app.is_relative_to(base) and not base.is_relative_to(app),'Staging overlaps the frozen baseline')
    baseline=read_json(base/'manifest.json')
    require(baseline.get('version')=='0.5.4','Expected a frozen 0.5.4 baseline')
    from apply_desktop_update import inventory as release_inventory
    baseline_files=release_inventory(baseline)
    for prefix in ('runtime',*('packs/'+folder for folder in STARTER)):
        for path in files(base/prefix):
            name=path.relative_to(base).as_posix()
            require(name in baseline_files,'Uninventoried baseline file: '+name)
            entry=baseline_files[name];verify(path,entry['sha256'],entry['bytes'])
    require(isinstance(source_artifact,dict) and {'file','bytes','sha256','packCompanions'}<=set(source_artifact),
            'Build and pin the source companion before staging the starter')
    digest(source_artifact['sha256'])
    require(isinstance(source_artifact['file'],str) and Path(source_artifact['file']).name==source_artifact['file']
            and '/' not in source_artifact['file'] and '\\' not in source_artifact['file']
            and source_artifact['file'].endswith('.zip') and type(source_artifact['bytes']) is int
            and source_artifact['bytes']>0, 'Invalid source companion identity')
    app.mkdir(parents=True)
    for origin,name in ((SOURCE/'build/desktop/DesktopWorkbench.exe','NativeWorkbench.exe'),
                        (SOURCE/'build/desktop/WorkbenchBridge.exe','WorkbenchBridge.exe'),(SOURCE/'LICENSE','LICENSE')):
        require(origin.is_file(),'Build the required component first: '+str(origin));shutil.copy2(origin,app/name)
    copy_tree(base/'runtime',app/'runtime')
    native_notices=SOURCE/'desktop/licenses'
    require(all((native_notices/name).is_file() for name in NATIVE_NOTICE_FILES),
            'The native application license notices are incomplete')
    copy_tree(native_notices,app/'runtime/licenses/native')
    workspace=app/'workspace';workspace.mkdir()
    for name in (*RUNTIME_MODULES,*RUNTIME_METADATA):
        path=SOURCE/'workspace'/name;require(path.is_file(),'Missing core runtime component: '+name)
        shutil.copy2(path,workspace/name)
    sources=SOURCE/'workspace/catalog-sources.json'
    if sources.exists():shutil.copy2(sources,workspace/sources.name)
    copy_tree(SOURCE/'workspace/release-split',app)
    copy_tree(SOURCE/'examples/starter',app/'examples/starter')
    (app/'packs').mkdir();starter=[]
    for folder in STARTER:
        original=base/'packs'/folder;pack,_,_=pack_inventory(original)
        copy_tree(original,app/'packs'/folder)
        copied=load_pack(app/'packs'/folder/'pack.ini')
        require(copied['manifestSha256']==pack['manifestSha256'],'Starter pack manifest changed')
        starter.append({'id':pack['id'],'version':pack['version'],'folder':'packs/'+folder,'manifestSha256':pack['manifestSha256']})
    availability={'schema':1,'applicationVersion':VERSION,'sourceArtifact':source_artifact,
                  'delivery':'Separate release asset, alongside application and tool pack ZIPs. Source recovery references require the exact listed companion packs. No network fetch occurs while running tools.',
                  'notices':'Application LICENSE, Python runtime LICENSE.txt, and native MinGW-w64, winpthreads and LLVM notices under runtime/licenses/native are installed. Each tool pack retains its complete license and corresponding-source tree.'}
    (app/'SOURCE-AVAILABILITY.json').write_text(json.dumps(availability,indent=2)+'\n',encoding='utf-8')
    inventory=[]
    for path in files(app):
        name=path.relative_to(app).as_posix()
        if name.startswith('packs/'):continue
        core_path(name);inventory.append(item(path,name))
    manifest={'schema_version':2,'version':VERSION,'ownership':'core','pack_management':'independent',
              'manifest_includes_itself':False,'platform':'windows-x86_64','interface':'native-win32',
              'transport':'anonymous-pipes','requires_browser':False,'network_listener':False,
              'native_windows_integration_tested':False,'starter_packs':starter,'files':inventory}
    core_inventory(manifest)
    (app/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return {'version':VERSION,'app_root':str(app),'core_files':len(inventory),'core_bytes':sum(i['bytes'] for i in inventory),
            'starter_packs':starter,'installed_bytes':sum(p.stat().st_size for p in files(app))}


def starter_archive(app,output):
    app=ordinary_root(app);manifest=read_json(app/'manifest.json')
    inventory=core_inventory(manifest)
    for name,entry in inventory.items():verify(inside(app,name),entry['sha256'],entry['bytes'])
    require({p.name for p in (app/'packs').iterdir()}==set(STARTER),'Starter pack inventory differs')
    expected=set(inventory)|{'manifest.json'}
    pins={entry['folder']:entry for entry in manifest.get('starter_packs',[])}
    for folder in STARTER:
        pack,members,_=pack_inventory(app/'packs'/folder)
        require('packs/'+folder in pins and pins['packs/'+folder]['manifestSha256']==pack['manifestSha256'],
                'Starter pack pin differs from release profile')
        expected.update(path.relative_to(app).as_posix() for path in members)
    members=files(app)
    require({p.relative_to(app).as_posix() for p in members}==expected,
            'Uninventoried files entered starter staging; user data cannot be included in a release')
    return _archive(output,[(p,'native-workbench/'+p.relative_to(app).as_posix(),False) for p in members])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('sources');command.add_argument('--base-root',type=Path,required=True);command.add_argument('--output',type=Path,required=True);command.add_argument('--metadata',type=Path,required=True)
    command=sub.add_parser('stage');command.add_argument('--base-root',type=Path,required=True);command.add_argument('--app-root',type=Path,required=True);command.add_argument('--source-metadata',type=Path,required=True)
    command=sub.add_parser('starter');command.add_argument('--app-root',type=Path,required=True);command.add_argument('--output',type=Path,required=True)
    command=sub.add_parser('pack');command.add_argument('--pack-root',type=Path,required=True);command.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='sources':
        require(not args.metadata.exists(),'Source metadata output already exists')
        result=build_sources(args.base_root,args.output)
        args.metadata.parent.mkdir(parents=True,exist_ok=True)
        args.metadata.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    elif args.command=='stage':result=stage(args.base_root,args.app_root,read_json(args.source_metadata))
    elif args.command=='starter':result=starter_archive(args.app_root,args.output)
    else:result=build_pack(args.pack_root,args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
