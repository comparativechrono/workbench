// Native Windows checks for the production runner's Job Object accounting.
// Cross-compilation alone does not pass these checks; execute the PE on Windows.
#include "workbench.h"
#include "process_performance.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <locale>
#include <stdexcept>

namespace {
constexpr SIZE_T ALLOCATION = 16 * 1024 * 1024;
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
bool write(HANDLE destination, const char* bytes, DWORD size) {
    while (size) {
        DWORD count = 0;
        if (!WriteFile(destination, bytes, size, &count, nullptr) || !count) return false;
        bytes += count; size -= count;
    }
    return true;
}
std::wstring self() {
    std::vector<wchar_t> path(32768);
    const auto length = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    require(length && length < path.size(), "Cannot locate performance test executable");
    return std::wstring(path.data(), length);
}
int child(int argc, wchar_t** argv) {
    const std::wstring mode = argv[2];
    if (mode == L"quiet-wait") { Sleep(INFINITE); return 41; }
    if (mode == L"wait") {
        if (!write(GetStdHandle(STD_ERROR_HANDLE), "waiting\n", 8)) return 40;
        Sleep(INFINITE); return 41;
    }
    if (mode == L"sink") {
        std::array<char, 4096> bytes{};
        for (;;) {
            DWORD count = 0;
            if (!ReadFile(GetStdHandle(STD_INPUT_HANDLE), bytes.data(), static_cast<DWORD>(bytes.size()), &count, nullptr))
                return GetLastError() == ERROR_BROKEN_PIPE ? 0 : 42;
            if (!count) return 0;
            if (!write(GetStdHandle(STD_OUTPUT_HANDLE), bytes.data(), count)) return 43;
        }
    }
    if (mode == L"detached") {
        auto command = bw::quote_argument(self()) + L" --child quiet-wait";
        STARTUPINFOW startup{}; startup.cb = sizeof(startup);
        PROCESS_INFORMATION process{};
        if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                nullptr, nullptr, &startup, &process)) return 44;
        const auto pid = std::to_string(process.dwProcessId) + "\n";
        CloseHandle(process.hThread); CloseHandle(process.hProcess);
        return write(GetStdHandle(STD_OUTPUT_HANDLE), pid.data(), static_cast<DWORD>(pid.size())) ? 0 : 45;
    }
    if (mode != L"work") return 46;
    auto* memory = static_cast<volatile unsigned char*>(VirtualAlloc(nullptr, ALLOCATION, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
    if (!memory) return 47;
    for (SIZE_T i = 0; i < ALLOCATION; i += 4096) memory[i] = static_cast<unsigned char>(i / 4096);
    volatile unsigned long value = 1;
    const auto began = GetTickCount64();
    while (GetTickCount64() - began < 100) for (unsigned i = 0; i < 10000; ++i) value = value * 1664525UL + 1013904223UL;
    if (!write(GetStdHandle(STD_OUTPUT_HANDLE), "measured output\n", 16)) return 48;
    VirtualFree(const_cast<unsigned char*>(memory), 0, MEM_RELEASE);
    return argc > 3 ? _wtoi(argv[3]) : 0;
}
void measured(const bw::ProcessPerformance& value, DWORD processes, bool memory = false) {
    // GetTickCount64 can legitimately return zero for a short command.
    require(value.launched && value.wall_available, "Missing command wall time");
    require(value.accounting_available && value.memory_available, "Job accounting query was unavailable");
    require(!value.accounting_error && !value.memory_error, "Successful accounting retained a query error");
    require(value.processes_total == processes, "Job accounting has incorrect process-tree scope");
    require(value.user_ticks >= 0 && value.kernel_ticks >= 0, "Negative Windows CPU accounting");
    if (memory) {
        require(value.wall_ms >= 100, "Timed work has an inconsistent command duration");
        require(value.peak_job_memory_bytes >= ALLOCATION, "Peak committed memory missed the allocation");
        require(value.user_ticks + value.kernel_ticks > 0, "CPU work was not observed");
    }
}
struct CommaDecimal : std::numpunct<char> { char do_decimal_point() const override { return ','; } };
} // namespace

int wmain(int argc, wchar_t** argv) {
    if (argc >= 3 && std::wstring(argv[1]) == L"--child") return child(argc, argv);
    try {
        require(argc == 2 || (argc == 4 && std::wstring(argv[2]) == L"--report"),
            "Usage: WindowsPerformanceChecks.exe OUTPUT_PARENT [--report NEW_REPORT_FILE]");
        const auto binary = self(), folder = bw::unique_directory(argv[1], L"performance-native-checks");
        bw::Cancel cancel{false};
        std::vector<std::string> observations;
        auto save = [&](const wchar_t* name, const bw::ProcessPerformance& value) {
            observations.push_back("{\"check\":" + bw::json_string(name) + ",\"performance\":" + bw::process_performance_json(value) + "}");
        };
        auto command = [&](const wchar_t* name, const std::wstring& mode, const std::wstring& code = L"0",
                const bw::Log& log = bw::Log{}, DWORD timeout = 10000, bw::ProcessPerformance* performance = nullptr) {
            const auto base = bw::join(folder, name);
            return bw::execute(binary, {L"--child", mode, code}, base + L".stdout", base + L".stderr",
                cancel, log, timeout, folder, performance);
        };
        auto result = command(L"exec-success", L"work");
        require(!result.exit_code && !result.cancelled && !result.performance.pipeline, "Exec outcome changed");
        require(bw::read_file(bw::join(folder, L"exec-success.stdout")) == "measured output\n", "Exec output changed");
        measured(result.performance, 1, true); save(L"exec-success", result.performance);
        result = command(L"exec-failure", L"work", L"17");
        require(result.exit_code == 17 && !result.cancelled, "Exec failure was hidden");
        measured(result.performance, 1, true); save(L"exec-failure", result.performance);

        auto pipe = [&](const wchar_t* name, const std::wstring& producer, const std::wstring& sink,
                const std::wstring& code = L"0", const bw::Log& log = bw::Log{}, DWORD timeout = 10000,
                bw::ProcessPerformance* performance = nullptr) {
            const auto base = bw::join(folder, name);
            return bw::execute_pipeline(binary, {L"--child", producer, code}, binary, {L"--child", sink},
                base + L".stdout", base + L".producer.stderr", base + L".sink.stderr",
                cancel, log, timeout, folder, performance);
        };
        auto piped = pipe(L"pipe-success", L"work", L"sink");
        require(!piped.producer_exit_code && !piped.sink_exit_code && !piped.cancelled && piped.performance.pipeline,
            "Pipeline outcome changed");
        require(bw::read_file(bw::join(folder, L"pipe-success.stdout")) == "measured output\n", "Pipe bytes changed");
        measured(piped.performance, 2, true); save(L"pipe-success", piped.performance);
        piped = pipe(L"pipe-failure", L"work", L"sink", L"17");
        require(piped.producer_exit_code == 17 && !piped.cancelled, "Pipeline failure was hidden");
        measured(piped.performance, 2, true); save(L"pipe-failure", piped.performance);

        result = command(L"exec-cancel", L"wait", L"0", [&](const std::wstring& line) {
            if (line == L"waiting") cancel.store(true);
        });
        require(result.cancelled && result.exit_code, "Exec cancellation changed");
        measured(result.performance, 1); save(L"exec-cancel", result.performance); cancel.store(false);
        bool producer_waiting = false, sink_waiting = false;
        piped = pipe(L"pipe-cancel", L"wait", L"wait", L"0", [&](const std::wstring& line) {
            producer_waiting = producer_waiting || line == L"[producer] waiting";
            sink_waiting = sink_waiting || line == L"[sink] waiting";
            if (producer_waiting && sink_waiting) cancel.store(true);
        });
        require(producer_waiting && sink_waiting && piped.cancelled && piped.producer_exit_code && piped.sink_exit_code,
            "Pipeline cancellation changed");
        measured(piped.performance, 2); save(L"pipe-cancel", piped.performance); cancel.store(false);

        bw::ProcessPerformance timeout;
        bool threw = false;
        try { (void)command(L"exec-timeout", L"wait", L"0", {}, 100, &timeout); }
        catch (const std::exception& error) { threw = std::string(error.what()).find("time limit") != std::string::npos; }
        require(threw, "Exec timeout no longer throws"); measured(timeout, 1); save(L"exec-timeout", timeout);
        threw = false;
        try { (void)pipe(L"pipe-timeout", L"wait", L"wait", L"0", {}, 100, &timeout); }
        catch (const std::exception& error) { threw = std::string(error.what()).find("time limit") != std::string::npos; }
        require(threw, "Pipeline timeout no longer throws"); measured(timeout, 2); save(L"pipe-timeout", timeout);

        bw::ProcessPerformance interrupted_exec;
        threw = false;
        try {
            (void)command(L"exec-observer-exception", L"wait", L"0", [&](const std::wstring& line) {
                if (line == L"waiting") throw std::runtime_error("deliberate observer failure");
            }, 10000, &interrupted_exec);
        } catch (const std::exception& error) {
            threw = std::string(error.what()) == "deliberate observer failure";
        }
        require(threw && interrupted_exec.launched && interrupted_exec.accounting_available &&
            interrupted_exec.memory_available && interrupted_exec.processes_total == 1 && interrupted_exec.processes_active == 1,
            "Exec exception discarded the live child's accounting");
        require(bw::process_performance_json(interrupted_exec).find("\"coverage\":\"partial\"") != std::string::npos,
            "Exec exception claimed complete coverage");
        save(L"exec-observer-exception", interrupted_exec);

        // The sink is suspended inside the job when producer creation fails.
        // This exercises exception unwinding before the ordinary exit snapshot.
        bw::ProcessPerformance interrupted;
        threw = false;
        const auto interrupted_base = bw::join(folder, L"producer-start-failure");
        try {
            (void)bw::execute_pipeline(bw::join(folder, L"missing.exe"), {}, binary, {L"--child", L"wait"},
                interrupted_base + L".stdout", interrupted_base + L".producer.stderr", interrupted_base + L".sink.stderr",
                cancel, {}, 10000, folder, &interrupted);
        } catch (const std::exception& error) {
            threw = std::string(error.what()).find("Cannot start pipeline executable") != std::string::npos;
        }
        require(threw && interrupted.launched && interrupted.accounting_available && interrupted.memory_available &&
            interrupted.processes_total == 1 && interrupted.processes_active == 1,
            "Partial-start exception discarded the live sink's accounting");
        require(bw::process_performance_json(interrupted).find("\"coverage\":\"partial\"") != std::string::npos,
            "Partial-start exception claimed complete coverage");
        save(L"pipeline-start-exception", interrupted);

        result = command(L"live-descendant", L"detached");
        require(!result.exit_code && result.performance.processes_active > 0, "Live descendant was not reflected in coverage");
        measured(result.performance, 2);
        require(bw::process_performance_json(result.performance).find("\"coverage\":\"partial\"") != std::string::npos,
            "Live descendant incorrectly reported complete coverage");
        const auto pid = static_cast<DWORD>(std::stoul(bw::read_file(bw::join(folder, L"live-descendant.stdout"))));
        const auto descendant = OpenProcess(SYNCHRONIZE, FALSE, pid);
        if (descendant) {
            const auto stopped = WaitForSingleObject(descendant, 5000);
            CloseHandle(descendant);
            require(stopped == WAIT_OBJECT_0, "Existing job cleanup did not stop the descendant");
        } else require(GetLastError() == ERROR_INVALID_PARAMETER, "Cannot establish descendant cleanup");
        save(L"live-descendant-partial-coverage-and-cleanup", result.performance);

        cancel.store(true);
        result = command(L"not-started", L"work");
        require(result.cancelled && !result.performance.launched && !result.performance.wall_available,
            "Cancelled-before-start execution fabricated observations");
        const auto absent = bw::process_performance_json(result.performance);
        require(absent.find("\"user_cpu_seconds\":null") != std::string::npos &&
            absent.find("\"peak_job_memory_bytes\":null") != std::string::npos &&
            absent.find("\"coverage\":\"not-started\"") != std::string::npos, "Unavailable values were not null");
        save(L"cancel-before-start", result.performance); cancel.store(false);

        bw::ProcessPerformance unavailable; unavailable.launched = true;
        { bw::JobPerformanceCapture invalid(INVALID_HANDLE_VALUE, unavailable); invalid.capture(); }
        require(!unavailable.accounting_available && !unavailable.memory_available &&
            unavailable.accounting_error == ERROR_INVALID_HANDLE && unavailable.memory_error == ERROR_INVALID_HANDLE,
            "Unavailable counters were silently reported as zero");
        const auto invalid_json = bw::process_performance_json(unavailable);
        require(invalid_json.find("\"user_cpu_seconds\":null") != std::string::npos &&
            invalid_json.find("\"peak_job_memory_bytes\":null") != std::string::npos &&
            invalid_json.find("\"coverage\":\"unavailable\"") != std::string::npos, "Failed queries fabricated metrics");
        save(L"unavailable-query", unavailable);

        bw::ProcessPerformance decimal; decimal.launched = true; decimal.accounting_available = true; decimal.user_ticks = 1234567;
        const auto previous = std::locale();
        std::locale::global(std::locale(previous, new CommaDecimal));
        const auto locale_json = bw::process_performance_json(decimal);
        std::locale::global(previous);
        require(locale_json.find("\"user_cpu_seconds\":0.1234567") != std::string::npos, "Locale corrupted JSON CPU seconds");
        save(L"locale-independent-json", decimal);

        std::string report = "{\"schema\":1,\"native_windows_execution\":true,\"passed\":" +
            std::to_string(observations.size()) + ",\"failed\":0,\"skipped\":0,\"observations\":[";
        for (size_t i = 0; i < observations.size(); ++i) { if (i) report += ','; report += observations[i]; }
        report += "]}\n";
        bw::write_file_new(bw::join(folder, L"performance-validation.json"), report);
        if (argc == 4) bw::write_file_new(argv[3], report);
        std::wprintf(L"PASS: %zu native Windows performance checks. Results: %ls\n", observations.size(), folder.c_str());
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what()); return 1;
    }
}
