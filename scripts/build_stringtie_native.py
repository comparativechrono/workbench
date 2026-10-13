#!/usr/bin/env python3
"""Build pinned StringTie 3.0.3 with a narrow nonmodal Windows CLI boundary."""
import argparse, concurrent.futures, difflib, hashlib, json, os, re, shutil, struct, subprocess, tarfile, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='3.0.3-workbench1'
UPSTREAM_VERSION='3.0.3'
PATCH=ROOT/'tools/stringtie/workbench1.patch'
SOURCE_COMMIT='3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19'
SOURCE_NAME='stringtie-3.0.3.tar.gz'
SOURCE_SHA256='52a5d94b0e85404d740d2c7a0c7cc698d373a1b8888e9a2a395ae294032d95c0'
SOURCE_URL='https://codeload.github.com/gpertea/stringtie/tar.gz/'+SOURCE_COMMIT
SOURCES={SOURCE_NAME:(SOURCE_URL,SOURCE_SHA256),'zlib-1.3.2.tar.gz':('https://zlib.net/fossils/zlib-1.3.2.tar.gz','bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16'),'tre-0.9.0.tar.gz':('https://codeload.github.com/laurikari/tre/tar.gz/refs/tags/v0.9.0','5b7e5a730f041c6b0dab8f66576cda917577ec06bb393f156b169c51bca170d1')}
TC_NAME='llvm-mingw-20260922-ucrt-ubuntu-22.04-x86_64'
WINDOWS_STACK_RESERVE=8388608;WINDOWS_STACK_COMMIT=65536
Z_FILES='adler32 crc32 gzclose gzlib gzread gzwrite deflate infback inffast inflate inftrees trees zutil'.split()
CPP_FILES='gclib/GThreads.cpp gclib/GBase.cpp gclib/GArgs.cpp gclib/GStr.cpp gclib/GSam.cpp gclib/gdna.cpp gclib/codons.cpp gclib/GFastaIndex.cpp gclib/GFaSeqGet.cpp gclib/gff.cpp bundle.cpp rlink.cpp tablemaker.cpp tmerge.cpp stringtie.cpp'.split()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def extract(path,dest):
    with tarfile.open(path) as t:
        for m in t.getmembers():
            p=Path(m.name)
            if p.is_absolute() or '..' in p.parts or not(m.isfile() or m.isdir()):raise ValueError('Unsafe source member '+m.name)
            if m.isfile():
                target=dest/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(t.extractfile(m).read())
def apply_compatibility(source):
    """Windows diagnostics, GFF flag storage ABI, and the attested banner only."""
    originals={name:(source/name).read_text() for name in ('gclib/GBase.cpp','gclib/gff.h','stringtie.cpp')}
    base=originals['gclib/GBase.cpp'];start=base.index('  #ifdef _WIN32\n',base.index('void GError('));end=base.index('  #else\n',start)
    replacement="""  #ifdef _WIN32
    // Native Workbench CLI boundary: report fatal errors without a modal dialog.
    // Scientific processing is unchanged; preserve the upstream exit status.
    va_list arguments;
    va_start(arguments,format);
    vfprintf(stderr,format,arguments);
    va_end(arguments);
    fflush(stderr);
"""
    base=base[:start]+replacement+base[end:]
    start=base.index('  #ifdef _WIN32\n',base.index('void GMessage('));end=base.index('  #else\n',start)
    replacement="""  #ifdef _WIN32
    // Native Workbench CLI boundary: consume diagnostic arguments once.
    va_list arguments;
    va_start(arguments,format);
    vfprintf(stderr,format,arguments);
    va_end(arguments);
    fflush(stderr);
"""
    base=base[:start]+replacement+base[end:]
    header=originals['gclib/gff.h'];start=header.index('   union {',header.index('class GffObj:'));end=header.index('   //-- friends:',start)
    flags=header[start:end];assert flags.count('bool flag_')==17
    flags=flags.replace('bool flag_', 'unsigned int flag_')
    flags=flags.replace('      unsigned int flags;', '      // Workbench: one 32-bit storage unit also under the Windows bitfield ABI.\n      unsigned int flags;')
    header=header[:start]+flags+header[end:]
    modified={'gclib/GBase.cpp':base,'gclib/gff.h':header,'stringtie.cpp':originals['stringtie.cpp'].replace('#define VERSION "3.0.3"','#define VERSION "3.0.3-workbench1"')}
    patch=''.join(''.join(difflib.unified_diff(originals[name].splitlines(True),modified[name].splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name in originals)
    if patch!=PATCH.read_text():raise ValueError('Compatibility changes differ from the reviewed exact patch')
    for name,text in modified.items():(source/name).write_text(text)
    return sha(PATCH)
def flag_layout_probe(header):
    """Exercise the exact source union, not a separately maintained approximation."""
    start=header.index('   union {',header.index('class GffObj:'));end=header.index('   //-- friends:',start)
    union=header[start:end]
    fields=re.findall(r'(?:bool|unsigned int)\s+(\w+)\s*:\s*(\d+)',union)
    assert len(fields)==19 and sum(int(n) for _,n in fields)==29
    checks=[];offset=0
    for name,width in fields:
        value=(1<<int(width))-1
        checks.append(f'  value.flags=0; value.{name}={value}; if(value.flags != {value<<offset}u) return 3;')
        offset+=int(width)
    return ('#include <cstdio>\n#include <cstring>\nstruct Flags {\n'+union+'};\n'
        'static_assert(sizeof(Flags)==sizeof(unsigned int) && sizeof(Flags)==4, "GFF flags must occupy one 32-bit word");\n'
        'int main() {\n  Flags value; std::memset(&value, 0xA5, sizeof(value)); value.flags=0;\n'
        '  if('+ ' || '.join('value.'+name for name,_ in fields)+') return 2;\n'
        +'\n'.join(checks)+'\n'
        '  std::puts(R"({"success":true,"unionBytes":4,"poison":165,"fieldsChecked":19})");\n  return 0;\n}\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'build/stringtie-cache');p.add_argument('--build',type=Path);p.add_argument('--toolchain',type=Path,default=ROOT/'build/toolchains'/TC_NAME);p.add_argument('--fetch',action='store_true');p.add_argument('--linux',action='store_true');p.add_argument('--upstream',action='store_true');p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
    if a.upstream and not a.linux:raise ValueError('Pristine upstream reference requires --linux')
    cache=a.cache.resolve();cache.mkdir(parents=True,exist_ok=True);out=(a.build or ROOT/('build/stringtie-'+('reference-linux' if a.upstream else 'linux' if a.linux else 'windows'))).resolve();out.mkdir(parents=True,exist_ok=True)
    for name,(url,digest) in SOURCES.items():
        f=cache/name
        if not f.is_file() and a.fetch:f.write_bytes(urllib.request.urlopen(url,timeout=180).read())
        if not f.is_file() or sha(f)!=digest:raise ValueError('Missing/changed source; use --fetch: '+name)
    source_root=out/'source'
    if source_root.exists():shutil.rmtree(source_root)
    for name in SOURCES:extract(cache/name,source_root)
    src=source_root/('stringtie-'+SOURCE_COMMIT);ht=src/'htslib';z=source_root/'zlib-1.3.2';tre=source_root/'tre-0.9.0';config=out/'config';config.mkdir(exist_ok=True)
    patch_hash=None if a.upstream else apply_compatibility(src)
    # Generated configure equivalents. Optional
    # remote plugins and non-zlib CRAM codecs are outside the BAM-only operation.
    (config/'config.h').write_text(('#define HAVE_WINDOWS_H 1\n#define HAVE_IO_H 1\n' if not a.linux else '#define HAVE_DRAND48 1\n')+'#define HAVE_FSEEKO 1\n#define HAVE_FTELLO 1\n#define HAVE_GMTIME_R 1\n#define HAVE_DECL___CPUID_COUNT 1\n#define HAVE_DECL___GET_CPUID_MAX 1\n')
    (config/'version.h').write_text('#define HTS_VERSION_TEXT "1.21-stringtie-bundled"\n#define HTSCODECS_VERSION_TEXT "1.4.0-stringtie-bundled"\n')
    (config/'config_vars.h').write_text('#define HTS_CC "source-bound-build"\n#define HTS_CPPFLAGS ""\n#define HTS_CFLAGS "baseline x86-64"\n#define HTS_LDFLAGS ""\n#define HTS_LIBS "zlib; no remote plugins"\n')
    treconfig=out/'tre-config';treconfig.mkdir(exist_ok=True)
    shutil.copyfile(tre/'win32/config.h',treconfig/'config.h');shutil.copyfile(tre/'win32/tre-config.h',treconfig/'tre-config.h')
    if not a.linux:(config/'regex.h').write_text('#include "tre.h"\n#define regcomp tre_regcomp\n#define regexec tre_regexec\n#define regerror tre_regerror\n#define regfree tre_regfree\n')
    elif (config/'regex.h').exists():(config/'regex.h').unlink()
    tc=a.toolchain.resolve();cc=shutil.which('gcc') if a.linux else str(tc/'bin/x86_64-w64-mingw32-clang');cxx=shutil.which('g++') if a.linux else str(tc/'bin/x86_64-w64-mingw32-clang++');env=dict(os.environ,LD_LIBRARY_PATH=str(tc/'lib'),TMPDIR=str(out/'tmp'));(out/'tmp').mkdir(exist_ok=True)
    make=(ht/'Makefile').read_text().replace('\\\n',' ');objs=re.search(r'^LIBHTS_OBJS\s*=\s*(.+)$',make,re.M).group(1).split();hfiles=[ht/(v[:-2]+'.c') for v in objs if v.endswith('.o')];hm=(ht/'htscodecs_bundled.mk').read_text().replace('\\\n',' ');hfiles += [ht/v.replace('$(HTSPREFIX)','') for v in re.search(r'^HTSCODECS_SOURCES\s*=\s*(.+)$',hm,re.M).group(1).split()]
    zfiles=[z/(n+'.c') for n in Z_FILES];tfiles=[] if a.linux else sorted((tre/'lib').glob('*.c'));cppfiles=[src/v for v in CPP_FILES];files=hfiles+zfiles+tfiles+cppfiles
    flags=['-O2','-DNDEBUG','-D_FILE_OFFSET_BITS=64','-fno-strict-aliasing','-fno-fast-math','-march=x86-64','-mtune=generic','-mno-avx','-mno-avx2','-include','stdint.h'];includes=['-I'+str(v) for v in [src,src/'gclib',ht,z,config]]+([] if a.linux else ['-I'+str(treconfig),'-I'+str(tre/'lib'),'-I'+str(tre/'local_includes')]);commands=[]
    def compile_one(f):
        obj=out/(f.relative_to(source_root).as_posix().replace('/','_')+'.o');cmd=[cxx if f.suffix=='.cpp' else cc,*flags,*includes,'-c',str(f),'-o',str(obj)]
        if f in tfiles:cmd[1:1]=['-I'+str(treconfig),'-I'+str(tre/'lib'),'-DHAVE_CONFIG_H']
        if f.suffix=='.cpp':cmd+=['-std=c++11','-fsigned-char','-fno-exceptions','-fno-rtti']
        r=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/(obj.stem+'.compile.log')).write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(f.name+'\n'+r.stderr)
        return obj,cmd
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,a.jobs)) as pool:built=list(pool.map(compile_one,files))
    commands.extend(x[1] for x in built);suffix='' if a.linux else '.exe';link=['-pthread','-lm'] if a.linux else ['-static','-pthread','-lws2_32','-Wl,--no-insert-timestamp','-Xlinker','--stack','-Xlinker',str(WINDOWS_STACK_RESERVE)+','+str(WINDOWS_STACK_COMMIT)];binary=out/('stringtie'+suffix)
    cmd=[cxx,*[str(x[0]) for x in built],*link,'-o',str(binary)];subprocess.run(cmd,env=env,check=True);commands.append(cmd);binaries=[binary]
    guard=ROOT/'tools/stringtie/guard.cpp'
    if not a.upstream:
        helper=out/('stringtie-guard'+suffix);cmd=[cxx,'-O2','-std=c++17','-Wall','-Wextra','-Werror','-march=x86-64','-mno-avx','-mno-avx2',*includes,str(guard),*[str(obj) for (f,(obj,_)) in zip(files,built) if f in hfiles+zfiles+tfiles],*link,'-o',str(helper)];subprocess.run(cmd,env=env,check=True);commands.append(cmd);binaries.append(helper)
    record={'schema':1,'tool':'stringtie','version':UPSTREAM_VERSION if a.upstream else VERSION,'upstreamVersion':UPSTREAM_VERSION,'sourceCommit':SOURCE_COMMIT,'upstreamCommit':SOURCE_COMMIT,'sources':{k:{'url':v[0],'sha256':v[1]} for k,v in SOURCES.items()},'platform':'linux-x86_64' if a.linux else 'windows-x86_64','cpuBaseline':'x86-64; no AVX/AVX2 or SSE4 requirement','threadsExposed':1,'upstreamScientificAlgorithmsUnmodified':True,'upstreamSourceUnmodified':a.upstream,'patchSha256':patch_hash,'executionTestsPerformedByBuild':bool(a.linux and not a.upstream),'scientificExecutionTestsPerformedByBuild':False,'builderSha256':sha(Path(__file__)),'compiler':subprocess.check_output([cc,'--version'],env=env,text=True).splitlines()[0],'compilerSha256':sha(cc),'commands':commands,'files':{},'generatedConfiguration':{f.relative_to(out).as_posix():sha(f) for folder in [config,treconfig] for f in folder.iterdir()},'buildRoute':'Direct upstream object list, native GThreads Windows route, forced standard stdint.h include, BAM-only HTSlib zlib configuration, TRE POSIX regex symbols; '+('pristine source reference, no compatibility patch' if a.upstream else 'workbench1.patch makes Windows GError nonmodal, consumes GError/GMessage diagnostic arguments once, restores one 32-bit GFF flag storage unit under the Windows ABI, and attests the build version; scientific algorithms unchanged')}
    if not a.upstream:record.update(guardSourceSha256=sha(guard),guardCompilerSha256=sha(cxx))
    if not a.upstream:
        probe_source=out/'flag-layout-check.cpp';probe=out/('flag-layout-check'+suffix)
        probe_source.write_text(flag_layout_probe((src/'gclib/gff.h').read_text()))
        probe_cmd=[cxx,'-O2','-std=c++11',str(probe_source),*link,'-o',str(probe)]
        subprocess.run(probe_cmd,env=env,check=True)
        probe_record={'schema':1,'sourceSha256':sha(probe_source),'executableSha256':sha(probe),'patchedHeaderSha256':sha(src/'gclib/gff.h'),'builderSha256':sha(Path(__file__)),'compilerSha256':sha(cxx),'patchSha256':patch_hash,'command':probe_cmd,'nativeExecutionPerformed':a.linux}
        if a.linux:
            executed=subprocess.run([str(probe)],text=True,capture_output=True,check=True)
            probe_record['result']=json.loads(executed.stdout)
        (out/'flag-layout-check.json').write_text(json.dumps(probe_record,indent=2)+'\n')
        record['flagLayoutCheck']=probe_record

    for f in binaries:
        info={'bytes':f.stat().st_size,'sha256':sha(f)}
        if not a.linux:
            b=f.read_bytes();off=struct.unpack_from('<I',b,60)[0];reserve,commit=struct.unpack_from('<QQ',b,off+24+72);info.update(stackReserveBytes=reserve,stackCommitBytes=commit)
            if b[:2]!=b'MZ' or (reserve,commit)!=(WINDOWS_STACK_RESERVE,WINDOWS_STACK_COMMIT):raise ValueError('Unexpected PE/stack configuration')
            imports=subprocess.check_output([str(tc/'bin/llvm-readobj'),'--coff-imports',str(f)],env=env,text=True);(out/(f.stem+'.imports.txt')).write_text(imports);info['imports']=re.findall(r'^\s*Name:\s*(\S+)\s*$',imports,re.M)
            if not info['imports'] or any(v.lower() not in {'kernel32.dll','msvcrt.dll','ucrtbase.dll','advapi32.dll','user32.dll','ws2_32.dll'} and not v.lower().startswith('api-ms-win-crt-') for v in info['imports']):raise ValueError('Unexpected runtime dependency')
        record['files'][f.name]=info
    notices=out/'compiler-notices';notices.mkdir(exist_ok=True)
    if not a.linux:
        for f in [tc/'LICENSE.TXT',*sorted((tc/'x86_64-w64-mingw32/share/mingw32').glob('COPYING*'))]:shutil.copyfile(f,notices/f.name)
    record['compilerNotices']={f.name:sha(f) for f in notices.iterdir()};(out/'build.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'build':str(out),'files':record['files']},indent=2))
if __name__=='__main__':main()
