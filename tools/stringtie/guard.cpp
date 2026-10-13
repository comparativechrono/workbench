// SPDX-License-Identifier: MIT
// Bounded BAM/GTF I/O and subprocess boundary. StringTie performs assembly and estimation.
#include <algorithm>
#include <htslib/sam.h>
#include <htslib/bgzf.h>
#include <regex>
#include <cctype>
#include <cstdint>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;
static void need(bool ok, const std::string& message) {
    if (!ok) throw std::runtime_error(message);
}
static std::string json_quote(const std::string& value) {
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { result += '\\'; result += char(c); }
        else if (c == '\n') result += "\\n";
        else if (c == '\r') result += "\\r";
        else if (c == '\t') result += "\\t";
        else { need(c >= 32 && c < 127, "ASCII text required"); result += char(c); }
    }
    return result + '"';
}
static void local(const std::string& path) {
    need(!path.empty() && path != "-" && path.find("://") == std::string::npos,
         "Select explicit local paths, not a URL or standard input");
    for (unsigned char c : path)
        need(c >= 32 && c < 127,
             "ASCII installation, input and results paths required; spaces are supported");
}
static std::string read(const fs::path& path, size_t maximum) {
    need(fs::is_regular_file(path), "Cannot read file: " + path.string());
    need(fs::file_size(path) <= maximum, "File exceeds bounded pack size limit: " + path.string());
    std::ifstream input(path, std::ios::binary);
    need(bool(input), "Cannot read file: " + path.string());
    return std::string(std::istreambuf_iterator<char>(input), {});
}
static void write(const fs::path& path, const std::string& content) {
    need(!fs::exists(path), "Refusing to replace existing output: " + path.string());
    std::ofstream output(path, std::ios::binary);
    need(bool(output), "Cannot create output: " + path.string());
    output << content;
    output.close();
    need(bool(output), "Output write failed: " + path.string());
}
static int child(const std::vector<std::string>& arguments, const fs::path& log) {
#ifdef _WIN32
    std::string command;
    for (const auto& arg : arguments) {
        if (!command.empty()) command += ' ';
        command += '"';
        size_t slashes = 0;
        for (char c : arg) {
            if (c == '\\') { ++slashes; continue; }
            if (c == '"') { command.append(slashes * 2 + 1, '\\'); command += '"'; }
            else { command.append(slashes, '\\'); command += c; }
            slashes = 0;
        }
        command.append(slashes * 2, '\\');
        command += '"';
    }
    SECURITY_ATTRIBUTES security{sizeof(security), nullptr, TRUE};
    HANDLE output = CreateFileA(log.string().c_str(), GENERIC_WRITE, FILE_SHARE_READ,
                                &security, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    need(output != INVALID_HANDLE_VALUE, "Cannot create StringTie execution log");
    HANDLE input = CreateFileA("NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                               &security, OPEN_EXISTING, 0, nullptr);
    if (input == INVALID_HANDLE_VALUE) { CloseHandle(output); need(false, "Cannot open null input for StringTie"); }
    STARTUPINFOA startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdOutput = startup.hStdError = output;
    startup.hStdInput = input;
    PROCESS_INFORMATION process{};
    BOOL started = CreateProcessA(arguments[0].c_str(), command.data(), nullptr, nullptr,
                                   TRUE, CREATE_NO_WINDOW, nullptr, nullptr, &startup, &process);
    CloseHandle(output);
    CloseHandle(input);
    need(started, "Cannot start bundled StringTie executable; reinstall this pack");
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return int(code);
#else
    pid_t process = fork();
    need(process >= 0, "Cannot start StringTie subprocess");
    if (process == 0) {
        int output = open(log.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        int input = open("/dev/null", O_RDONLY);
        if (output < 0 || input < 0) _exit(126);
        dup2(output, STDOUT_FILENO);
        dup2(output, STDERR_FILENO);
        dup2(input, STDIN_FILENO);
        close(output);
        close(input);
        std::vector<char*> argv;
        for (const auto& arg : arguments) argv.push_back(const_cast<char*>(arg.c_str()));
        argv.push_back(nullptr);
        execv(argv[0], argv.data());
        _exit(127);
    }
    int status = 0;
    need(waitpid(process, &status, 0) == process, "Cannot wait for StringTie subprocess");
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
#endif
}
static double decimal(const std::string& s,double lo,double hi,const std::string& name) {
    need(!s.empty() && s.size()<24 && s.find_first_not_of("0123456789.")==std::string::npos,name+": enter a finite decimal without units");
    size_t used=0;double x=std::stod(s,&used);need(used==s.size() && std::isfinite(x) && x>=lo && x<=hi,name+": value outside supported bounds");return x;
}
static std::vector<std::string> split(const std::string& s,char sep) {std::vector<std::string> v;std::istringstream in(s);std::string x;while(std::getline(in,x,sep))v.push_back(x);return v;}
static std::string attribute(const std::string& s,const std::string& name) {
    std::regex re("(^|;)\\s*"+name+"\\s+\"([^\"]+)\"\\s*(?=;|$)");std::sregex_iterator begin(s.begin(),s.end(),re),end;need(begin!=end,"GTF requires quoted "+name);auto found=*begin;need(++begin==end,"GTF repeats "+name);return found[2];
}
struct Evidence {uint64_t records=0,mapped=0,spliced=0,exons=0,transcripts=0;std::map<std::string,int64_t> refs;std::set<std::string> samples;};
static Evidence validate(const fs::path& bam,const fs::path& gtf) {
    need(fs::is_regular_file(bam) && fs::file_size(bam)<=4294967296ULL,"Select one local BAM no larger than 4 GiB");
    samFile* f=sam_open(bam.string().c_str(),"rb");need(f,"Cannot open BAM");
    need(hts_get_format(f)->format==::bam,"Binary BGZF BAM required; SAM and CRAM are not supported");
    need(f->is_bgzf && bgzf_check_EOF(f->fp.bgzf)==1,"BAM BGZF end marker missing: regenerate or finish writing this BAM");
    sam_hdr_t* h=sam_hdr_read(f);need(h,"Cannot read BAM header");
    std::string header=sam_hdr_str(h);bool sorted=false;Evidence e;
    for(auto line:split(header,'\n')) {auto cols=split(line,'\t');if(cols.empty())continue;if(cols[0]=="@HD")for(auto c:cols)if(c=="SO:coordinate")sorted=true;
        if(cols[0]=="@RG")for(auto c:cols)if(c.rfind("SM:",0)==0)e.samples.insert(c.substr(3));}
    need(sorted,"BAM must declare SO:coordinate and be actually coordinate sorted; sort RNA alignments before StringTie");need(e.samples.size()<=1,"Multiple RG sample names found; run one biological sample at a time");
    need(sam_hdr_nref(h)>0 && sam_hdr_nref(h)<=1000000,"Invalid or oversized BAM reference dictionary");
    for(int i=0;i<sam_hdr_nref(h);++i){std::string name=sam_hdr_tid2name(h,i);need(name.size()<=199 && name.find_first_of("\t\r\n ")==std::string::npos,"Unsupported BAM contig name");need(e.refs.emplace(name,sam_hdr_tid2len(h,i)).second,"Duplicate BAM contig name");}
    bam1_t* b=bam_init1();int result=0,lasttid=-1;hts_pos_t lastpos=-1;bool unplaced=false;int pairing=-1;
    while((result=sam_read1(f,h,b))>=0) {
        ++e.records;need(e.records<=10000000,"BAM exceeds this pack's 10 million alignment-record bound");const auto& c=b->core;
        need(c.l_qseq>=0 && c.l_qseq<=1000,"Short-read operation supports at most 1000 sequence bases per alignment");
        need(!(c.flag&BAM_FSUPPLEMENTARY),"Supplementary alignments are not supported; supply a short-read RNA BAM without flag 0x800");
        if(c.tid<0){need(c.tid==-1 && (c.flag&BAM_FUNMAP),"Unplaced BAM record must have tid -1 and unmapped flag");unplaced=true;continue;}need(!unplaced && c.tid>=lasttid && (c.tid!=lasttid || c.pos>=lastpos),"BAM records are not coordinate sorted; sort the RNA BAM before running");lasttid=c.tid;lastpos=c.pos;
        need(c.tid<sam_hdr_nref(h) && c.pos>=0,"Invalid BAM reference or alignment coordinate");
        if(c.flag&BAM_FUNMAP)continue;
        ++e.mapped;
        int paired=bool(c.flag&BAM_FPAIRED);need(pairing==-1 || pairing==paired,"Mixed single-end and paired-end records are not supported");pairing=paired;
        if(paired)need(bool(c.flag&BAM_FREAD1)!=bool(c.flag&BAM_FREAD2),"Paired alignments must identify exactly read 1 or read 2");
        need(c.l_qseq>=1 && c.n_cigar>0,"Mapped BAM record lacks sequence or CIGAR");auto cigar=bam_get_cigar(b);int64_t q=0,r=0;bool splice=false;
        for(uint32_t i=0;i<c.n_cigar;++i){auto op=bam_cigar_op(cigar[i]);auto len=bam_cigar_oplen(cigar[i]);need(len>0 && op<=BAM_CDIFF,"Invalid/unsupported CIGAR operation");if(bam_cigar_type(op)&1)q+=len;if(bam_cigar_type(op)&2)r+=len;if(op==BAM_CREF_SKIP)splice=true;}
        need(q==c.l_qseq && r>0 && c.pos+r<=sam_hdr_tid2len(h,c.tid),"BAM CIGAR sequence/reference bounds disagree");
        uint8_t* nh=bam_aux_get(b,"NH");need(nh && std::string("cCsSiI").find(char(*nh))!=std::string::npos && bam_aux2i(nh)>=1 && bam_aux2i(nh)<=1000000,"Mapped RNA alignments require a positive integer NH tag; rerun HISAT2/STAR with alignment tags retained");
        if(splice){++e.spliced;uint8_t* xs=bam_aux_get(b,"XS");need(xs && *xs=='A' && (bam_aux2A(xs)=='+' || bam_aux2A(xs)=='-'),"Spliced RNA alignments require XS:A:+ or XS:A:-; use HISAT2 --dta, or STAR --outSAMstrandField intronMotif");}
    }
    bam_destroy1(b);sam_hdr_destroy(h);need(sam_close(f)==0 && result==-1,"Damaged/truncated BAM records");
    std::string data=read(gtf,268435456);need(data.find('\0')==std::string::npos,"Uncompressed GTF text required");
    struct Tx {std::string chr,gene,strand;std::vector<std::pair<int64_t,int64_t>> exons;};std::map<std::string,Tx> txs;std::map<std::string,std::pair<std::string,std::string>> genes;
    for(auto line:split(data,'\n')) {if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.empty()||line[0]=='#')continue;need(line.size()<=65536,"GTF line exceeds 64 KiB bound");auto flds=split(line,'\t');need(flds.size()==9,"GTF requires exactly nine tab-separated columns");if(flds[2]!="exon")continue;
        need(e.refs.count(flds[0]),"GTF contig absent from BAM reference dictionary: "+flds[0]);auto start=int64_t(decimal(flds[3],1,2147483647,"GTF start"));auto end=int64_t(decimal(flds[4],1,2147483647,"GTF end"));need(flds[3].find('.')==std::string::npos && flds[4].find('.')==std::string::npos && end>=start && end<=e.refs.at(flds[0]),"GTF exon coordinates outside BAM reference bounds");need(flds[6]=="+"||flds[6]=="-","GTF exons require + or - strand");
        auto tid=attribute(flds[8],"transcript_id"),gid=attribute(flds[8],"gene_id");need(tid.size()<=199 && gid.size()<=199,"GTF IDs exceed 199 characters");auto context=std::make_pair(flds[0],flds[6]);auto existing=genes.emplace(gid,context);need(existing.second || existing.first->second==context,"A GTF gene_id maps to inconsistent contig/strand");auto& tx=txs[tid];if(tx.exons.empty()){tx.chr=flds[0];tx.gene=gid;tx.strand=flds[6];}need(tx.chr==flds[0]&&tx.gene==gid&&tx.strand==flds[6],"A GTF transcript_id maps to inconsistent contig/gene/strand");tx.exons.emplace_back(start,end);++e.exons;need(e.exons<=1000000 && txs.size()<=100000,"GTF exceeds one million exons or 100000 transcripts");
    }
    need(!txs.empty(),"GTF contains no valid exon rows with gene_id and transcript_id");
    for(auto& item:txs){auto& ex=item.second.exons;std::sort(ex.begin(),ex.end());for(size_t i=1;i<ex.size();++i)need(ex[i].first>ex[i-1].second,"Overlapping or duplicate exons within a GTF transcript are not supported");}
    e.transcripts=txs.size();return e;
}
static std::string summarize(const fs::path& out,const Evidence& e) {
    auto data=read(out/"transcripts.gtf",268435456);uint64_t transcripts=0,exons=0;double maxcov=0,maxtpm=0;
    for(auto line:split(data,'\n')){if(line.empty()||line[0]=='#')continue;auto f=split(line,'\t');need(f.size()==9,"StringTie returned malformed GTF");if(f[2]=="exon")++exons;if(f[2]!="transcript")continue;++transcripts;
        for(auto name:{"cov","FPKM","TPM"}) {auto value=attribute(f[8],name);size_t used=0;double n=std::stod(value,&used);need(used==value.size()&&std::isfinite(n)&&n>=0,"StringTie returned nonfinite/negative abundance");if(std::string(name)=="cov")maxcov=std::max(maxcov,n);if(std::string(name)=="TPM")maxtpm=std::max(maxtpm,n);}}
    auto abundance=read(out/"gene-abundance.tsv",268435456);need(abundance.rfind("Gene ID\t",0)==0,"StringTie gene-abundance header missing");
    std::ostringstream s;s<<std::setprecision(12)<<"{\n  \"bamRecords\": "<<e.records<<",\n  \"mappedRecords\": "<<e.mapped<<",\n  \"splicedRecords\": "<<e.spliced<<",\n  \"guideTranscripts\": "<<e.transcripts<<",\n  \"guideExons\": "<<e.exons<<",\n  \"outputTranscripts\": "<<transcripts<<",\n  \"outputExons\": "<<exons<<",\n  \"maximumTranscriptCoverage\": "<<maxcov<<",\n  \"maximumTranscriptTPM\": "<<maxtpm<<",\n  \"measurementsAreExpressionEstimates\": true,\n  \"integerReadCountsProduced\": false,\n  \"assemblyIdentityEstablishedByContigBounds\": false,\n  \"guidance\": "<<json_quote(transcripts?"Coverage, FPKM and TPM are estimates, not read counts or QC pass thresholds.":"No transcript passed the selected assembly settings. Review coverage, strandedness, annotation compatibility and recorded parameters; this is a valid empty result.")<<"\n}\n";return s.str();
}
int main(int argc,char** argv) {
    try {
        need(argc==12,"Usage: stringtie-guard assemble-guided|estimate-reference alignment.bam annotation.gtf results unstranded|rf|fr min-length min-coverage junction-coverage isoform-fraction single-exon-coverage max-multimap-fraction");
        std::string mode=argv[1],strand=argv[5];need(mode=="assemble-guided"||mode=="estimate-reference","Unknown StringTie operation");need(strand=="unstranded"||strand=="rf"||strand=="fr","Select library strandedness explicitly: unstranded, rf (read1 opposes), or fr (read1 follows transcript)");
        for(int i:{2,3,4})local(argv[i]);
        fs::path bam=fs::absolute(argv[2]),gtf=fs::absolute(argv[3]),out=fs::absolute(argv[4]);need(fs::is_directory(out),"Results directory is missing");
        decimal(argv[6],30,10000,"Minimum transcript length");need(std::string(argv[6]).find('.')==std::string::npos,"Minimum transcript length must be an integer");decimal(argv[7],0.001,1000000,"Minimum coverage");decimal(argv[8],0,1000000,"Junction coverage");need(decimal(argv[9],0,1,"Isoform fraction")<1,"Isoform fraction must be less than1");decimal(argv[10],0.001,1000000,"Single-exon coverage");decimal(argv[11],0,1,"Maximum multimap fraction");
        for(auto name:{"transcripts.gtf","gene-abundance.tsv","stringtie-summary.json","analysis-settings.json","stringtie.log"})need(!fs::exists(out/name),"Refusing to replace existing output: "+std::string(name));
        Evidence e=validate(bam,gtf);
#ifdef _WIN32
        const char* executable="stringtie.exe";
#else
        const char* executable="stringtie";
#endif
        fs::path binary=fs::absolute(argv[0]).parent_path()/executable;need(fs::is_regular_file(binary),"Bundled StringTie executable missing; reinstall the pack");
        std::vector<std::string> args={binary.string(),bam.generic_string(),"-G",gtf.generic_string(),"-o",(out/"transcripts.gtf").generic_string(),"-A",(out/"gene-abundance.tsv").generic_string(),"-p","1","-m",argv[6],"-c",argv[7],"-j",argv[8],"-f",argv[9],"-s",argv[10],"-M",argv[11],"-a","10","-g","50","-l","STRG"};if(mode=="estimate-reference")args.push_back("-e");if(strand!="unstranded")args.push_back("--"+strand);
        std::ostringstream settings;settings<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\n  \"toolVersion\": \"3.0.3-workbench1\",\n  \"operation\": "<<json_quote(mode)<<",\n  \"strandness\": "<<json_quote(strand)<<",\n  \"processingThreads\": 1,\n  \"minimumTranscriptLength\": "<<std::stod(argv[6])<<",\n  \"minimumCoverage\": "<<std::stod(argv[7])<<",\n  \"minimumJunctionCoverage\": "<<std::stod(argv[8])<<",\n  \"minimumIsoformFraction\": "<<std::stod(argv[9])<<",\n  \"minimumSingleExonCoverage\": "<<std::stod(argv[10])<<",\n  \"maximumMultimapFraction\": "<<std::stod(argv[11])<<",\n  \"minimumJunctionAnchorBases\": 10,\n  \"bundleGapBases\": 50,\n  \"multimapCorrection\": true,\n  \"endTrimming\": true,\n  \"sampleIdentity\": "<<json_quote(e.samples.empty()?"User-selected one-sample BAM; no RG sample declared":*e.samples.begin())<<",\n  \"referenceAssociation\": \"User selected matching annotation; guard verifies names and bounds, not genome sequence identity\",\n  \"arguments\": [";for(size_t i=0;i<args.size();++i){if(i)settings<<", ";settings<<json_quote(args[i]);}settings<<"]\n}\n";write(out/"analysis-settings.json",settings.str());
        int status=child(args,out/"stringtie.log");need(status==0,"StringTie failed (exit "+std::to_string(status)+"); inspect stringtie.log, BAM integrity, annotation and available memory");write(out/"stringtie-summary.json",summarize(out,e));return 0;
    }catch(const std::exception& e){std::cerr<<"StringTie input/result validation: "<<e.what()<<"\n";return 2;}
}
