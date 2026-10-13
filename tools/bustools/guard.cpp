// SPDX-License-Identifier: MIT
// Bounded coherent BUS I/O and subprocess boundary. Upstream bustools performs all scientific transformations.
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <limits>
#include <tuple>
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;
constexpr size_t MAX_INPUT = 64 * 1024 * 1024;


static void need(bool ok, const std::string& message) {
    if (!ok) throw std::runtime_error(message);
}
static std::string json(const std::string& value) {
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
static bool id_character(unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-';
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
    need(output != INVALID_HANDLE_VALUE, "Cannot create bustools execution log");
    HANDLE input = CreateFileA("NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                               &security, OPEN_EXISTING, 0, nullptr);
    if (input == INVALID_HANDLE_VALUE) { CloseHandle(output); need(false, "Cannot open null input for bustools"); }
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
    need(started, "Cannot start bundled bustools executable; reinstall this pack");
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return int(code);
#else
    pid_t process = fork();
    need(process >= 0, "Cannot start bustools subprocess");
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
    need(waitpid(process, &status, 0) == process, "Cannot wait for bustools subprocess");
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
#endif
}
static std::vector<std::string> split(const std::string& value, char delimiter) {
    std::vector<std::string> result;
    size_t start = 0;
    do {
        size_t end = value.find(delimiter, start);
        result.push_back(value.substr(start, end == std::string::npos ? end : end - start));
        if (end == std::string::npos) break;
        start = end + 1;
    } while (true);
    return result;
}
static uint64_t integer(const std::string& value, uint64_t maximum, const std::string& label) {
    need(!value.empty() && value.size() <= 20, "Invalid " + label);
    uint64_t n = 0;
    for (unsigned char c : value) {
        need(c >= '0' && c <= '9' && uint64_t(c - '0') <= maximum && n <= (maximum - uint64_t(c - '0')) / 10, "Out-of-range " + label);
        n = n * 10 + uint64_t(c - '0');
    }
    need(n <= maximum, "Out-of-range " + label);
    return n;
}
static std::vector<std::string> lines(const fs::path& path, size_t maxBytes, size_t maxLines, bool empty=false) {
    auto content = read(path, maxBytes);
    std::vector<std::string> result;
    std::istringstream input(content);
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        need(!line.empty() && line.size() <= 1048576, "Blank or oversized text row: " + path.string());
        for (unsigned char c : line) need(c == '\t' || (c >= 32 && c < 127), "Plain ASCII text required: " + path.string());
        result.push_back(line);
        need(result.size() <= maxLines, "Too many text rows: " + path.string());
    }
    need(empty || !result.empty(), "Required table is empty: " + path.string());
    return result;
}
static void identifier(const std::string& value) {
    need(!value.empty() && value.size() <= 128, "Transcript/gene identifiers must contain 1-128 ASCII letters, digits, dots, underscores or hyphens");
    for (unsigned char c : value) need(id_character(c), "Invalid transcript/gene identifier");
}
static uint64_t dna(const std::string& text, uint32_t length) {
    need(text.size() == length, "Allowlist barcode length differs from BUS header; select the same assay's allowlist");
    uint64_t result = 0;
    for (char c : text) {
        auto i = std::string("ACGT").find(c);
        need(i != std::string::npos, "Allowlist requires uppercase A/C/G/T barcodes without suffixes");
        result = (result << 2) | i;
    }
    return result;
}
static uint32_t u32(const std::string& data, size_t pos) {
    uint32_t n = 0;
    for (size_t i = 0; i < 4; ++i) n |= uint32_t(static_cast<unsigned char>(data.at(pos+i))) << (8*i);
    return n;
}
static uint64_t u64(const std::string& data, size_t pos) {
    return uint64_t(u32(data,pos)) | uint64_t(u32(data,pos+4)) << 32;
}
struct BusInfo { uint32_t bc, umi; size_t records; uint64_t multiplicity; std::set<uint64_t> barcodes; };
static BusInfo bus(const fs::path& path, size_t ecCount, bool sorted=false) {
    auto data = read(path, MAX_INPUT + 4116);
    need(data.size() >= 20 && data.substr(0,4) == std::string("BUS\0",4) && u32(data,4) == 1,
         "Select an uncompressed little-endian BUS version 1 file from kallisto bus; BUSZ/FASTQ are unsupported");
    auto bc = u32(data,8), umi = u32(data,12), header = u32(data,16);
    need(bc >= 1 && bc <= 16 && umi >= 1 && umi <= 31, "Supported BUS barcode length is 1-16 and UMI length is 1-31; longer/split barcodes require a separate reviewed workflow");
    need(header <= 4096 && data.size() >= 20 + header && (data.size()-20-header)%32 == 0,
         "Truncated BUS header/record or unsupported oversized BUS comment");
    size_t n = (data.size()-20-header)/32;
    need(n <= 2000000, "BUS input exceeds the 2000000-record limit");
    BusInfo info{bc,umi,n,0,{}};
    std::tuple<uint64_t,uint64_t,uint32_t> previous{};
    for (size_t i=0,p=20+header; i<n; ++i,p+=32) {
        auto barcode = u64(data,p), um = u64(data,p+8);
        auto ec=u32(data,p+16), count=u32(data,p+20);
        need((barcode >> (2*bc)) == 0 && (um >> (2*umi)) == 0,
             "BUS contains barcode/UMI metadata above the declared sequence length; pooled/split metadata is unsupported");
        need(ec < ecCount, "BUS equivalence-class index is absent from matrix.ec; select files from the same kallisto bus run");
        need(count > 0, "BUS read multiplicity must be positive");
        need(u32(data,p+24)==0 && u32(data,p+28)==0, "Nonzero BUS flags/padding are unsupported; use an ordinary unmodified kallisto BUS bundle");
        info.multiplicity += count;
        need(info.multiplicity <= std::numeric_limits<uint32_t>::max(), "Total BUS read multiplicity exceeds the safe 32-bit collapse bound");
        auto current = std::make_tuple(barcode,um,ec);
        need(!sorted || i==0 || previous < current, "Upstream sorted BUS is not strictly ordered/deduplicated");
        previous=current;
        info.barcodes.insert(barcode);
    }
    return info;
}
static void canonical(const fs::path& target, const std::vector<std::string>& rows) {
    std::string content;
    for (const auto& row : rows) content += row + '\n';
    write(target, content);
}
static int run(int argc, char** argv) {
    need(argc==7, "Usage: bustools-guard BUS transcripts.txt matrix.ec transcripts-to-genes.tsv allowlist.txt output-directory");
    std::vector<fs::path> inputs;
    for (int i=1;i<argc;++i) local(argv[i]);
    for (int i=1;i<=5;++i) inputs.push_back(fs::absolute(argv[i]));
    fs::path out=fs::absolute(argv[6]);
    local(out.string());
    need(fs::is_directory(out), "Select an existing results directory");
    for (size_t i=0;i<inputs.size();++i) {
        need(fs::is_regular_file(inputs[i]), "Required local input is missing");
        for (size_t j=0;j<i;++j) need(!fs::equivalent(inputs[i],inputs[j]), "Select five distinct coherent bundle files");
    }
    auto transcripts=lines(inputs[1],32*1024*1024,250000);
    std::set<std::string> txSet;
    for (const auto& tx:transcripts) { identifier(tx); need(txSet.insert(tx).second,"Duplicate transcript identifier"); }
    auto ecs=lines(inputs[2],64*1024*1024,500000);
    size_t membership=0;
    for (size_t i=0;i<ecs.size();++i) {
        auto row=split(ecs[i],'\t');
        need(row.size()==2 && integer(row[0],499999,"EC index")==i,"matrix.ec requires consecutive zero-based IDs and tab-separated transcript indices");
        auto refs=split(row[1],',');
        uint64_t previous=0;
        for (size_t j=0;j<refs.size();++j) {
            auto value=integer(refs[j],transcripts.size()-1,"EC transcript index");
            need(j==0 || previous<value,"matrix.ec transcript indices must be sorted and unique");
            previous=value;
        }
        membership+=refs.size();
        need(membership<=5000000,"EC mapping exceeds 5000000 transcript memberships");
    }
    auto mapping=lines(inputs[3],64*1024*1024,250000);
    std::set<std::string> mapped, genes;
    std::vector<std::string> normalizedMap;
    for (const auto& line:mapping) {
        auto row=split(line,'\t');
        need(row.size()==2 || row.size()==3,"Transcript-to-gene mapping requires two or three tab-separated columns; optional third gene-name column is ignored");
        identifier(row[0]); identifier(row[1]);
        need(txSet.count(row[0])==1 && mapped.insert(row[0]).second,"Transcript-to-gene mapping contains an unknown or duplicate transcript");
        genes.insert(row[1]); normalizedMap.push_back(row[0]+'\t'+row[1]);
    }
    need(mapped==txSet,"Every transcript must have exactly one gene mapping; select mapping from the same annotation/index");
    auto original=bus(inputs[0],ecs.size());
    auto allow=lines(inputs[4],128*1024*1024,4000000);
    std::set<uint64_t> allowed;
    for (const auto& value:allow) need(allowed.insert(dna(value,original.bc)).second,"Duplicate barcode in assay allowlist");
    for (const auto& name:{"counts.mtx","counts.genes.txt","counts.barcodes.txt","corrected.bus","sorted.bus","summary.json","settings.json","adapter.log","correct.log","sort.log","count.log","transcripts.input.txt","matrix.input.ec","genes.input.tsv","allowlist.input.txt"})
        need(!fs::exists(out/name),"Refusing to replace existing result: "+std::string(name));
    need(!fs::exists(out/"sort-tmp"),"Refusing to reuse an existing temporary directory");
    fs::create_directory(out/"sort-tmp");
    canonical(out/"transcripts.input.txt",transcripts); canonical(out/"matrix.input.ec",ecs);
    canonical(out/"genes.input.tsv",normalizedMap); canonical(out/"allowlist.input.txt",allow);
    fs::path tool=fs::absolute(argv[0]).parent_path()/
#ifdef _WIN32
        "bustools.exe";
#else
        "bustools";
#endif
    local(tool.string()); need(fs::is_regular_file(tool),"Bundled bustools executable missing; reinstall this pack");
    std::vector<std::vector<std::string>> commands={
        {tool.string(),"correct","-w",(out/"allowlist.input.txt").string(),"-o",(out/"corrected.bus").string(),inputs[0].string()},
        {tool.string(),"sort","-t","1","-m","64M","-T",(out/"sort-tmp").string(),"-o",(out/"sorted.bus").string(),(out/"corrected.bus").string()},
        {tool.string(),"count","-o",(out/"counts").string(),"-g",(out/"genes.input.tsv").string(),"-e",(out/"matrix.input.ec").string(),"-t",(out/"transcripts.input.txt").string(),"--genecounts",(out/"sorted.bus").string()}};
    const std::vector<std::string> stages={"correct","sort","count"};
    bool emptyHeaderPreserved=false;
    for (size_t i=0;i<commands.size();++i) {
        int code=child(commands[i],out/(stages[i]+".log"));
        need(code==0,"bustools "+stages[i]+" failed (exit "+std::to_string(code)+"); inspect "+stages[i]+".log and review bundle consistency, local disk space and assay choice");
        if (i==1) {
            auto retained=bus(out/"corrected.bus",ecs.size());
            // Upstream sort 0.45.1 emits no header for zero input records.
            // Preserve the exact valid input header, adding no scientific record.
            if (retained.records==0 && fs::is_regular_file(out/"sorted.bus") && fs::file_size(out/"sorted.bus")==0) {
                fs::copy_file(out/"corrected.bus",out/"sorted.bus",fs::copy_options::overwrite_existing);
                emptyHeaderPreserved=true;
            }
            bus(out/"sorted.bus",ecs.size(),true);
        }

    }
    auto corrected=bus(out/"corrected.bus",ecs.size()), ordered=bus(out/"sorted.bus",ecs.size(),true);
    need(corrected.bc==original.bc && corrected.umi==original.umi && ordered.bc==original.bc && ordered.umi==original.umi,"Upstream changed BUS sequence dimensions");
    need(corrected.records<=original.records && corrected.multiplicity<=original.multiplicity && ordered.multiplicity==corrected.multiplicity,"Upstream correction/sort read conservation failed");
    for (auto bc:corrected.barcodes) need(allowed.count(bc)==1,"Corrected BUS contains a barcode absent from assay allowlist");
    auto geneRows=lines(out/"counts.genes.txt",32*1024*1024,250000);
    need(std::set<std::string>(geneRows.begin(),geneRows.end())==genes && geneRows.size()==genes.size(),"Upstream matrix gene labels differ from mapping");
    auto barcodeRows=lines(out/"counts.barcodes.txt",64*1024*1024,2000000,true);
    std::set<uint64_t> barcodes;
    for (const auto& line:barcodeRows) need(barcodes.insert(dna(line,original.bc)).second,"Duplicate output barcode label");
    need(barcodes==corrected.barcodes,"Upstream matrix barcode labels differ from retained BUS");
    std::istringstream matrix(read(out/"counts.mtx",128*1024*1024));
    std::string line; need(bool(std::getline(matrix,line)) && line.find("%%MatrixMarket matrix coordinate real general")==0,"Unexpected Matrix Market header");
    do { need(bool(std::getline(matrix,line)),"Missing matrix dimensions"); } while(!line.empty() && line[0]=='%');
    size_t rows=0,cols=0,entries=0; std::string extra;
    { std::istringstream dim(line); need(bool(dim>>rows>>cols>>entries) && !(dim>>extra),"Invalid matrix dimensions"); }
    need(rows==barcodeRows.size() && cols==geneRows.size() && entries<=2000000,"Matrix dimensions do not match labels/bounds");
    uint64_t molecules=0; std::set<std::pair<size_t,size_t>> coordinates;
    for (size_t i=0;i<entries;++i) {
        need(bool(std::getline(matrix,line)),"Truncated Matrix Market entries");
        size_t r=0,c=0; std::string value; std::istringstream entry(line);
        need(bool(entry>>r>>c>>value) && !(entry>>extra) && r>=1 && r<=rows && c>=1 && c<=cols,"Invalid Matrix Market coordinate");
        auto count=integer(value,2000000,"molecule count");
        need(count>0 && coordinates.insert({r,c}).second,"Invalid duplicate/zero matrix count");
        molecules+=count;
    }
    while (std::getline(matrix,line)) need(line.find_first_not_of(" \t\r")==std::string::npos,"Unexpected matrix trailing entries");
    need(molecules<=corrected.records,"Counted molecules exceed retained BUS records");
    std::ostringstream summary;
    summary << "{\n  \"schema\": 1,\n  \"inputRecords\": " << original.records << ",\n  \"inputReadMultiplicity\": " << original.multiplicity
      << ",\n  \"retainedRecords\": " << corrected.records << ",\n  \"retainedReadMultiplicity\": " << corrected.multiplicity
      << ",\n  \"sortedRecords\": " << ordered.records << ",\n  \"discardedBarcodeRecords\": " << original.records-corrected.records
      << ",\n  \"barcodes\": " << rows << ",\n  \"genes\": " << cols << ",\n  \"nonzeroEntries\": " << entries
      << ",\n  \"countedMolecules\": " << molecules << ",\n  \"matrixOrientation\": \"barcodes-by-genes\",\n  \"cellCallingPerformed\": false,\n  \"qcThresholdsApplied\": false\n}\n";
    write(out/"summary.json",summary.str());
    std::ostringstream settings;
    settings << "{\n  \"schema\": 1,\n  \"toolVersion\": \"0.45.1-workbench1\",\n  \"barcodeCorrection\": \"retain exact allowlist matches; uniquely correct Hamming-distance-1; discard ambiguous/unmatched\",\n  \"umiPolicy\": \"exact barcode-plus-UMI; retain only a single-gene intersection across its equivalence classes; no collision rescue\",\n  \"umiErrorCorrection\": false,\n  \"sortThreads\": 1,\n  \"sortBufferBytes\": 67108864,\n  \"sortBufferIsProcessMemoryCap\": false,\n  \"textNormalization\": \"CRLF to LF; optional third gene-name column ignored\",\n  \"associationReview\": \"Caller must select BUS, matrix.ec and transcript order from the same kallisto run and a matching annotation/assay. Structural checks cannot prove common biological origin.\",\n  \"commands\": [";
    for(size_t i=0;i<commands.size();++i) { if(i) settings<<','; settings<<'['; for(size_t j=0;j<commands[i].size();++j) { if(j) settings<<','; settings<<json(commands[i][j]); } settings<<']'; }
    settings << "],\n  \"emptySortedBusHeaderPreserved\": " << (emptyHeaderPreserved ? "true" : "false") << "\n}\n";
    write(out/"settings.json",settings.str());
    write(out/"adapter.log",molecules ? "Coherent input structure and upstream matrix dimensions verified. Counts are measurements, not cell calls or QC acceptance.\n" : "Zero retained molecule counts is a valid result. Review assay allowlist, mapping associations and ambiguity logs; do not interpret zero as a QC pass or evidence of no expression.\n");
    std::cout << "bustools completed: " << molecules << " exact-UMI molecule counts across " << rows << " retained barcode rows (not called cells)\n";
    return 0;
}
int main(int argc,char** argv) {
    try { return run(argc,argv); }
    catch(const std::exception& error) { std::cerr << "bustools input/execution error: " << error.what() << '\n'; return 2; }
}
