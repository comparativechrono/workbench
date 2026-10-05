#include "desktop_ipc.h"
#include "workbench.h"
#include <algorithm>
#include <commctrl.h>
#include <cwctype>
#include <deque>
#include <gdiplus.h>
#include <iomanip>
#include <map>
#include <memory>
#include <objidl.h>
#include <set>
#include <shellapi.h>
#include <shobjidl.h>
#include <sstream>
#include <windowsx.h>

namespace {
using desktop::Json;
constexpr UINT HOST_MESSAGE = WM_APP + 35;
constexpr COLORREF BACK = RGB(243, 245, 248), PAPER = RGB(255, 255, 255),
                   INK = RGB(32, 44, 62), MUTED = RGB(98, 112, 132),
                   BORDER = RGB(218, 225, 233), ACCENT = RGB(54, 82, 121);
enum {
  NAME = 101,
  SEARCH,
  CATEGORY,
  TASKS,
  ADD,
  STEPS,
  REMOVE,
  UNDO,
  UP,
  DOWN,
  OUTPUT,
  BROWSE_OUTPUT,
  RUN,
  CANCEL,
  REVIEW,
  BACK_WORKSPACE,
  DAG,
  FORM,
  STATUS,
  FILE_NEW = 301,
  FILE_EXAMPLE,
  FILE_SAVE_PIPELINE,
  FILE_SAVE_PRESET,
  FILE_LOAD,
  FILE_HISTORY,
  FILE_IMPORT,
  FILE_CHECK,
  FILE_EXIT,
  VIEW_LOG,
  VIEW_METHODS,
  OPEN_RESULTS,
  CLEAR_FILTER = 401,
  MANAGE_TOOLS,
  MANAGE_REFERENCES,
  PACK_SEARCH = 501,
  PACK_FILTER,
  PACK_LIST,
  PACK_DETAILS,
  PACK_INSTALL,
  PACK_IMPORT_ZIP,
  PACK_IMPORT_FOLDER,
  PACK_SOURCE,
  PACK_REFRESH,
  PACK_CANCEL,
  PACK_PROGRESS,
  PACK_NOTICE,
  PACK_CLOSE,
  REF_TAB = 601,
  REF_RELEASE,
  REF_QUERY,
  REF_SEARCH,
  REF_SPECIES,
  REF_DISCOVER,
  REF_FILES,
  REF_DETAILS,
  REF_DESTINATION,
  REF_BROWSE,
  REF_DOWNLOAD,
  REF_LOCAL,
  REF_TARGET,
  REF_USE,
  REF_OPEN,
  REF_CANCEL,
  REF_PROGRESS,
  REF_NOTICE,
  REF_CLOSE,
  FIELD_BASE = 2000
};
std::wstring wide(const std::string &s) { return bw::utf16(s); }
std::string narrow(const std::wstring &s) { return bw::utf8(s); }
std::string text(const Json &j, const std::string &fallback = {}) {
  if (j.is_string())
    return j.string();
  if (j.is_bool() || j.is_number())
    return j.dump();
  return fallback;
}
std::string getstr(const Json &j, const char *key,
                   const std::string &fallback = {}) {
  return text(j.get(key), fallback);
}
std::wstring wt(const Json &j, const char *key,
                const std::string &fallback = {}) {
  return wide(getstr(j, key, fallback));
}
std::wstring control_text(HWND h) {
  const int n = GetWindowTextLengthW(h);
  std::wstring out(static_cast<size_t>(n) + 1, L'\0');
  int got = GetWindowTextW(h, out.data(), n + 1);
  out.resize(std::max(0, got));
  return out;
}
std::wstring lower(std::wstring s) {
  for (auto &c : s)
    c = static_cast<wchar_t>(std::towlower(c));
  return s;
}
std::string display_id(const std::string &id) {
  auto p = id.find('-');
  return (id.rfind("step-", 0) == 0 ? "S" : "I") +
         (p == id.npos ? id : id.substr(p + 1));
}
std::wstring quote(const std::wstring &arg) {
  std::wstring out = L"\"";
  size_t n = 0;
  for (wchar_t c : arg) {
    if (c == L'\\') {
      ++n;
      continue;
    }
    out.append(c == L'"' ? n * 2 + 1 : n, L'\\');
    out += c;
    n = 0;
  }
  out.append(n * 2, L'\\');
  return out + L'"';
}
Json object(std::initializer_list<std::pair<const std::string, Json>> values) {
  return Json(Json::Object(values));
}
std::wstring lines(std::wstring s) {
  std::wstring r;
  for (wchar_t c : s) {
    if (c == L'\n')
      r += L'\r';
    if (c != L'\r')
      r += c;
  }
  return r;
}
void rounded(Gdiplus::Graphics &g, float x, float y, float w, float h,
             float radius, COLORREF fill, COLORREF stroke = BORDER) {
  if (w <= 0 || h <= 0)
    return;
  Gdiplus::GraphicsPath p;
  float d = std::min({radius * 2, w, h});
  p.AddArc(x, y, d, d, 180, 90);
  p.AddArc(x + w - d, y, d, d, 270, 90);
  p.AddArc(x + w - d, y + h - d, d, d, 0, 90);
  p.AddArc(x, y + h - d, d, d, 90, 90);
  p.CloseFigure();
  Gdiplus::SolidBrush b(
      Gdiplus::Color(255, GetRValue(fill), GetGValue(fill), GetBValue(fill)));
  g.FillPath(&b, &p);
  Gdiplus::Pen pen(Gdiplus::Color(255, GetRValue(stroke), GetGValue(stroke),
                                  GetBValue(stroke)));
  g.DrawPath(&pen, &p);
}
std::wstring pick(HWND owner, bool folder, bool multiple,
                  const std::wstring &filter, const std::wstring &title) {
  IFileOpenDialog *raw = nullptr;
  HRESULT hr = CoCreateInstance(CLSID_FileOpenDialog, nullptr,
                                CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&raw));
  if (FAILED(hr))
    throw std::runtime_error("Windows could not create the file picker.");
  struct Release {
    IFileOpenDialog *p;
    ~Release() { p->Release(); }
  } release{raw};
  FILEOPENDIALOGOPTIONS flags{};
  raw->GetOptions(&flags);
  hr = raw->SetOptions(flags | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST |
                       FOS_NOCHANGEDIR |
                       (folder ? FOS_PICKFOLDERS : FOS_FILEMUSTEXIST) |
                       (multiple ? FOS_ALLOWMULTISELECT : 0));
  if (FAILED(hr))
    throw std::runtime_error("Windows could not configure the file picker.");
  raw->SetTitle(title.c_str());
  std::vector<std::wstring> parts;
  std::vector<COMDLG_FILTERSPEC> specs;
  if (!folder && !filter.empty()) {
    size_t pos = 0;
    for (;;) {
      auto end = filter.find(L'|', pos);
      parts.push_back(
          filter.substr(pos, end == filter.npos ? filter.npos : end - pos));
      if (end == filter.npos)
        break;
      pos = end + 1;
    }
    if (parts.size() % 2 == 0)
      for (size_t i = 0; i < parts.size(); i += 2)
        specs.push_back({parts[i].c_str(), parts[i + 1].c_str()});
    if (!specs.empty())
      raw->SetFileTypes(static_cast<UINT>(specs.size()), specs.data());
  }
  hr = raw->Show(owner);
  if (hr == HRESULT_FROM_WIN32(ERROR_CANCELLED))
    return {};
  if (FAILED(hr))
    throw std::runtime_error("The file picker failed.");
  IShellItemArray *items = nullptr;
  hr = raw->GetResults(&items);
  if (FAILED(hr))
    throw std::runtime_error("Could not read selected paths.");
  struct RI {
    IShellItemArray *p;
    ~RI() { p->Release(); }
  } ri{items};
  DWORD count = 0;
  items->GetCount(&count);
  std::wstring out;
  for (DWORD i = 0; i < count; ++i) {
    IShellItem *item = nullptr;
    if (FAILED(items->GetItemAt(i, &item)))
      continue;
    PWSTR p = nullptr;
    hr = item->GetDisplayName(SIGDN_FILESYSPATH, &p);
    item->Release();
    if (FAILED(hr))
      continue;
    if (!out.empty())
      out += L'\n';
    out += p;
    CoTaskMemFree(p);
  }
  return out;
}
void clipboard(HWND owner, const std::wstring &value) {
  if (!OpenClipboard(owner))
    return;
  EmptyClipboard();
  const size_t bytes = (value.size() + 1) * sizeof(wchar_t);
  HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, bytes);
  if (mem) {
    void *p = GlobalLock(mem);
    if (p) {
      memcpy(p, value.c_str(), bytes);
      GlobalUnlock(mem);
      if (!SetClipboardData(CF_UNICODETEXT, mem))
        GlobalFree(mem);
    } else
      GlobalFree(mem);
  }
  CloseClipboard();
}

struct Modal {
  HWND owner{}, window{}, body{}, ok{};
  HFONT font{};
  int mode = 0;
  bool multiple = false, accepted = false;
  std::wstring title, message, value, confirm = L"OK";
  std::vector<std::wstring> labels;
  std::vector<int> selected;
  UINT dpi = 96;
  int px(int n) const { return MulDiv(n, static_cast<int>(dpi), 96); }
  static LRESULT CALLBACK proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    auto *s = reinterpret_cast<Modal *>(GetWindowLongPtrW(h, GWLP_USERDATA));
    if (m == WM_NCCREATE) {
      s = static_cast<Modal *>(
          reinterpret_cast<CREATESTRUCTW *>(l)->lpCreateParams);
      s->window = h;
      SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(s));
    }
    if (!s)
      return DefWindowProcW(h, m, w, l);
    if (m == WM_COMMAND) {
      if (LOWORD(w) == IDOK) {
        s->accepted = true;
        if (s->mode == 1)
          s->value = control_text(s->body);
        if (s->mode == 0) {
          s->selected.clear();
          if (s->multiple) {
            int n =
                static_cast<int>(SendMessageW(s->body, LB_GETSELCOUNT, 0, 0));
            if (n > 0) {
              s->selected.resize(static_cast<size_t>(n));
              SendMessageW(s->body, LB_GETSELITEMS, n,
                           reinterpret_cast<LPARAM>(s->selected.data()));
            }
          } else {
            int n = static_cast<int>(SendMessageW(s->body, LB_GETCURSEL, 0, 0));
            if (n >= 0)
              s->selected.push_back(n);
          }
        }
        DestroyWindow(h);
        return 0;
      }
      if (LOWORD(w) == IDCANCEL) {
        DestroyWindow(h);
        return 0;
      }
      if (LOWORD(w) == 103) {
        clipboard(h, control_text(s->body));
        return 0;
      }
      if (HIWORD(w) == LBN_DBLCLK && !s->multiple) {
        SendMessageW(h, WM_COMMAND, IDOK, 0);
        return 0;
      }
    }
    if (m == WM_SIZE) {
      RECT r{};
      GetClientRect(h, &r);
      MoveWindow(s->body, s->px(18), s->px(48),
                 std::max<int>(1, r.right - s->px(36)),
                 std::max<int>(s->px(30), r.bottom - s->px(110)), TRUE);
      MoveWindow(s->ok, r.right - s->px(250), r.bottom - s->px(48), s->px(130),
                 s->px(32), TRUE);
      MoveWindow(GetDlgItem(h, IDCANCEL), r.right - s->px(108),
                 r.bottom - s->px(48), s->px(90), s->px(32), TRUE);
      if (s->mode == 2)
        MoveWindow(GetDlgItem(h, 103), s->px(18), r.bottom - s->px(48),
                   s->px(130), s->px(32), TRUE);
      return 0;
    }
    if (m == WM_CLOSE) {
      DestroyWindow(h);
      return 0;
    }
    return DefWindowProcW(h, m, w, l);
  }
  bool show() {
    HINSTANCE inst = GetModuleHandleW(nullptr);
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = proc;
    wc.hInstance = inst;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    wc.lpszClassName = L"WorkbenchNativeModal051";
    RegisterClassExW(&wc);
    dpi = GetDpiForWindow(owner);
    RECT r{};
    GetWindowRect(owner, &r);
    const int width = px(mode == 1 ? 560 : 720),
              height = px(mode == 1 ? 225 : 530);
    window = CreateWindowExW(
        WS_EX_DLGMODALFRAME | WS_EX_CONTROLPARENT, wc.lpszClassName,
        title.c_str(), WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME,
        r.left + std::max<LONG>(0, (r.right - r.left - width) / 2),
        r.top + std::max<LONG>(0, (r.bottom - r.top - height) / 2), width,
        height, owner, nullptr, inst, this);
    if (!window)
      return false;
    auto control = [&](const wchar_t *klass, const wchar_t *content,
                       DWORD style, int id) {
      HWND h = CreateWindowExW(
          0, klass, content, WS_CHILD | WS_VISIBLE | style, 0, 0, 1, 1, window,
          reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), inst, nullptr);
      SendMessageW(h, WM_SETFONT, reinterpret_cast<WPARAM>(font), FALSE);
      return h;
    };
    HWND label = control(L"STATIC", message.c_str(), 0, 104);
    MoveWindow(label, px(18), px(15), width - px(44), px(30), FALSE);
    if (mode == 0) {
      body = control(L"LISTBOX", L"",
                     WS_TABSTOP | WS_VSCROLL | WS_HSCROLL | LBS_NOTIFY |
                         (multiple ? LBS_EXTENDEDSEL : 0) | WS_BORDER,
                     105);
      for (auto &item : labels)
        SendMessageW(body, LB_ADDSTRING, 0,
                     reinterpret_cast<LPARAM>(item.c_str()));
      for (int n : selected)
        SendMessageW(body, multiple ? LB_SETSEL : LB_SETCURSEL,
                     multiple ? TRUE : n, multiple ? n : 0);
    } else {
      body = control(L"EDIT", lines(value).c_str(),
                     WS_TABSTOP | WS_BORDER |
                         (mode == 2 ? ES_MULTILINE | ES_READONLY |
                                          ES_AUTOVSCROLL | WS_VSCROLL
                                    : ES_AUTOHSCROLL),
                     105);
      if (mode == 2) {
        SendMessageW(body, EM_SETLIMITTEXT, 8 * 1024 * 1024, 0);
        SetWindowTextW(body, lines(value).c_str());
      }
    }
    ok = control(L"BUTTON", confirm.c_str(), WS_TABSTOP | BS_DEFPUSHBUTTON,
                 IDOK);
    control(L"BUTTON", mode == 2 ? L"Close" : L"Cancel", WS_TABSTOP, IDCANCEL);
    if (mode == 2)
      control(L"BUTTON", L"Copy text", WS_TABSTOP, 103);
    SendMessageW(window, WM_SIZE, 0, 0);
    EnableWindow(owner, FALSE);
    ShowWindow(window, SW_SHOW);
    SetFocus(body);
    MSG msg{};
    while (IsWindow(window) && GetMessageW(&msg, nullptr, 0, 0) > 0) {
      if (!IsDialogMessageW(window, &msg)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
      }
    }
    EnableWindow(owner, TRUE);
    SetForegroundWindow(owner);
    return accepted;
  }
};

class Workspace {
  struct Field {
    HWND h{}, button{};
    std::string kind, key, node, source, port;
    Json schema;
    std::wstring initial;
    int y = 0, height = 34;
  };
  struct Hit {
    RECT box;
    std::string id;
    bool source = false;
  };
  HINSTANCE instance{};
  HWND window{}, name{}, search{}, category{}, tasks{}, add{}, clearFilter{},
      steps{}, remove{}, undo{}, up{}, down{}, output{}, browse{}, run{},
      cancel{}, review{}, back{}, dag{}, form{}, status{}, manageTools{},
      packWindow{}, packSearch{}, packFilter{}, packList{}, packDetails{},
      packInstall{}, packImportZip{}, packImportFolder{}, packSource{},
      packRefresh{}, packCancel{}, packProgress{}, packNotice{}, packClose{},
      manageReferences{}, refWindow{}, refTab{}, refIntro{}, refReleaseLabel{},
      refRelease{}, refQuery{}, refSearch{}, refSpecies{}, refDiscover{},
      refFiles{}, refDetails{}, refDestinationLabel{}, refDestination{},
      refBrowse{}, refDownload{}, refLocal{}, refTargetLabel{}, refTarget{},
      refUse{}, refOpen{}, refCancel{}, refProgress{}, refNotice{}, refClose{};
  HFONT font{}, bold{}, small{};
  HFONT refFont{};
  HBRUSH paper{}, background{};
  desktop::HostProcess host;
  Json state = Json::object(), catalog = object({{"tools", Json::object()}}),
       runState = Json::object(), historyRun = Json::object(),
       packState = object({{"packs", Json::array()}}),
       packOperation = Json::object(), refState = Json::object(),
       refOperation = Json::object(), refTargets = Json::array();
  std::map<long long, std::string> pending;
  long long nextRequest = 1, activeRequest = 0;
  std::deque<Json> outgoing;
  std::string submittedFields;
  ULONGLONG closeStarted = 0;
  bool rebuilding = false, ready = false, busy = false, closing = false,
       reviewThenRun = false, showingHistory = false, autoCheck = false;
  bool packBusy = false, packActionPending = false, packPollPending = false,
       packRebuilding = false, packReloadAfterOperation = false,
       packListAfterOperation = false, packPollFailed = false;
  bool refBusy = false, refActionPending = false, refPollPending = false,
       refRebuilding = false, refPollFailed = false;
  UINT dpi = 96;
  UINT packDpi = 96;
  UINT refDpi = 96;
  int width = 1000, height = 700, formScroll = 0, formExtent = 0, dagX = 0,
      dagY = 0, dagWidth = 1, dagHeight = 1;
  std::vector<Field> fields;
  std::vector<HWND> formControls;
  std::map<int, size_t> fieldIds;
  std::vector<std::string> taskIds, stepIds;
  std::vector<size_t> packRows;
  std::vector<std::pair<size_t, size_t>> refLocalRows;
  std::vector<Hit> hits;
  std::string selected, runId, dragTool;
  Json requiredPack = Json::object();
  std::wstring root, logs;
  ULONGLONG lastPoll = 0;
  ULONGLONG lastPackPoll = 0;
  ULONGLONG lastRefPoll = 0;
  bool pollPending = false;
  int px(int n) const { return MulDiv(n, static_cast<int>(dpi), 96); }
  HWND make(const wchar_t *klass, const std::wstring &title, DWORD style,
            int id, HWND parent = nullptr, DWORD ex = 0) {
    HWND h = CreateWindowExW(ex, klass, title.c_str(),
                             WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | style, 0,
                             0, 1, 1, parent ? parent : window,
                             reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),
                             instance, nullptr);
    if (!h)
      throw std::runtime_error("Could not create a Windows interface control.");
    SendMessageW(h, WM_SETFONT, reinterpret_cast<WPARAM>(font), FALSE);
    return h;
  }
  HWND button(const wchar_t *s, int id, HWND p = nullptr) {
    return make(L"BUTTON", s, WS_TABSTOP | BS_PUSHBUTTON, id, p);
  }
  void place(HWND h, int x, int y, int w, int hgt) {
    MoveWindow(h, px(x), px(y), px(std::max(1, w)), px(std::max(1, hgt)), TRUE);
  }
  static LRESULT CALLBACK field_proc(HWND h, UINT message_, WPARAM w, LPARAM l,
                                     UINT_PTR, DWORD_PTR context) {
    auto *app = reinterpret_cast<Workspace *>(context);
    if (message_ == WM_SETFOCUS) {
      auto found = app->fieldIds.find(GetDlgCtrlID(h));
      if (found != app->fieldIds.end() && found->second < app->fields.size()) {
        const auto &field = app->fields[found->second];
        RECT client{};
        GetClientRect(app->form, &client);
        int visible = MulDiv(client.bottom, 96, app->dpi);
        if (field.y < app->formScroll)
          app->formScroll = field.y;
        else if (field.y + field.height > app->formScroll + visible)
          app->formScroll = field.y + field.height - visible;
        app->layout_fields();
      }
    }
    if (message_ == WM_MOUSEWHEEL &&
        !SendMessageW(h, CB_GETDROPPEDSTATE, 0, 0)) {
      app->scroll(app->form, SB_VERT, 0,
                  -GET_WHEEL_DELTA_WPARAM(w) * 48 / WHEEL_DELTA);
      return 0;
    }
    if (message_ == WM_NCDESTROY)
      RemoveWindowSubclass(h, field_proc, 1);
    return DefSubclassProc(h, message_, w, l);
  }
  void fonts() {
    for (HFONT f : {font, bold, small})
      if (f)
        DeleteObject(f);
    auto create = [&](int size, int weight) {
      return CreateFontW(-px(size), 0, 0, 0, weight, FALSE, FALSE, FALSE,
                         DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                         CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH,
                         L"Segoe UI");
    };
    font = create(14, FW_NORMAL);
    bold = create(14, FW_SEMIBOLD);
    small = create(12, FW_NORMAL);
    if (window)
      EnumChildWindows(
          window,
          [](HWND h, LPARAM l) -> BOOL {
            SendMessageW(h, WM_SETFONT, static_cast<WPARAM>(l), TRUE);
            return TRUE;
          },
          reinterpret_cast<LPARAM>(font));
  }
  void close_host_window() {
    host.stop();
    MSG msg{};
    while (PeekMessageW(&msg, window, HOST_MESSAGE, HOST_MESSAGE, PM_REMOVE))
      delete reinterpret_cast<std::string *>(msg.lParam);
    DestroyWindow(window);
  }
  void message(const std::wstring &value) {
    MessageBoxW(window, value.c_str(), L"Native Workbench",
                MB_OK | MB_ICONERROR);
  }
  void status_text(const std::wstring &value) {
    SetWindowTextW(status, value.c_str());
  }
  void pump() {
    if (activeRequest || outgoing.empty())
      return;
    Json request = std::move(outgoing.front());
    outgoing.pop_front();
    activeRequest = request.get("id").integer();
    host.send(request);
    enabled();
  }
  long long send(const std::string &method, Json params = Json::object()) {
    long long id = nextRequest++;
    pending[id] = method;
    outgoing.push_back(object(
        {{"id", id}, {"method", method}, {"params", std::move(params)}}));
    pump();
    return id;
  }
  void model(const std::string &action, Json payload = Json::object()) {
    if (!ready || busy || packBusy || packActionPending || refBusy ||
        refActionPending || showingHistory)
      return;
    send("model",
         object({{"action", action}, {"payload", std::move(payload)}}));
  }
  const Json &graph() const {
    static const Json empty =
        object({{"nodes", Json::array()}, {"sources", Json::array()}});
    const Json &g =
        showingHistory ? historyRun.get("graph") : state.get("graph");
    return g.is_object() && g.get("nodes").is_array() &&
                   g.get("sources").is_array()
               ? g
               : empty;
  }
  const Json &tool(const std::string &id) const {
    return catalog.get("tools").get(id);
  }
  const Json &tool(const Json &node) const {
    static const Json missing = Json::object();
    const auto id = getstr(node, "tool");
    if (!node.contains("pin"))
      return tool(id);
    const auto &pin = node.get("pin");
    if (!pin.is_object() || getstr(pin, "packVersion").empty() ||
        getstr(pin, "manifestSha256").empty())
      return missing;
    const auto matches = [&](const Json &candidate) {
      return getstr(candidate, "packVersion") == getstr(pin, "packVersion") &&
             getstr(candidate, "manifestSha256") == getstr(pin, "manifestSha256") &&
             (!pin.contains("packId") || getstr(candidate, "packId") == getstr(pin, "packId"));
    };
    for (const auto &candidate : catalog.get("toolVersions").get(id).array_items())
      if (matches(candidate))
        return candidate;
    const auto &latest = tool(id);
    return matches(latest) ? latest : missing;
  }
  std::string node_name(const Json &n) const {
    std::string label = getstr(n, "label");
    return label.empty()
               ? getstr(tool(n), "name", getstr(n, "tool"))
               : label;
  }
  std::map<std::string, int> ranks() const {
    std::map<std::string, int> r;
    for (const auto &n : graph().get("nodes").array_items())
      r[getstr(n, "id")] = 1;
    for (size_t k = 0; k < r.size(); ++k) {
      bool changed = false;
      for (const auto &n : graph().get("nodes").array_items()) {
        const auto id = getstr(n, "id");
        int rank = 1;
        for (const auto &port : n.get("inputs").object_items())
          for (const auto &ref : port.second.array_items()) {
            auto value = text(ref);
            auto sep = value.find("::");
            if (sep != value.npos) {
              auto found = r.find(value.substr(0, sep));
              if (found != r.end())
                rank = std::max(rank, found->second + 1);
            }
          }
        if (rank != r[id]) {
          r[id] = rank;
          changed = true;
        }
      }
      if (!changed)
        break;
    }
    return r;
  }
  static std::wstring download_size(long long bytes) {
    if (bytes <= 0)
      return L"—";
    std::wostringstream value;
    if (bytes < 1024 * 1024)
      value << std::fixed << std::setprecision(0) << bytes / 1024.0 << L" KB";
    else if (bytes < 1024LL * 1024 * 1024)
      value << std::fixed << std::setprecision(1)
            << bytes / (1024.0 * 1024.0) << L" MB";
    else
      value << std::fixed << std::setprecision(1)
            << bytes / (1024.0 * 1024.0 * 1024.0) << L" GB";
    return value.str();
  }
  static std::string pack_key(const Json &item) {
    return getstr(item, "id") + "\n" + getstr(item, "version") + "\n" +
           getstr(item, "sourceId");
  }
  const Json &selected_pack() const {
    static const Json empty = Json::object();
    if (!packWindow)
      return empty;
    int row = ListView_GetNextItem(packList, -1, LVNI_SELECTED);
    if (row < 0 || static_cast<size_t>(row) >= packRows.size())
      return empty;
    const auto &items = packState.get("packs").array_items();
    size_t at = packRows[static_cast<size_t>(row)];
    return at < items.size() ? items[at] : empty;
  }
  void pack_send(const std::string &method, Json params = Json::object()) {
    if (method != "packs/list" && method != "packs/status")
      packActionPending = true;
    if (method == "packs/status")
      packPollPending = true;
    if (method == "packs/refresh")
      packListAfterOperation = true;
    send(method, std::move(params));
    pack_enabled();
  }
  void pack_enabled() {
    if (!packWindow)
      return;
    const bool idle = ready && !busy && !closing && !packBusy && !refBusy &&
                      !refActionPending &&
                      !packActionPending;
    const auto &item = selected_pack();
    const bool canInstall = !getstr(item, "id").empty() &&
                            !item.get("installed").boolean() &&
                            item.get("compatible").boolean(true) &&
                            !getstr(item, "sourceId").empty();
    SetWindowTextW(packInstall, item.get("updateAvailable").boolean()
                                   ? L"Install update"
                                   : L"Install selected");
    EnableWindow(packInstall, idle && canInstall);
    for (HWND h : {packImportZip, packImportFolder, packSource, packRefresh})
      EnableWindow(h, idle);
    EnableWindow(packCancel, ready && packBusy && !packActionPending &&
                                 packOperation.get("cancellable").boolean(true) &&
                                 getstr(packOperation, "status") != "cancelling");
  }
  void pack_selection() {
    if (!packWindow)
      return;
    const auto &item = selected_pack();
    std::wstring value;
    if (!getstr(item, "id").empty()) {
      value = wt(item, "name", getstr(item, "id")) + L"  ·  " +
              wt(item, "version") + L"\n\n" + wt(item, "description");
      if (!getstr(item, "category").empty())
        value += L"\n\nCategory: " + wt(item, "category");
      for (const auto &version : item.get("toolVersions").object_items())
        value += L"\n" + wide(version.first) + L": " + wide(text(version.second));
      if (!getstr(item, "sourceId").empty())
        value += L"\nCatalogue: " + wt(item, "sourceId");
      value += L"\nDownload: " + download_size(item.get("size").integer());
      value += item.get("installed").boolean() ? L"\nInstalled on this computer."
                                               : L"\nAvailable to install.";
      if (!item.get("compatible").boolean(true))
        value += L"\nCannot install: " +
                 wt(item, "reason", "This pack requires a different application version.");
      else if (!getstr(item, "reason").empty())
        value += L"\n" + wt(item, "reason");
      if (item.get("updateAvailable").boolean())
        value += L"\nAn update is available. Existing versions are retained for saved pipelines.";
    } else
      value = L"Select a tool pack to see its description and requirements.\n\n"
              L"Install from a trusted catalogue, or import a pack ZIP or folder. "
              L"Analysis and input data stay on this computer.";
    for (const auto &source : packState.get("sources").array_items())
      if (!getstr(source, "error").empty())
        value += L"\n\nCatalogue warning — " + wt(source, "name", getstr(source, "id")) +
                 L": " + wt(source, "error");
    for (const auto &error : packState.get("errors").array_items())
      value += L"\n\nUnavailable local pack — " + wt(error, "folder") +
               L"\n" + wt(error, "message", "This pack could not be loaded.");
    SetWindowTextW(packDetails, lines(value).c_str());
    pack_enabled();
  }
  void refresh_packs(const std::string &selectKey = {}) {
    if (!packWindow)
      return;
    const auto keep = selectKey.empty() ? pack_key(selected_pack()) : selectKey;
    const auto query = lower(control_text(packSearch));
    const int filter = static_cast<int>(SendMessageW(packFilter, CB_GETCURSEL, 0, 0));
    packRebuilding = true;
    SendMessageW(packList, WM_SETREDRAW, FALSE, 0);
    ListView_DeleteAllItems(packList);
    packRows.clear();
    int selectedRow = -1;
    const auto &items = packState.get("packs").array_items();
    for (size_t i = 0; i < items.size(); ++i) {
      const auto &item = items[i];
      const bool installed = item.get("installed").boolean();
      if ((filter == 1 && installed) || (filter == 2 && !installed) ||
          (filter == 3 && !item.get("updateAvailable").boolean()))
        continue;
      std::wstring label = wt(item, "name", getstr(item, "id"));
      if (!query.empty() &&
          lower(label + L" " + wt(item, "id") + L" " +
                wt(item, "category") + L" " + wt(item, "description"))
                  .find(query) == std::wstring::npos)
        continue;
      LVITEMW row{};
      row.mask = LVIF_TEXT;
      row.iItem = static_cast<int>(packRows.size());
      row.pszText = label.data();
      ListView_InsertItem(packList, &row);
      auto version = wt(item, "version");
      auto availability = installed ? L"Installed" : L"Available";
      if (!item.get("compatible").boolean(true))
        availability = L"Incompatible";
      else if (item.get("updateAvailable").boolean() && !installed)
        availability = L"Update available";
      auto size = download_size(item.get("size").integer());
      ListView_SetItemText(packList, row.iItem, 1, version.data());
      ListView_SetItemText(packList, row.iItem, 2,
                          const_cast<wchar_t *>(availability));
      ListView_SetItemText(packList, row.iItem, 3, size.data());
      if (pack_key(item) == keep)
        selectedRow = row.iItem;
      if (!getstr(requiredPack, "packId").empty() &&
          getstr(item, "id") == getstr(requiredPack, "packId") &&
          getstr(item, "version") == getstr(requiredPack, "packVersion") &&
          getstr(item, "manifestSha256") == getstr(requiredPack, "manifestSha256"))
        selectedRow = row.iItem;
      packRows.push_back(i);
    }
    if (selectedRow < 0 && !packRows.empty())
      selectedRow = 0;
    if (selectedRow >= 0) {
      ListView_SetItemState(packList, selectedRow, LVIS_SELECTED | LVIS_FOCUSED,
                            LVIS_SELECTED | LVIS_FOCUSED);
      ListView_EnsureVisible(packList, selectedRow, FALSE);
    }
    SendMessageW(packList, WM_SETREDRAW, TRUE, 0);
    InvalidateRect(packList, nullptr, TRUE);
    packRebuilding = false;
    pack_selection();
  }
  void pack_notice() {
    if (!packWindow)
      return;
    std::wstring value = wt(packOperation, "message");
    if (packBusy && getstr(packOperation, "message").rfind("Cancelling", 0) != 0) {
      if (getstr(packOperation, "phase") == "downloading")
        value = L"Downloading files...";
      else if (getstr(packOperation, "phase") == "verifying")
        value = L"Verifying pack files...";
    }
    if (value.empty())
      value = wt(packState, "notice");
    if (!packBusy)
      for (const auto &source : packState.get("sources").array_items())
        if (!getstr(source, "error").empty()) {
          value = wt(source, "name", getstr(source, "id")) + L": " + wt(source, "error");
          break;
        }
    if (value.empty())
      value = packRows.empty()
                  ? L"No matching packs. Change the filter, import a pack, or add a catalogue."
                  : L"Installed tools work offline. Refresh checks only the catalogues you have added.";
    const auto bytes = packOperation.get("bytes").integer(),
               total = packOperation.get("total").integer();
    if (packBusy && bytes > 0)
      value += L"  " + download_size(bytes) +
               (total > 0 ? L" / " + download_size(total) : L"");
    SetWindowTextW(packNotice, value.c_str());
    SendMessageW(packProgress, PBM_SETRANGE32, 0, 1000);
    SendMessageW(packProgress, PBM_SETPOS,
                 total > 0 ? static_cast<WPARAM>(std::clamp(
                                 1000.0 * static_cast<double>(bytes) /
                                     static_cast<double>(total),
                                 0.0, 1000.0))
                           : 0,
                 0);
    ShowWindow(packProgress, packBusy ? SW_SHOW : SW_HIDE);
  }
  void pack_layout() {
    if (!packWindow)
      return;
    RECT r{};
    GetClientRect(packWindow, &r);
    const int w = MulDiv(r.right, 96, packDpi),
              h = MulDiv(r.bottom, 96, packDpi);
    auto put = [&](HWND control, int x, int y, int cw, int ch) {
      MoveWindow(control, MulDiv(x, packDpi, 96), MulDiv(y, packDpi, 96),
                 MulDiv(std::max(1, cw), packDpi, 96),
                 MulDiv(std::max(1, ch), packDpi, 96), TRUE);
    };
    put(packSearch, 18, 18, w - 218, 32);
    put(packFilter, w - 188, 18, 170, 180);
    const int listHeight = std::max(110, h - 376);
    put(packList, 18, 62, w - 36, listHeight);
    put(packDetails, 18, 74 + listHeight, w - 36, 138);
    put(packInstall, 18, h - 154, 144, 32);
    put(packImportZip, 174, h - 154, 138, 32);
    put(packImportFolder, 324, h - 154, 138, 32);
    put(packSource, 18, h - 112, 144, 32);
    put(packRefresh, 174, h - 112, 138, 32);
    put(packCancel, 324, h - 112, 138, 32);
    put(packClose, w - 112, h - 112, 94, 32);
    put(packNotice, 18, h - 69, w - 36, 43);
    put(packProgress, 18, h - 20, w - 36, 7);
    ListView_SetColumnWidth(packList, 0, MulDiv(std::max(210, w - 380), packDpi, 96));
    ListView_SetColumnWidth(packList, 1, MulDiv(112, packDpi, 96));
    ListView_SetColumnWidth(packList, 2, MulDiv(130, packDpi, 96));
    ListView_SetColumnWidth(packList, 3, MulDiv(92, packDpi, 96));
  }
  void pack_command(int id, int notification) {
    if (id == PACK_CLOSE || id == IDCANCEL) {
      DestroyWindow(packWindow);
      return;
    }
    if ((id == PACK_SEARCH && notification == EN_CHANGE) ||
        (id == PACK_FILTER && notification == CBN_SELCHANGE)) {
      refresh_packs();
      pack_notice();
      return;
    }
    if (id == PACK_CANCEL && packBusy && !packActionPending &&
        packOperation.get("cancellable").boolean(true)) {
      pack_send("packs/cancel");
      return;
    }
    if (!ready || busy || closing || packBusy || packActionPending ||
        refBusy || refActionPending)
      return;
    if (id == PACK_REFRESH) {
      pack_send("packs/refresh");
      return;
    }
    if (id == PACK_INSTALL) {
      const auto &item = selected_pack();
      if (getstr(item, "id").empty() || item.get("installed").boolean() ||
          !item.get("compatible").boolean(true) || getstr(item, "sourceId").empty())
        return;
      commit_all();
      packReloadAfterOperation = true;
      pack_send("packs/install", object({{"source_id", getstr(item, "sourceId")},
                                          {"pack_id", getstr(item, "id")},
                                          {"version", getstr(item, "version")}}));
      return;
    }
    if (id == PACK_IMPORT_ZIP || id == PACK_IMPORT_FOLDER || id == PACK_SOURCE) {
      const bool folder = id == PACK_IMPORT_FOLDER;
      auto path = pick(packWindow, folder, false,
                       id == PACK_SOURCE ? L"Catalogue source configuration|*.json"
                                         : L"Tool pack archive|*.zip",
                       id == PACK_SOURCE ? L"Choose a trusted catalogue source configuration"
                       : folder ? L"Choose a trusted tool pack folder containing pack.ini"
                                : L"Choose a trusted tool pack ZIP");
      if (path.empty())
        return;
      const auto prompt = id == PACK_SOURCE
          ? L"Add this catalogue source?\n\nOnly add a source configuration supplied by "
            L"a publisher or institution you trust. Its packs contain programs that "
            L"will run on this computer.\n\nAdding the source does not install tools. "
            L"Use Refresh to retrieve its catalogue."
          : L"Import this tool pack?\n\nTool packs contain programs that run on this "
            L"computer. Only import packs from a publisher or institution you trust.";
      if (MessageBoxW(packWindow, prompt, L"Manage tools",
                       MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES)
        return;
      commit_all();
      if (id != PACK_SOURCE)
        packReloadAfterOperation = true;
      pack_send(id == PACK_SOURCE ? "packs/source" : "packs/import",
                object({{"path", narrow(path)}}));
    }
  }
  static LRESULT CALLBACK pack_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    auto *app = reinterpret_cast<Workspace *>(GetWindowLongPtrW(h, GWLP_USERDATA));
    if (m == WM_NCCREATE) {
      app = static_cast<Workspace *>(reinterpret_cast<CREATESTRUCTW *>(l)->lpCreateParams);
      app->packWindow = h;
      SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(app));
    }
    if (!app)
      return DefWindowProcW(h, m, w, l);
    try {
      switch (m) {
      case WM_COMMAND:
        app->pack_command(LOWORD(w), HIWORD(w));
        return 0;
      case WM_NOTIFY: {
        auto *n = reinterpret_cast<NMHDR *>(l);
        if (n->idFrom == PACK_LIST && n->code == LVN_ITEMCHANGED &&
            !app->packRebuilding) {
          app->requiredPack = Json::object();
          app->pack_selection();
        }
        return 0;
      }
      case WM_SIZE:
        app->pack_layout();
        return 0;
      case WM_DPICHANGED: {
        app->packDpi = HIWORD(w);
        auto *r = reinterpret_cast<RECT *>(l);
        SetWindowPos(h, nullptr, r->left, r->top, r->right - r->left,
                     r->bottom - r->top, SWP_NOZORDER | SWP_NOACTIVATE);
        app->pack_layout();
        return 0;
      }
      case WM_GETMINMAXINFO: {
        auto *info = reinterpret_cast<MINMAXINFO *>(l);
        info->ptMinTrackSize = {MulDiv(680, app->packDpi, 96),
                                MulDiv(570, app->packDpi, 96)};
        return 0;
      }
      case WM_CTLCOLORSTATIC:
      case WM_CTLCOLOREDIT:
      case WM_CTLCOLORBTN: {
        HDC dc = reinterpret_cast<HDC>(w);
        SetTextColor(dc, INK);
        SetBkColor(dc, BACK);
        return reinterpret_cast<LRESULT>(app->background);
      }
      case WM_CLOSE:
        DestroyWindow(h);
        return 0;
      case WM_NCDESTROY:
        app->packWindow = nullptr;
        app->packRows.clear();
        app->requiredPack = Json::object();
        SetWindowLongPtrW(h, GWLP_USERDATA, 0);
        return DefWindowProcW(h, m, w, l);
      default:
        break;
      }
    } catch (const std::exception &e) {
      MessageBoxW(h, wide(e.what()).c_str(), L"Manage tools", MB_OK | MB_ICONERROR);
    }
    return DefWindowProcW(h, m, w, l);
  }
  void show_pack_manager() {
    if (packWindow) {
      ShowWindow(packWindow, SW_RESTORE);
      SetForegroundWindow(packWindow);
      return;
    }
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = pack_proc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = background;
    wc.lpszClassName = L"WorkbenchPackManager060";
    RegisterClassExW(&wc);
    RECT r{};
    GetWindowRect(window, &r);
    packDpi = dpi;
    const int w = px(830), h = px(700);
    packWindow = CreateWindowExW(
        WS_EX_CONTROLPARENT, wc.lpszClassName, L"Manage tools · Native Workbench",
        WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN,
        r.left + std::max<LONG>(0, (r.right - r.left - w) / 2),
        r.top + std::max<LONG>(0, (r.bottom - r.top - h) / 2), w, h,
        window, nullptr, instance, this);
    if (!packWindow)
      throw std::runtime_error("Could not open the tool manager.");
    packSearch = make(L"EDIT", L"", WS_TABSTOP | ES_AUTOHSCROLL,
                       PACK_SEARCH, packWindow, WS_EX_CLIENTEDGE);
    SendMessageW(packSearch, EM_SETCUEBANNER, FALSE,
                 reinterpret_cast<LPARAM>(L"Search tools, descriptions or categories"));
    packFilter = make(L"COMBOBOX", L"", WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
                       PACK_FILTER, packWindow);
    for (const auto *label : {L"All packs", L"Available", L"Installed", L"Updates"})
      SendMessageW(packFilter, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(label));
    SendMessageW(packFilter, CB_SETCURSEL, 0, 0);
    packList = make(WC_LISTVIEWW, L"Tool packs",
                     WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
                     PACK_LIST, packWindow, WS_EX_CLIENTEDGE);
    ListView_SetExtendedListViewStyle(packList,
        LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_LABELTIP);
    int column = 0;
    for (const auto *label : {L"Tool pack", L"Pack version", L"Status", L"Download"}) {
      LVCOLUMNW col{};
      col.mask = LVCF_TEXT | LVCF_WIDTH;
      col.pszText = const_cast<wchar_t *>(label);
      col.cx = px(120);
      ListView_InsertColumn(packList, column++, &col);
    }
    packDetails = make(L"EDIT", L"",
        WS_TABSTOP | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL,
        PACK_DETAILS, packWindow, WS_EX_CLIENTEDGE);
    SendMessageW(packDetails, EM_SETLIMITTEXT, 256 * 1024, 0);
    packInstall = button(L"Install selected", PACK_INSTALL, packWindow);
    packImportZip = button(L"Import ZIP...", PACK_IMPORT_ZIP, packWindow);
    packImportFolder = button(L"Import folder...", PACK_IMPORT_FOLDER, packWindow);
    packSource = button(L"Add catalogue...", PACK_SOURCE, packWindow);
    packRefresh = button(L"Refresh", PACK_REFRESH, packWindow);
    packCancel = button(L"Cancel download", PACK_CANCEL, packWindow);
    packClose = button(L"Close", PACK_CLOSE, packWindow);
    packNotice = make(L"STATIC", L"Loading installed packs...", SS_LEFT | SS_NOPREFIX,
                       PACK_NOTICE, packWindow);
    packProgress = make(PROGRESS_CLASSW, L"Download progress", PBS_SMOOTH,
                         PACK_PROGRESS, packWindow);
    pack_layout();
    refresh_packs();
    pack_notice();
    ShowWindow(packWindow, SW_SHOW);
    SetFocus(packSearch);
    pack_send("packs/list");
  }
  void pack_response(const std::string &method, const Json &result) {
    packPollFailed = false;
    const auto previousSelection = pack_key(selected_pack());
    if (result.get("packs").is_array()) {
      packState = result;
      refresh_packs(previousSelection);
    }
    if (result.contains("operation"))
      packOperation = result.get("operation");
    packBusy = packOperation.get("active").boolean();
    if (result.contains("model")) {
      snapshot(result.get("model"));
      refresh_tasks(true);
    }
    const bool operationResponse = method == "packs/status" ||
        method == "packs/install" || method == "packs/import" || method == "packs/refresh";
    if (!packBusy && operationResponse && packReloadAfterOperation) {
      packReloadAfterOperation = false;
      packListAfterOperation = false;
      if (!result.contains("model") && packOperation.get("success").boolean())
        send("init");
      pack_send("packs/list");
    } else if (!packBusy && operationResponse && packListAfterOperation) {
      packListAfterOperation = false;
      if (!result.get("packs").is_array())
        pack_send("packs/list");
    } else if ((method == "packs/source" || method == "packs/refresh") &&
               !packBusy && !result.get("packs").is_array())
      pack_send("packs/list");
    if (packBusy)
      status_text(L"Managing tools: " + wt(packOperation, "message"));
    else if (!getstr(packOperation, "message").empty())
      status_text(wt(packOperation, "message"));
    pack_notice();
    pack_enabled();
    enabled();
    if (closing && !packBusy && !busy && !refBusy)
      send("shutdown");
  }
  static std::wstring reference_species(const Json &item) {
    const auto &species = item.get("species");
    return species.is_object() ? wt(species, "name", getstr(species, "id"))
                               : wide(text(species));
  }
  const Json &reference_local_record() const {
    static const Json empty = Json::object();
    if (!refWindow)
      return empty;
    const int row = ListView_GetNextItem(refLocal, -1, LVNI_SELECTED);
    if (row < 0 || static_cast<size_t>(row) >= refLocalRows.size())
      return empty;
    const auto index = refLocalRows[static_cast<size_t>(row)].first;
    const auto &items = refState.get("local").array_items();
    return index < items.size() ? items[index] : empty;
  }
  const Json &reference_local_file() const {
    static const Json empty = Json::object();
    if (!refWindow)
      return empty;
    const int row = ListView_GetNextItem(refLocal, -1, LVNI_SELECTED);
    if (row < 0 || static_cast<size_t>(row) >= refLocalRows.size())
      return empty;
    const auto index = refLocalRows[static_cast<size_t>(row)].second;
    const auto &files = reference_local_record().get("files").array_items();
    return index < files.size() ? files[index] : empty;
  }
  const Json &reference_selected_species() const {
    static const Json empty = Json::object();
    if (!refWindow)
      return empty;
    const int row = ListView_GetNextItem(refSpecies, -1, LVNI_SELECTED);
    const auto &items = refState.get("species").array_items();
    return row >= 0 && static_cast<size_t>(row) < items.size()
               ? items[static_cast<size_t>(row)] : empty;
  }
  void reference_send(const std::string &method, Json params = Json::object()) {
    if (method == "references/status")
      refPollPending = true;
    else
      refActionPending = true;
    send(method, std::move(params));
    enabled();
  }
  void reference_enabled() {
    if (!refWindow)
      return;
    const bool idle = ready && !busy && !closing && !packBusy &&
                      !packActionPending && !refBusy && !refActionPending;
    for (HWND h : {refRelease, refQuery, refSearch, refSpecies, refFiles,
                   refDestination, refBrowse, refLocal, refTarget})
      EnableWindow(h, idle);
    EnableWindow(refDiscover, idle &&
                 !getstr(reference_selected_species(), "id").empty());
    bool checked = false;
    for (int row = 0; row < ListView_GetItemCount(refFiles); ++row)
      checked = checked || ListView_GetCheckState(refFiles, row);
    EnableWindow(refDownload, idle && checked &&
                 !getstr(refState.get("discovery"), "selection_id").empty() &&
                 !control_text(refDestination).empty());
    EnableWindow(refOpen, idle && !getstr(reference_local_record(), "id").empty());
    EnableWindow(refTarget, idle && reference_local_record().get("available").boolean(true));
    EnableWindow(refUse, idle && !showingHistory &&
                 reference_local_record().get("available").boolean(true) &&
                 SendMessageW(refTarget, CB_GETCURSEL, 0, 0) >= 0 &&
                 !refTargets.array_items().empty());
    EnableWindow(refCancel, ready && refBusy && !refActionPending &&
                 refOperation.get("cancellable").boolean(true) &&
                 getstr(refOperation, "status") != "cancelling");
  }
  void reference_details() {
    if (!refWindow)
      return;
    std::wstring value;
    if (TabCtrl_GetCurSel(refTab) == 1) {
      const auto &record = reference_local_record(), &file = reference_local_file();
      if (!getstr(record, "id").empty()) {
        if (!record.get("available").boolean(true))
          value = L"Unavailable: " + wt(record, "error", "This reference bundle needs attention.") + L"\n";
        value += reference_species(record) + L"  ·  " + wt(record, "assembly") +
                L"  ·  Ensembl release " + wt(record, "release") +
                L"\nAssembly accession: " + wt(record, "assembly_accession", "Not recorded") +
                L"\n" + wt(file, "path") + L"\nSHA-256: " + wt(file, "sha256") +
                L"\nDownload record: " + wt(record, "receipt_path");
        for (const auto &warning : record.get("warnings").array_items())
          value += L"\nWarning: " + wide(text(warning));
      } else
        value = L"No downloaded reference files yet. Find a species on the Find online tab, "
                L"then select the files to download. Existing downloads can be used offline.";
      const auto omitted = refState.get("omitted_local").integer();
      if (omitted > 0)
        value += L"\nLibrary display limit: " + std::to_wstring(omitted) +
                 L" older reference bundles are not shown here. Their files remain on disk.";
    } else {
      const auto &discovery = refState.get("discovery");
      value = wt(discovery, "notice");
      if (!getstr(discovery, "selection_id").empty()) {
        const auto &species = discovery.get("species");
        value = reference_species(discovery) + L"  ·  " +
                wt(discovery, "assembly", getstr(species, "assembly")) +
                L"  ·  Ensembl release " + wt(discovery, "release") +
                L"\nAssembly accession: " + wt(discovery, "assembly_accession",
                    getstr(species, "assembly_accession", "Not recorded")) + L"\n" + value;
        for (const auto &warning : discovery.get("warnings").array_items())
          value += L"\nWarning: " + wide(text(warning));
        const int row = ListView_GetNextItem(refFiles, -1, LVNI_SELECTED);
        const auto &files = discovery.get("files").array_items();
        if (row >= 0 && static_cast<size_t>(row) < files.size()) {
          const auto &file = files[static_cast<size_t>(row)];
          value += L"\n" + wt(file, "filename") + L"\n" + wt(file, "detail");
          value += L"\nIntegrity: Ensembl CHECKSUMS (BSD sum) and gzip CRC are checked; "
                   L"local SHA-256 hashes are recorded. BSD sum is not a cryptographic signature.";
        }
      }
      if (value.empty())
        value = L"Select a species, then Find files. Genome, annotation and transcript files "
                L"are tied to the selected release and assembly. Downloads are unpacked to "
                L"plain local files with a provenance record.";
    }
    SetWindowTextW(refDetails, lines(value).c_str());
    reference_enabled();
  }
  void reference_targets() {
    refTargets = Json::array();
    if (!refWindow)
      return;
    SendMessageW(refTarget, CB_RESETCONTENT, 0, 0);
    const auto &record = reference_local_record(), &file = reference_local_file();
    if (ready && !refBusy && !refActionPending && !packBusy && !busy &&
        !closing && !showingHistory && !getstr(file, "id").empty() &&
        record.get("available").boolean(true))
      reference_send("references/targets", object({{"record_id", getstr(record, "id")},
                                                   {"file_id", getstr(file, "id")}}));
    reference_details();
  }
  void reference_refresh(const Json &previous) {
    if (!refWindow)
      return;
    refRebuilding = true;
    if (previous.get("releases").dump() != refState.get("releases").dump()) {
      auto selectedRelease = control_text(refRelease);
      SendMessageW(refRelease, CB_RESETCONTENT, 0, 0);
      int selectedIndex = -1, index = 0;
      for (const auto &release : refState.get("releases").array_items()) {
        auto label = wide(release.is_object() ? getstr(release, "release", getstr(release, "id"))
                                             : text(release));
        SendMessageW(refRelease, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(label.c_str()));
        if (label == selectedRelease || (selectedRelease.empty() && label == L"116"))
          selectedIndex = index;
        ++index;
      }
      if (index == 0) {
        SendMessageW(refRelease, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"116"));
        index = 1;
      }
      SendMessageW(refRelease, CB_SETCURSEL, selectedIndex < 0 ? 0 : selectedIndex, 0);
    }
    if (previous.get("species").dump() != refState.get("species").dump()) {
      ListView_DeleteAllItems(refSpecies);
      for (const auto &species : refState.get("species").array_items()) {
        LVITEMW row{};
        row.mask = LVIF_TEXT;
        row.iItem = ListView_GetItemCount(refSpecies);
        auto label = wt(species, "name", getstr(species, "id"));
        row.pszText = label.data();
        ListView_InsertItem(refSpecies, &row);
        auto assembly = wt(species, "assembly") + L" · " + wt(species, "release"),
             accession = wt(species, "assembly_accession");
        ListView_SetItemText(refSpecies, row.iItem, 1, assembly.data());
        ListView_SetItemText(refSpecies, row.iItem, 2, accession.data());
      }
      if (ListView_GetItemCount(refSpecies))
        ListView_SetItemState(refSpecies, 0, LVIS_SELECTED | LVIS_FOCUSED,
                             LVIS_SELECTED | LVIS_FOCUSED);
    }
    if (previous.get("discovery").dump() != refState.get("discovery").dump()) {
      ListView_DeleteAllItems(refFiles);
      for (const auto &file : refState.get("discovery").get("files").array_items()) {
        LVITEMW row{};
        row.mask = LVIF_TEXT;
        row.iItem = ListView_GetItemCount(refFiles);
        auto label = wt(file, "label", getstr(file, "kind"));
        row.pszText = label.data();
        ListView_InsertItem(refFiles, &row);
        auto filename = wt(file, "filename"), size = download_size(file.get("bytes").integer());
        ListView_SetItemText(refFiles, row.iItem, 1, filename.data());
        ListView_SetItemText(refFiles, row.iItem, 2, size.data());
      }
    }
    if (previous.get("local").dump() != refState.get("local").dump()) {
      // Resolve previous row identities against the previous snapshot, not the new one.
      std::string keepRecord, keepFile;
      int selectedRow = ListView_GetNextItem(refLocal, -1, LVNI_SELECTED);
      if (selectedRow >= 0 && static_cast<size_t>(selectedRow) < refLocalRows.size()) {
        const auto pair = refLocalRows[static_cast<size_t>(selectedRow)];
        const auto &oldRecords = previous.get("local").array_items();
        if (pair.first < oldRecords.size()) {
          const auto &old = oldRecords[pair.first];
          keepRecord = getstr(old, "id");
          if (pair.second < old.get("files").array_items().size())
            keepFile = getstr(old.get("files").array_items()[pair.second], "id");
        }
      }
      ListView_DeleteAllItems(refLocal);
      refLocalRows.clear();
      const auto &records = refState.get("local").array_items();
      selectedRow = -1;
      for (size_t r = 0; r < records.size(); ++r) {
        const auto &record = records[r];
        const auto &files = record.get("files").array_items();
        for (size_t f = 0; f < files.size(); ++f) {
          const auto &file = files[f];
          LVITEMW row{};
          row.mask = LVIF_TEXT;
          row.iItem = static_cast<int>(refLocalRows.size());
          auto label = reference_species(record);
          if (!record.get("available").boolean(true))
            label += L" · unavailable";
          row.pszText = label.data();
          ListView_InsertItem(refLocal, &row);
          auto assembly = wt(record, "assembly") + L" · " + wt(record, "release"),
               kind = wt(file, "label", getstr(file, "kind")),
               size = download_size(file.get("bytes").integer());
          ListView_SetItemText(refLocal, row.iItem, 1, assembly.data());
          ListView_SetItemText(refLocal, row.iItem, 2, kind.data());
          ListView_SetItemText(refLocal, row.iItem, 3, size.data());
          if (getstr(record, "id") == keepRecord && getstr(file, "id") == keepFile)
            selectedRow = row.iItem;
          refLocalRows.push_back({r, f});
        }
      }
      if (selectedRow < 0 && !refLocalRows.empty())
        selectedRow = 0;
      if (selectedRow >= 0)
        ListView_SetItemState(refLocal, selectedRow, LVIS_SELECTED | LVIS_FOCUSED,
                             LVIS_SELECTED | LVIS_FOCUSED);
      refTargets = Json::array();
      SendMessageW(refTarget, CB_RESETCONTENT, 0, 0);
    }
    refRebuilding = false;
    reference_details();
  }
  void reference_notice() {
    if (!refWindow)
      return;
    auto value = wt(refOperation, "message", getstr(refState, "notice"));
    if (value.empty())
      value = L"Search and download contact Ensembl. Analysis files stay on this computer.";
    const auto omitted = refState.get("omitted_local").integer();
    if (omitted > 0)
      value += L"  " + std::to_wstring(omitted) +
               L" older bundles are outside the library display limit; their files remain on disk.";
    const auto bytes = refOperation.get("bytes").integer(),
               total = refOperation.get("total").integer();
    if (refBusy && bytes > 0)
      value += L"  " + download_size(bytes) +
               (total > 0 ? L" / " + download_size(total) : L"");
    SetWindowTextW(refNotice, value.c_str());
    SendMessageW(refProgress, PBM_SETRANGE32, 0, 1000);
    SendMessageW(refProgress, PBM_SETPOS,
                 total > 0 ? static_cast<WPARAM>(std::clamp(
                   1000.0 * static_cast<double>(bytes) / static_cast<double>(total),
                   0.0, 1000.0)) : 0, 0);
    ShowWindow(refProgress, refBusy ? SW_SHOW : SW_HIDE);
    SetWindowTextW(refClose, refBusy ? L"Hide" : L"Close");
  }
  void reference_layout() {
    if (!refWindow)
      return;
    RECT rect{};
    GetClientRect(refWindow, &rect);
    const int w = MulDiv(rect.right, 96, refDpi), h = MulDiv(rect.bottom, 96, refDpi);
    auto put = [&](HWND control, int x, int y, int cw, int ch) {
      MoveWindow(control, MulDiv(x, refDpi, 96), MulDiv(y, refDpi, 96),
                 MulDiv(std::max(1, cw), refDpi, 96),
                 MulDiv(std::max(1, ch), refDpi, 96), TRUE);
    };
    const bool local = TabCtrl_GetCurSel(refTab) == 1;
    put(refTab, 18, 14, w - 36, 30);
    put(refIntro, 18, 54, w - 36, 43);
    SetWindowTextW(refIntro, local
      ? L"Downloaded references are local files. Select one, choose a compatible input in "
        L"your current workspace, then Use for input."
      : L"Ensembl archive · release-pinned genomes and annotations. Release 116 is the final "
        L"classic release; newer Ensembl data is not included in this provider.");
    // Reserve the details panel and two visible gaps before sizing the lists.
    // Independent bottom offsets previously overlapped details and destination
    // controls by 15 logical pixels, including at the minimum window size.
    const int destinationTop = h - 119, detailsHeight = 76,
              onlineDetailsTop = destinationTop - 12 - detailsHeight,
              available = std::max(0, onlineDetailsTop - 12 - 190),
              speciesHeight = available * 2 / 5,
              filesTop = 190 + speciesHeight, filesHeight = available - speciesHeight;
    put(refReleaseLabel, 18, 107, 56, 28);
    put(refRelease, 78, 104, 84, 250);
    put(refQuery, 174, 104, w - 302, 32);
    put(refSearch, w - 116, 104, 98, 32);
    put(refSpecies, 18, 148, w - 36, speciesHeight);
    put(refDiscover, 18, 154 + speciesHeight, 132, 30);
    put(refFiles, 18, filesTop, w - 36, filesHeight);
    put(refLocal, 18, 104, w - 36, h - 360);
    put(refDetails, 18, onlineDetailsTop, w - 36, detailsHeight);
    if (local) {
      put(refDetails, 18, h - 244, w - 36, 114);
      put(refTargetLabel, 18, h - 116, 116, 30);
      put(refTarget, 138, h - 119, w - 432, 240);
      put(refUse, w - 282, h - 119, 128, 32);
      put(refOpen, w - 142, h - 119, 124, 32);
    } else {
      put(refDestinationLabel, 18, destinationTop + 3, 66, 30);
      put(refDestination, 88, destinationTop, w - 400, 32);
      put(refBrowse, w - 300, destinationTop, 128, 32);
      put(refDownload, w - 160, destinationTop, 142, 32);
    }
    put(refNotice, 18, h - 74, w - 278, 50);
    put(refCancel, w - 252, h - 74, 128, 32);
    put(refClose, w - 112, h - 74, 94, 32);
    put(refProgress, 18, h - 15, w - 36, 6);
    for (HWND control : {refReleaseLabel, refRelease, refQuery, refSearch, refSpecies,
                         refDiscover, refFiles, refDestinationLabel, refDestination,
                         refBrowse, refDownload})
      ShowWindow(control, local ? SW_HIDE : SW_SHOW);
    for (HWND control : {refLocal, refTargetLabel, refTarget, refUse, refOpen})
      ShowWindow(control, local ? SW_SHOW : SW_HIDE);
    auto column = [&](HWND list, int at, int size) {
      ListView_SetColumnWidth(list, at, MulDiv(size, refDpi, 96));
    };
    column(refSpecies, 0, (w - 70) / 2);
    column(refSpecies, 1, (w - 70) / 4);
    column(refSpecies, 2, (w - 70) / 4);
    column(refFiles, 0, 210);
    column(refFiles, 1, std::max(220, w - 366));
    column(refFiles, 2, 98);
    column(refLocal, 0, std::max(180, (w - 170) / 3));
    column(refLocal, 1, std::max(180, (w - 170) / 3));
    column(refLocal, 2, std::max(180, (w - 170) / 3));
    column(refLocal, 3, 98);
  }
  void reference_fonts() {
    HFONT replacement = CreateFontW(-MulDiv(14, refDpi, 96), 0, 0, 0, FW_NORMAL,
        FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
    EnumChildWindows(refWindow, [](HWND child, LPARAM value) -> BOOL {
      SendMessageW(child, WM_SETFONT, static_cast<WPARAM>(value), TRUE);
      return TRUE;
    }, reinterpret_cast<LPARAM>(replacement));
    if (refFont)
      DeleteObject(refFont);
    refFont = replacement;
  }
  void reference_command(int id, int notification) {
    if (refRebuilding)
      return;
    if (id == REF_CLOSE || id == IDCANCEL) {
      DestroyWindow(refWindow);
      return;
    }
    if (id == REF_DESTINATION || id == REF_TARGET) {
      reference_enabled();
      return;
    }
    if (id == REF_CANCEL && refBusy && !refActionPending &&
        refOperation.get("cancellable").boolean(true)) {
      reference_send("references/cancel");
      return;
    }
    if (!ready || busy || closing || packBusy || packActionPending ||
        refBusy || refActionPending)
      return;
    if ((id == REF_QUERY && notification == EN_CHANGE) || id == REF_RELEASE)
      return;
    if (id == REF_SEARCH || (id == IDOK && TabCtrl_GetCurSel(refTab) == 0)) {
      const auto release = control_text(refRelease);
      if (release.empty())
        return;
      reference_send("references/search", object({{"release", std::stoi(release)},
                                                   {"query", narrow(control_text(refQuery))}}));
    } else if (id == REF_DISCOVER) {
      const auto &species = reference_selected_species();
      if (!getstr(species, "id").empty())
        reference_send("references/discover", object({{"release", species.get("release")},
                            {"species_id", getstr(species, "id")}}));
    } else if (id == REF_BROWSE) {
      const auto path = pick(refWindow, true, false, L"", L"Choose where to store reference downloads");
      if (!path.empty())
        SetWindowTextW(refDestination, path.c_str());
    } else if (id == REF_DOWNLOAD) {
      Json selectedFiles = Json::array();
      const auto &files = refState.get("discovery").get("files").array_items();
      for (size_t i = 0; i < files.size(); ++i)
        if (ListView_GetCheckState(refFiles, static_cast<int>(i)))
          selectedFiles.array_items().push_back(getstr(files[i], "id"));
      if (!selectedFiles.array_items().empty())
        reference_send("references/download", object({
            {"selection_id", getstr(refState.get("discovery"), "selection_id")},
            {"file_ids", selectedFiles}, {"destination", narrow(control_text(refDestination))}}));
    } else if (id == REF_OPEN || id == REF_USE) {
      const auto &record = reference_local_record(), &file = reference_local_file();
      if (getstr(record, "id").empty())
        return;
      if (id == REF_OPEN)
        reference_send("references/open", object({{"record_id", getstr(record, "id")}}));
      else {
        if (!record.get("available").boolean(true))
          return;
        const auto selectedTarget = SendMessageW(refTarget, CB_GETCURSEL, 0, 0);
        const auto &targets = refTargets.array_items();
        if (selectedTarget >= 0 && static_cast<size_t>(selectedTarget) < targets.size()) {
          const auto &target = targets[static_cast<size_t>(selectedTarget)];
          commit_all();
          reference_send("references/use", object({{"record_id", getstr(record, "id")},
              {"file_id", getstr(file, "id")}, {"source_id", getstr(target, "source_id")},
              {"field_id", getstr(target, "field_id")}}));
        }
      }
    }
    reference_enabled();
  }
  static LRESULT CALLBACK reference_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    auto *app = reinterpret_cast<Workspace *>(GetWindowLongPtrW(h, GWLP_USERDATA));
    if (m == WM_NCCREATE) {
      app = static_cast<Workspace *>(reinterpret_cast<CREATESTRUCTW *>(l)->lpCreateParams);
      app->refWindow = h;
      SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(app));
    }
    if (!app)
      return DefWindowProcW(h, m, w, l);
    try {
      switch (m) {
      case WM_COMMAND:
        app->reference_command(LOWORD(w), HIWORD(w));
        return 0;
      case WM_NOTIFY: {
        auto *notice = reinterpret_cast<NMHDR *>(l);
        if (app->refRebuilding)
          return 0;
        if (notice->idFrom == REF_TAB && notice->code == TCN_SELCHANGE) {
          app->reference_layout();
          if (TabCtrl_GetCurSel(app->refTab) == 1)
            app->reference_targets();
          app->reference_details();
        } else if (notice->code == LVN_ITEMCHANGED) {
          if (notice->idFrom == REF_LOCAL) {
            const auto *change = reinterpret_cast<NMLISTVIEW *>(l);
            if ((change->uNewState & LVIS_SELECTED) && !(change->uOldState & LVIS_SELECTED))
              app->reference_targets();
          } else if (notice->idFrom == REF_FILES || notice->idFrom == REF_SPECIES)
            app->reference_details();
        }
        return 0;
      }
      case WM_SIZE:
        app->reference_layout();
        return 0;
      case WM_ACTIVATE:
        if (LOWORD(w) != WA_INACTIVE && app->refTab &&
            TabCtrl_GetCurSel(app->refTab) == 1 && !app->refActionPending)
          app->reference_targets();
        break;
      case WM_DPICHANGED: {
        app->refDpi = HIWORD(w);
        app->reference_fonts();
        const auto *rect = reinterpret_cast<RECT *>(l);
        SetWindowPos(h, nullptr, rect->left, rect->top, rect->right - rect->left,
                     rect->bottom - rect->top, SWP_NOZORDER | SWP_NOACTIVATE);
        app->reference_layout();
        return 0;
      }
      case WM_GETMINMAXINFO: {
        auto *info = reinterpret_cast<MINMAXINFO *>(l);
        info->ptMinTrackSize = {MulDiv(820, app->refDpi, 96), MulDiv(680, app->refDpi, 96)};
        return 0;
      }
      case WM_CTLCOLORSTATIC:
      case WM_CTLCOLOREDIT:
      case WM_CTLCOLORBTN: {
        auto dc = reinterpret_cast<HDC>(w);
        SetTextColor(dc, INK);
        SetBkColor(dc, BACK);
        return reinterpret_cast<LRESULT>(app->background);
      }
      case WM_CLOSE:
        DestroyWindow(h);
        return 0;
      case WM_NCDESTROY:
        app->refWindow = nullptr;
        app->refLocalRows.clear();
        app->refTargets = Json::array();
        SetWindowLongPtrW(h, GWLP_USERDATA, 0);
        return DefWindowProcW(h, m, w, l);
      default:
        break;
      }
    } catch (const std::exception &error) {
      MessageBoxW(h, wide(error.what()).c_str(), L"References", MB_OK | MB_ICONERROR);
    }
    return DefWindowProcW(h, m, w, l);
  }
  void show_references() {
    if (refWindow) {
      ShowWindow(refWindow, SW_RESTORE);
      SetForegroundWindow(refWindow);
      return;
    }
    WNDCLASSEXW klass{sizeof(klass)};
    klass.lpfnWndProc = reference_proc;
    klass.hInstance = instance;
    klass.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    klass.hbrBackground = background;
    klass.lpszClassName = L"WorkbenchReferences070";
    RegisterClassExW(&klass);
    RECT owner{}, area{};
    GetWindowRect(window, &owner);
    MONITORINFO monitor{sizeof(monitor)};
    if (GetMonitorInfoW(MonitorFromWindow(window, MONITOR_DEFAULTTONEAREST), &monitor))
      area = monitor.rcWork;
    else
      SystemParametersInfoW(SPI_GETWORKAREA, 0, &area, 0);
    refDpi = dpi;
    const int w = std::min<int>(px(960), area.right - area.left),
              h = std::min<int>(px(800), area.bottom - area.top),
              x = std::clamp<int>(owner.left + (owner.right - owner.left - w) / 2,
                                  area.left, area.right - w),
              y = std::clamp<int>(owner.top + (owner.bottom - owner.top - h) / 2,
                                  area.top, area.bottom - h);
    refWindow = CreateWindowExW(WS_EX_CONTROLPARENT, klass.lpszClassName,
        L"References · Native Workbench", WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN,
        x, y, w, h, window, nullptr, instance, this);
    if (!refWindow)
      throw std::runtime_error("Could not open reference discovery.");
    refRebuilding = true;
    refTab = make(WC_TABCONTROLW, L"Reference views", WS_TABSTOP, REF_TAB, refWindow);
    for (const auto *label : {L"Find online", L"Downloaded"}) {
      TCITEMW item{};
      item.mask = TCIF_TEXT;
      item.pszText = const_cast<wchar_t *>(label);
      TabCtrl_InsertItem(refTab, TabCtrl_GetItemCount(refTab), &item);
    }
    refIntro = make(L"STATIC", L"", SS_LEFT | SS_NOPREFIX, 650, refWindow);
    refReleaseLabel = make(L"STATIC", L"Release", SS_LEFT, 651, refWindow);
    refRelease = make(L"COMBOBOX", L"", WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
                      REF_RELEASE, refWindow);
    SendMessageW(refRelease, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"116"));
    SendMessageW(refRelease, CB_SETCURSEL, 0, 0);
    refQuery = make(L"EDIT", L"", WS_TABSTOP | ES_AUTOHSCROLL, REF_QUERY,
                   refWindow, WS_EX_CLIENTEDGE);
    SendMessageW(refQuery, EM_SETCUEBANNER, FALSE,
                 reinterpret_cast<LPARAM>(L"Species name, e.g. human or Saccharomyces"));
    refSearch = button(L"Search", REF_SEARCH, refWindow);
    auto list = [&](const wchar_t *title, int id, bool checks,
                    std::initializer_list<const wchar_t *> labels) {
      HWND control = make(WC_LISTVIEWW, title,
          WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
          id, refWindow, WS_EX_CLIENTEDGE);
      ListView_SetExtendedListViewStyle(control, LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER |
          LVS_EX_LABELTIP | (checks ? LVS_EX_CHECKBOXES : 0));
      int index = 0;
      for (const auto *label : labels) {
        LVCOLUMNW column{};
        column.mask = LVCF_TEXT | LVCF_WIDTH;
        column.pszText = const_cast<wchar_t *>(label);
        column.cx = px(150);
        ListView_InsertColumn(control, index++, &column);
      }
      return control;
    };
    refSpecies = list(L"Species and assemblies", REF_SPECIES, false,
                       {L"Species", L"Assembly · release", L"Assembly accession"});
    refDiscover = button(L"Find files", REF_DISCOVER, refWindow);
    refFiles = list(L"Reference files to download", REF_FILES, true,
                     {L"Select files", L"Archive filename", L"Download"});
    refDetails = make(L"EDIT", L"", WS_TABSTOP | ES_MULTILINE | ES_READONLY |
        ES_AUTOVSCROLL | WS_VSCROLL, REF_DETAILS, refWindow, WS_EX_CLIENTEDGE);
    SendMessageW(refDetails, EM_SETLIMITTEXT, 256 * 1024, 0);
    refDestinationLabel = make(L"STATIC", L"Save to", SS_LEFT, 652, refWindow);
    refDestination = make(L"EDIT", root + L"\\user-data\\references", WS_TABSTOP |
        ES_AUTOHSCROLL, REF_DESTINATION, refWindow, WS_EX_CLIENTEDGE);
    refBrowse = button(L"Choose folder...", REF_BROWSE, refWindow);
    refDownload = button(L"Download selected", REF_DOWNLOAD, refWindow);
    refLocal = list(L"Downloaded reference files", REF_LOCAL, false,
                     {L"Species", L"Assembly · release", L"Reference file", L"Size"});
    refTargetLabel = make(L"STATIC", L"Workspace input", SS_LEFT, 653, refWindow);
    refTarget = make(L"COMBOBOX", L"", WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
                     REF_TARGET, refWindow);
    refUse = button(L"Use for input", REF_USE, refWindow);
    refOpen = button(L"Open folder", REF_OPEN, refWindow);
    refCancel = button(L"Cancel operation", REF_CANCEL, refWindow);
    refProgress = make(PROGRESS_CLASSW, L"Reference download progress", PBS_SMOOTH,
                       REF_PROGRESS, refWindow);
    refNotice = make(L"STATIC", L"Loading local references...", SS_LEFT | SS_NOPREFIX,
                     REF_NOTICE, refWindow);
    refClose = button(L"Close", REF_CLOSE, refWindow);
    refRebuilding = false;
    reference_fonts();
    reference_refresh(Json::object());
    reference_layout();
    reference_notice();
    ShowWindow(refWindow, SW_SHOW);
    SetFocus(refQuery);
    reference_send("references/list");
  }
  void reference_response(const std::string &method, const Json &result) {
    refPollFailed = false;
    if (result.contains("operation"))
      refOperation = result.get("operation");
    const bool wasBusy = refBusy;
    refBusy = refOperation.get("active").boolean();
    if (result.get("local").is_array()) {
      Json previous = refState;
      refState = result;
      reference_refresh(previous);
    }
    if (result.contains("model"))
      snapshot(result.get("model"));
    if (method == "references/targets" && refWindow) {
      refTargets = result.get("targets");
      SendMessageW(refTarget, CB_RESETCONTENT, 0, 0);
      for (const auto &target : refTargets.array_items()) {
        auto label = wt(target, "label") + L" (" + wt(target, "type") + L")";
        if (!getstr(target, "current_path").empty())
          label += L" · replace current file";
        SendMessageW(refTarget, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(label.c_str()));
      }
      if (!refTargets.array_items().empty())
        SendMessageW(refTarget, CB_SETCURSEL, 0, 0);
      else
        SetWindowTextW(refNotice, wt(result, "notice",
            "No compatible input in this workspace. Add a tool that accepts this reference first.").c_str());
    } else if (method == "references/open") {
      const auto path = wt(result, "path");
      if (!path.empty() && reinterpret_cast<INT_PTR>(ShellExecuteW(
            refWindow ? refWindow : window, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL)) <= 32)
        message(L"Windows could not open the reference folder.");
    } else if (method == "references/use") {
      status_text(L"The downloaded reference is assigned to the selected workspace input.");
      if (refWindow)
        SetWindowTextW(refNotice, L"Reference assigned. Its download provenance will be retained with the run.");
    } else {
      reference_notice();
      if (refBusy)
        status_text(L"References: " + wt(refOperation, "message"));
      else if (wasBusy && !getstr(refOperation, "message").empty())
        status_text(wt(refOperation, "message"));
      if ((wasBusy || method == "references/download") && !refBusy &&
          getstr(refOperation, "action") == "download" &&
          refOperation.get("success").boolean() && refWindow) {
        TabCtrl_SetCurSel(refTab, 1);
        reference_layout();
        reference_targets();
      }
    }
    reference_enabled();
    enabled();
    if (closing && !refBusy && !busy && !packBusy)
      send("shutdown");
  }
  void controls() {
    HMENU menu = CreateMenu(), file = CreatePopupMenu(),
          view = CreatePopupMenu();
    for (auto pair : std::vector<std::pair<UINT, const wchar_t *>>{
             {FILE_NEW, L"New workspace"},
             {FILE_EXAMPLE, L"Load bundled example"},
             {FILE_SAVE_PIPELINE, L"Save pipeline..."},
             {FILE_SAVE_PRESET, L"Save selected tool settings..."},
             {FILE_LOAD, L"Load saved pipeline or settings..."},
             {FILE_HISTORY, L"Run history..."},
             {FILE_IMPORT, L"Manage tools..."},
             {MANAGE_REFERENCES, L"References..."},
             {FILE_CHECK, L"Check installation"},
             {FILE_EXIT, L"Exit"}})
      AppendMenuW(file, MF_STRING, pair.first, pair.second);
    AppendMenuW(view, MF_STRING, VIEW_METHODS, L"Planned methods...");
    AppendMenuW(view, MF_STRING, VIEW_LOG, L"Run log...");
    AppendMenuW(view, MF_STRING, OPEN_RESULTS, L"Open results folder");
    AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(file), L"File");
    AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(view), L"View");
    SetMenu(window, menu);
    name = make(L"EDIT", L"Untitled analysis", WS_TABSTOP | ES_AUTOHSCROLL,
                NAME, nullptr, WS_EX_CLIENTEDGE);
    output = make(L"EDIT", root + L"\\results", WS_TABSTOP | ES_AUTOHSCROLL,
                  OUTPUT, nullptr, WS_EX_CLIENTEDGE);
    browse = button(L"Results folder...", BROWSE_OUTPUT);
    manageReferences = button(L"References...", MANAGE_REFERENCES);
    run = button(L"Review and run", RUN);
    cancel = button(L"Cancel run", CANCEL);
    review = button(L"Methods", REVIEW);
    back = button(L"Back to workspace", BACK_WORKSPACE);
    search = make(L"EDIT", L"", WS_TABSTOP | ES_AUTOHSCROLL, SEARCH, nullptr,
                  WS_EX_CLIENTEDGE);
    SendMessageW(search, EM_SETCUEBANNER, FALSE,
                 reinterpret_cast<LPARAM>(L"Search tasks or tools"));
    category = make(L"COMBOBOX", L"",
                    WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL, CATEGORY);
    tasks = make(WC_LISTVIEWW, L"Available tasks",
                 WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
                 TASKS, nullptr, WS_EX_CLIENTEDGE);
    ListView_SetExtendedListViewStyle(
        tasks, LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_LABELTIP);
    LVCOLUMNW col{};
    col.mask = LVCF_TEXT | LVCF_WIDTH;
    col.pszText = const_cast<wchar_t *>(L"Task library");
    col.cx = px(195);
    ListView_InsertColumn(tasks, 0, &col);
    add = button(L"Add selected task", ADD);
    manageTools = button(L"Manage tools...", MANAGE_TOOLS);
    clearFilter = button(L"Show all tasks", CLEAR_FILTER);
    steps = make(WC_LISTVIEWW, L"Pipeline steps by dependency level",
                 WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
                 STEPS, nullptr, WS_EX_CLIENTEDGE);
    ListView_SetExtendedListViewStyle(
        steps, LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_LABELTIP);
    col.pszText = const_cast<wchar_t *>(L"Steps");
    col.cx = px(188);
    ListView_InsertColumn(steps, 0, &col);
    remove = button(L"Remove", REMOVE);
    undo = button(L"Undo", UNDO);
    up = button(L"Move up", UP);
    down = button(L"Move down", DOWN);
    dag = CreateWindowExW(
        0, L"WorkbenchNativeSurface051", L"Pipeline dependency diagram",
        WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_HSCROLL | WS_VSCROLL |
            WS_CLIPSIBLINGS,
        0, 0, 1, 1, window, reinterpret_cast<HMENU>(DAG), instance, this);
    form = CreateWindowExW(
        WS_EX_CONTROLPARENT, L"WorkbenchNativeSurface051",
        L"Step inputs and options",
        WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
        0, 0, 1, 1, window, reinterpret_cast<HMENU>(FORM), instance, this);
    status = make(L"STATIC", L"Starting the local analysis engine...", SS_LEFT,
                  STATUS);
    SetTimer(window, 1, 400, nullptr);
    layout();
  }
  void layout() {
    RECT rc{};
    GetClientRect(window, &rc);
    width = std::max(1, MulDiv(rc.right, 96, dpi));
    height = std::max(1, MulDiv(rc.bottom, 96, dpi));
    int side = 216, main = side + 24, mw = std::max(400, width - main - 18),
        top = 108, dh = std::clamp(height / 3, 145, 255), body = top + dh + 12,
        bh = std::max(90, height - body - 54),
        sw = std::clamp(mw / 3, 164, 230);
    place(name, 18, 14, std::max(250, width - 454), 32);
    place(review, width - 418, 14, 92, 32);
    place(run, width - 316, 14, 156, 32);
    place(cancel, width - 150, 14, 132, 32);
    place(browse, 18, 57, 138, 32);
    place(output, 166, 57, std::max(100, width - 320), 32);
    place(manageReferences, width - 142, 57, 124, 32);
    place(search, 18, top, side - 18, 32);
    place(category, 18, top + 40, side - 18, 230);
    const bool filtering = !getstr(state, "pendingSource").empty();
    place(tasks, 18, top + 80 + (filtering ? 38 : 0), side - 18,
          std::max(70, height - top - 204 - (filtering ? 38 : 0)));
    ShowWindow(clearFilter, filtering ? SW_SHOW : SW_HIDE);
    place(add, 18, height - 112, side - 18, 32);
    place(manageTools, 18, height - 72, side - 18, 32);
    place(clearFilter, 18, top + 80, side - 18, 30);
    place(dag, main, top, mw, dh);
    place(steps, main, body, sw, bh - 78);
    place(remove, main, body + bh - 70, sw / 2 - 4, 30);
    place(undo, main + sw / 2 + 4, body + bh - 70, sw / 2 - 4, 30);
    place(up, main, body + bh - 34, sw / 2 - 4, 30);
    place(down, main + sw / 2 + 4, body + bh - 34, sw / 2 - 4, 30);
    place(form, main + sw + 12, body, mw - sw - 12, bh);
    place(status, 18, height - 30, width - 36, 24);
    place(back, main, top + 5, 170, 28);
    ShowWindow(back, showingHistory ? SW_SHOW : SW_HIDE);
    ListView_SetColumnWidth(tasks, 0, px(side - 40));
    ListView_SetColumnWidth(steps, 0, px(sw - 22));
    layout_fields();
    InvalidateRect(dag, nullptr, FALSE);
    InvalidateRect(window, nullptr, TRUE);
  }
  void enabled() {
    bool edit = ready && !busy && !packBusy && !packActionPending &&
                !refBusy && !refActionPending &&
                !showingHistory && !closing &&
                !activeRequest && outgoing.empty();
    for (HWND h :
         {name, search, category, tasks, add, steps, remove, undo, up, down})
      EnableWindow(h, edit);
    EnableWindow(undo, edit && state.get("canUndo").boolean());
    EnableWindow(run, edit && !graph().get("nodes").array_items().empty());
    EnableWindow(review, ready && !activeRequest && outgoing.empty());
    EnableWindow(cancel, busy && !closing);
    EnableWindow(output, !busy && !packBusy && !packActionPending && !refBusy && !refActionPending);
    EnableWindow(browse, !busy && !packBusy && !packActionPending && !refBusy && !refActionPending);
    EnableWindow(manageTools, ready && !busy && !closing && !showingHistory);
    EnableWindow(manageReferences, ready && !busy && !closing && !showingHistory);
    for (const auto &f : fields) {
      EnableWindow(f.h, edit || f.kind.rfind("historical-", 0) == 0);
      if (f.button)
        EnableWindow(f.button, edit);
    }
    HMENU m = GetMenu(window);
    for (UINT id : {FILE_NEW, FILE_EXAMPLE, FILE_SAVE_PIPELINE,
                    FILE_SAVE_PRESET, FILE_LOAD, FILE_CHECK})
      EnableMenuItem(m, id, MF_BYCOMMAND | (edit ? MF_ENABLED : MF_GRAYED));
    EnableMenuItem(m, FILE_IMPORT, MF_BYCOMMAND |
                   (ready && !busy && !closing && !showingHistory ? MF_ENABLED : MF_GRAYED));
    EnableMenuItem(m, MANAGE_REFERENCES, MF_BYCOMMAND |
                   (ready && !busy && !closing && !showingHistory ? MF_ENABLED : MF_GRAYED));
    DrawMenuBar(window);
    pack_enabled();
    reference_enabled();
  }
  void refresh_tasks(bool categories = false) {
    rebuilding = true;
    if (categories) {
      SendMessageW(category, CB_RESETCONTENT, 0, 0);
      SendMessageW(category, CB_ADDSTRING, 0,
                   reinterpret_cast<LPARAM>(L"All categories"));
      std::set<std::wstring> cats;
      for (const auto &entry : catalog.get("tools").object_items())
        cats.insert(wt(entry.second, "category", "Other"));
      for (const auto &cat : cats)
        SendMessageW(category, CB_ADDSTRING, 0,
                     reinterpret_cast<LPARAM>(cat.c_str()));
      SendMessageW(category, CB_SETCURSEL, 0, 0);
    }
    const auto query = lower(control_text(search)),
               cat = control_text(category);
    ListView_DeleteAllItems(tasks);
    taskIds.clear();
    std::set<std::string> compatible;
    if (state.get("compatibleTools").is_array())
      for (const auto &c : state.get("compatibleTools").array_items())
        compatible.insert(text(c));
    const bool filtered = !getstr(state, "pendingSource").empty();
    for (const auto &entry : catalog.get("tools").object_items()) {
      const auto &t = entry.second;
      std::wstring label = wt(t, "name"),
                   categoryName = wt(t, "category", "Other");
      if (!query.empty() &&
          lower(label + L" " + wt(t, "packId") + L" " + wt(t, "description"))
                  .find(query) == std::wstring::npos)
        continue;
      if (!cat.empty() && cat != L"All categories" && cat != categoryName)
        continue;
      if (filtered && !compatible.count(entry.first))
        continue;
      LVITEMW row{};
      row.mask = LVIF_TEXT;
      row.iItem = static_cast<int>(taskIds.size());
      row.pszText = label.data();
      ListView_InsertItem(tasks, &row);
      taskIds.push_back(entry.first);
    }
    rebuilding = false;
  }
  void refresh_steps() {
    rebuilding = true;
    ListView_DeleteAllItems(steps);
    ListView_RemoveAllGroups(steps);
    ListView_EnableGroupView(steps, TRUE);
    stepIds.clear();
    auto rank = ranks();
    std::map<int, std::vector<const Json *>> groups;
    for (const auto &n : graph().get("nodes").array_items())
      groups[rank[getstr(n, "id")]].push_back(&n);
    int selectedIndex = -1;
    for (const auto &level : groups) {
      std::wstring header = L"Dependency level " + std::to_wstring(level.first);
      LVGROUP group{};
      group.cbSize = sizeof(group);
      group.mask = LVGF_HEADER | LVGF_GROUPID;
      group.pszHeader = header.data();
      group.iGroupId = level.first;
      ListView_InsertGroup(steps, -1, &group);
      for (const auto *n : level.second) {
        std::string id = getstr(*n, "id");
        std::wstring label = wide(display_id(id) + " · " + node_name(*n));
        LVITEMW row{};
        row.mask = LVIF_TEXT | LVIF_GROUPID;
        row.iGroupId = level.first;
        row.iItem = static_cast<int>(stepIds.size());
        row.pszText = label.data();
        ListView_InsertItem(steps, &row);
        if (id == selected)
          selectedIndex = row.iItem;
        stepIds.push_back(id);
      }
    }
    if (selectedIndex >= 0) {
      ListView_SetItemState(steps, selectedIndex, LVIS_SELECTED | LVIS_FOCUSED,
                            LVIS_SELECTED | LVIS_FOCUSED);
      ListView_EnsureVisible(steps, selectedIndex, FALSE);
    }
    rebuilding = false;
  }
  int measured(const std::wstring &value, int width_, HFONT f) {
    if (value.empty())
      return 0;
    HDC dc = GetDC(form);
    HFONT old = static_cast<HFONT>(SelectObject(dc, f));
    RECT r{0, 0, px(std::max(20, width_)), 0};
    DrawTextW(dc, value.c_str(), -1, &r,
              DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX);
    SelectObject(dc, old);
    ReleaseDC(form, dc);
    return std::max(20, MulDiv(r.bottom, 96, dpi));
  }
  HWND form_text(const std::wstring &value, bool strong = false) {
    HWND h = make(L"STATIC", value, SS_LEFT, 0, form);
    SendMessageW(h, WM_SETFONT, reinterpret_cast<WPARAM>(strong ? bold : font),
                 FALSE);
    formControls.push_back(h);
    Field f;
    f.h = h;
    f.kind = "label";
    f.initial = value;
    f.schema = object({{"strong", strong}});
    fields.push_back(std::move(f));
    return h;
  }
  void add_field(std::string kind, std::string key, const Json &schema,
                 const std::string &value, const std::string &source = {},
                 const std::string &port = {}) {
    Field f;
    f.kind = std::move(kind);
    f.key = std::move(key);
    f.node = selected;
    f.source = source;
    f.port = port;
    f.schema = schema;
    if (f.kind == "source" && getstr(f.schema, "type") == "files")
      f.schema["type"] = "file";
    f.initial = wide(value);
    int id = FIELD_BASE + static_cast<int>(fields.size()) * 2;
    const auto type = getstr(f.schema, "type", "text");
    if (type == "boolean") {
      f.h = make(L"BUTTON", wt(schema, "label"), WS_TABSTOP | BS_AUTOCHECKBOX,
                 id, form);
      SendMessageW(f.h, BM_SETCHECK,
                   value == "true" ? BST_CHECKED : BST_UNCHECKED, 0);
    } else if (type == "choice") {
      f.h = make(L"COMBOBOX", L"", WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
                 id, form);
      int chosen = -1;
      for (const auto &c : schema.get("choices").array_items()) {
        auto label = wt(c, "label", getstr(c, "value"));
        int at = static_cast<int>(SendMessageW(
            f.h, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(label.c_str())));
        if (getstr(c, "value") == value)
          chosen = at;
      }
      SendMessageW(f.h, CB_SETCURSEL, chosen, 0);
    } else {
      f.h = make(L"EDIT", f.initial,
                 WS_TABSTOP | (type == "files"
                                   ? ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL
                                   : ES_AUTOHSCROLL),
                 id, form, WS_EX_CLIENTEDGE);
      SendMessageW(f.h, EM_SETLIMITTEXT,
                   type == "files" ? 8 * 1024 * 1024 : 32767, 0);
    }
    formControls.push_back(f.h);
    if (f.kind == "source" &&
        (type == "file" || type == "files" || type == "directory")) {
      f.button = button(L"Browse...", id + 1, form);
      formControls.push_back(f.button);
    }
    fieldIds[id] = fields.size();
    fieldIds[id + 1] = fields.size();
    SetWindowSubclass(f.h, field_proc, 1, reinterpret_cast<DWORD_PTR>(this));
    if (f.button)
      SetWindowSubclass(f.button, field_proc, 1,
                        reinterpret_cast<DWORD_PTR>(this));
    fields.push_back(std::move(f));
  }
  void form_action(const std::wstring &title, const std::string &kind,
                   const std::string &key = {},
                   const Json &schema = Json::object()) {
    Field f;
    f.kind = kind;
    f.key = key;
    f.node = selected;
    f.schema = schema;
    int id = FIELD_BASE + static_cast<int>(fields.size()) * 2;
    f.h = button(title.c_str(), id, form);
    formControls.push_back(f.h);
    fieldIds[id] = fields.size();
    SetWindowSubclass(f.h, field_proc, 1, reinterpret_cast<DWORD_PTR>(this));
    fields.push_back(std::move(f));
  }
  void rebuild_inspector() {
    rebuilding = true;
    for (HWND h : formControls)
      DestroyWindow(h);
    formControls.clear();
    fields.clear();
    fieldIds.clear();
    const auto &inspector = state.get("inspector");
    if (showingHistory) {
      form_text(L"Recorded run — read only", true);
      form_text(wt(historyRun, "status") + L"\n" + wt(historyRun, "message") +
                L"\n" + wt(historyRun, "folder"));
      form_text(L"This diagram is taken from the saved run graph. Your "
                L"editable workspace is preserved.");
      form_action(L"Show recorded methods", "historical-methods");
      form_action(L"Open results folder", "historical-open");
    } else if (selected.empty() || inspector.is_null()) {
      form_text(L"Build your analysis", true);
      form_text(L"Search the task library and add a tool. Each input names its "
                L"exact file slot or producing step. Shared outputs form "
                L"branches automatically.");
      form_text(L"Drag a task from the library into the diagram, or select it "
                L"and choose Add selected task.");
    } else {
      form_text(wide(display_id(selected)) + L" · " + wt(inspector, "name"),
                true);
      const auto &t = inspector.get("tool");
      form_text(wt(t, "description"));
      for (const auto &node : graph().get("nodes").array_items()) {
        if (getstr(node, "id") != selected || !getstr(tool(node), "id").empty())
          continue;
        const auto operation = getstr(node, "tool");
        Json pin = node.get("pin").is_object() ? node.get("pin") : Json::object();
        if (getstr(pin, "packId").empty())
          pin["packId"] = operation.substr(0, operation.find('/'));
        form_text(L"Required tool pack is unavailable", true);
        form_text(wt(pin, "packId") + L"  ·  version " +
                  wt(pin, "packVersion", "not recorded") +
                  L"\nInstall the original pack to restore this step. Its saved settings "
                  L"and connections have been preserved.");
        form_action(L"Find required pack in Manage tools...", "manage-required-pack", "", pin);
        form_action(L"Show required pack details...", "required-pack-details", "", pin);
        break;
      }
      form_text(L"Step name", true);
      add_field("rename", "name", object({{"type", "text"}}),
                getstr(inspector, "name"));
      for (const auto &port : inspector.get("ports").array_items()) {
        const auto pid = getstr(port, "id");
        form_text(wt(port, "label"), true);
        std::wstring sources;
        const Json &refs = port.get("refs");
        for (const auto &ref : refs.array_items()) {
          if (!sources.empty())
            sources += L"\n";
          sources += wt(ref, "label", getstr(ref, "ref", text(ref)));
        }
        form_text(sources.empty()
                      ? L"No source connected — choose a named input or output."
                      : L"From: " + sources);
        form_action(L"Choose connected source(s)...", "connect", pid, port);
        form_action(L"Add a new file input slot", "add-source", pid, port);
        if (!getstr(port, "help").empty())
          form_text(wt(port, "help"));
      }
      std::set<std::string> seen;
      const Json &sourceList = inspector.contains("sources")
                                   ? inspector.get("sources")
                                   : state.get("sources");
      for (const auto &source : sourceList.array_items()) {
        const auto sid = getstr(source, "id");
        if (sid.empty() || !seen.insert(sid).second)
          continue;
        form_text(wide(display_id(sid)) + L" · " + wt(source, "label"), true);
        for (const auto &field : source.get("fields").array_items()) {
          form_text(wt(field, "label", getstr(field, "id")));
          add_field("source", getstr(field, "id"), field,
                    getstr(field, "value"), sid);
          if (!getstr(field, "help").empty())
            form_text(wt(field, "help"));
        }
      }
      if (!inspector.get("params").array_items().empty())
        form_text(L"Tool settings", true);
      for (const auto &param : inspector.get("params").array_items()) {
        if (getstr(param, "type") != "boolean")
          form_text(wt(param, "label", getstr(param, "id")));
        add_field("param", getstr(param, "id"), param,
                  getstr(param, "value", getstr(param, "default")));
        if (!getstr(param, "help").empty())
          form_text(wt(param, "help"));
      }
      const Json *viewNode = nullptr;
      for (const auto &n : state.get("nodes").array_items())
        if (getstr(n, "id") == selected) {
          viewNode = &n;
          break;
        }
      if (viewNode) {
        form_text(L"Named outputs", true);
        for (const auto &out : viewNode->get("outputs").array_items()) {
          form_text(wt(out, "label"), true);
          std::wstring consumers;
          for (const auto &c : out.get("consumers").array_items()) {
            if (!consumers.empty())
              consumers += L"\n";
            consumers += wt(c, "displayId", getstr(c, "nodeId")) + L" · " +
                         wt(c, "name") + L" → " + wt(c, "portLabel");
          }
          form_text(consumers.empty() ? L"No downstream consumer yet."
                                      : L"Used by: " + consumers);
          form_action(L"Use this output in another task...", "use-output",
                      getstr(out, "ref"));
        }
      }
    }
    rebuilding = false;
    layout_fields();
    enabled();
  }
  void layout_fields() {
    if (!form)
      return;
    RECT r{};
    GetClientRect(form, &r);
    int fw = std::max(80, MulDiv(r.right, 96, dpi)),
        fh = std::max(30, MulDiv(r.bottom, 96, dpi)), y = 12;
    for (auto &f : fields) {
      f.y = y;
      if (f.kind == "label")
        f.height = measured(f.initial, fw - 34,
                            f.schema.get("strong").boolean() ? bold : font);
      else if (getstr(f.schema, "type") == "files")
        f.height = 76;
      else if (getstr(f.schema, "type") == "boolean")
        f.height =
            std::max(34, measured(wt(f.schema, "label"), fw - 52, font) + 8);
      else
        f.height = 34;
      y += f.height + (f.kind == "label" ? 8 : 12);
    }
    formExtent = y + 8;
    formScroll = std::clamp(formScroll, 0, std::max(0, formExtent - fh));
    SCROLLINFO si{sizeof(si),
                  SIF_RANGE | SIF_PAGE | SIF_POS | SIF_DISABLENOSCROLL};
    si.nMax = formExtent - 1;
    si.nPage = fh;
    si.nPos = formScroll;
    SetScrollInfo(form, SB_VERT, &si, TRUE);
    for (auto &f : fields) {
      int fw_ = fw - 32 - (f.button ? 94 : 0);
      place(f.h, 12, f.y - formScroll, fw_,
            getstr(f.schema, "type") == "choice" ? 260 : f.height);
      if (f.button)
        place(f.button, fw - 108, f.y - formScroll, 88, 34);
    }
    InvalidateRect(form, nullptr, TRUE);
  }
  std::string field_value(const Field &f) const {
    auto type = getstr(f.schema, "type");
    if (type == "boolean")
      return SendMessageW(f.h, BM_GETCHECK, 0, 0) == BST_CHECKED ? "true"
                                                                 : "false";
    if (type == "choice") {
      int i = static_cast<int>(SendMessageW(f.h, CB_GETCURSEL, 0, 0));
      const auto &a = f.schema.get("choices").array_items();
      return i >= 0 && static_cast<size_t>(i) < a.size()
                 ? getstr(a[static_cast<size_t>(i)], "value")
                 : "";
    }
    return narrow(control_text(f.h));
  }
  void commit(Field &f) {
    if (rebuilding || busy || showingHistory)
      return;
    const auto value = field_value(f);
    if (value == narrow(f.initial))
      return;
    f.initial = wide(value);
    if (f.kind == "param")
      model("set_param",
            object({{"nodeId", f.node}, {"paramId", f.key}, {"value", value}}));
    else if (f.kind == "source")
      model("bind_files", object({{"sourceId", f.source},
                                  {"files", object({{f.key, value}})}}));
    else if (f.kind == "rename")
      model("rename_step", object({{"nodeId", f.node}, {"name", value}}));
  }
  void commit_all() {
    if (rebuilding || busy || showingHistory || !ready)
      return;
    Json params = Json::object(), files = Json::object(),
         payload = object({{"nodeId", selected}});
    bool changed = false;
    for (const auto &f : fields) {
      if (f.kind != "param" && f.kind != "source" && f.kind != "rename")
        continue;
      auto value = field_value(f);
      if (value == narrow(f.initial))
        continue;
      changed = true;
      if (f.kind == "param")
        params[f.key] = value;
      else if (f.kind == "source")
        files[f.source][f.key] = value;
      else
        payload["name"] = value;
    }
    if (narrow(control_text(name)) != getstr(state.get("graph"), "name")) {
      payload["graphName"] = narrow(control_text(name));
      changed = true;
    }
    if (!changed)
      return;
    payload["params"] = params;
    payload["files"] = files;
    auto encoded = payload.dump();
    if (encoded == submittedFields)
      return;
    submittedFields = encoded;
    model("apply_fields", payload);
  }

  void show_text(const std::wstring &title, const std::wstring &value) {
    Modal m;
    m.owner = window;
    m.font = font;
    m.mode = 2;
    m.title = title;
    m.value = value;
    m.message = L"Select and copy text, or use Copy text.";
    m.confirm = L"Done";
    m.show();
  }
  void connection(const Field &f) {
    Modal m;
    m.owner = window;
    m.font = font;
    m.title = L"Choose sources for " + wt(f.schema, "label");
    m.mode = 0;
    m.multiple = f.schema.get("max").integer(1) > 1;
    m.message =
        m.multiple
            ? L"Ctrl-click to select multiple named sources. Apply replaces "
              L"this input's connections."
            : L"Choose the exact input slot or named output for this input.";
    m.confirm = L"Apply";
    std::vector<std::string> refs;
    if (!m.multiple) {
      refs.push_back("");
      m.labels.push_back(L"No source connected");
    }
    std::set<std::string> current;
    for (const auto &v : f.schema.get("refs").array_items())
      current.insert(v.is_string() ? v.string() : getstr(v, "ref"));
    for (const auto &v : f.schema.get("sources").array_items())
      current.insert(getstr(v, "ref", getstr(v, "id")));
    for (const auto &c : f.schema.get("choices").array_items()) {
      const auto ref = getstr(c, "ref");
      refs.push_back(ref);
      m.labels.push_back(wt(c, "label", ref));
      if (current.count(ref))
        m.selected.push_back(static_cast<int>(refs.size() - 1));
    }
    if (m.show()) {
      commit_all();
      Json::Array chosen;
      for (int n : m.selected)
        if (n >= 0 && static_cast<size_t>(n) < refs.size() &&
            !refs[static_cast<size_t>(n)].empty())
          chosen.emplace_back(refs[static_cast<size_t>(n)]);
      model("connect", object({{"nodeId", f.node},
                               {"portId", f.key},
                               {"refs", Json(chosen)}}));
    }
  }
  void field_command(int id, int notification) {
    auto found = fieldIds.find(id);
    if (found == fieldIds.end())
      return;
    const size_t idx = found->second;
    if (idx >= fields.size())
      return;
    Field &f = fields[idx];
    const bool secondary = f.button && id == GetDlgCtrlID(f.button);
    if (notification == EN_KILLFOCUS || notification == CBN_SELCHANGE ||
        (notification == BN_CLICKED && getstr(f.schema, "type") == "boolean"))
      return;
    if (notification != BN_CLICKED)
      return;
    if (secondary) {
      const auto path = pick(window, getstr(f.schema, "type") == "directory",
                             false, wt(f.schema, "filter", "All files|*.*"),
                             L"Choose " + wt(f.schema, "label"));
      if (!path.empty()) {
        SetWindowTextW(f.h, path.c_str());
        commit_all();
      }
      return;
    }
    const Field copy = f;
    if (f.kind == "connect") {
      connection(copy);
      return;
    }
    commit_all();
    if (f.kind == "add-source")
      model("add_source", object({{"nodeId", f.node}, {"portId", f.key}}));
    else if (f.kind == "use-output")
      model("use_output", object({{"ref", f.key}}));
    else if (f.kind == "historical-methods")
      show_text(
          L"Recorded methods",
          wt(historyRun, "methods",
             getstr(historyRun, "methods_planned",
                    "Recorded methods are available in the run folder.")));
    else if (f.kind == "historical-open")
      send("open", object({{"run_id", getstr(historyRun, "run_id")}}));
    else if (f.kind == "manage-required-pack") {
      requiredPack = copy.schema;
      show_pack_manager();
      SetWindowTextW(packSearch, wt(requiredPack, "packId").c_str());
      SendMessageW(packFilter, CB_SETCURSEL, 0, 0);
      refresh_packs();
      pack_notice();
    } else if (f.kind == "required-pack-details")
      show_text(L"Required tool pack",
                L"Pack: " + wt(copy.schema, "packId") +
                    L"\nVersion: " + wt(copy.schema, "packVersion", "not recorded") +
                    L"\nManifest SHA-256: " + wt(copy.schema, "manifestSha256", "not recorded") +
                    L"\n\nThis exact manifest is required to reproduce the saved step.");
  }
  void snapshot(Json value) {
    if (value.contains("model"))
      value = value.get("model");
    state = std::move(value);
    if (state.contains("catalog"))
      catalog = state.get("catalog");
    selected =
        getstr(state, "selected", getstr(state.get("inspector"), "nodeId"));
    rebuilding = true;
    SetWindowTextW(name,
                   wt(state.get("graph"), "name", "Untitled analysis").c_str());
    rebuilding = false;
    refresh_tasks();
    refresh_steps();
    rebuild_inspector();
    layout();
    InvalidateRect(dag, nullptr, FALSE);
    enabled();
  }
  void add_task() {
    int i = ListView_GetNextItem(tasks, -1, LVNI_SELECTED);
    if (i < 0 || static_cast<size_t>(i) >= taskIds.size())
      return;
    commit_all();
    const auto pendingSource = getstr(state, "pendingSource");
    Json payload = object({{"toolId", taskIds[static_cast<size_t>(i)]}});
    if (!pendingSource.empty())
      payload["fromRef"] = pendingSource;
    model("add_tool", payload);
  }
  void save(bool pipeline) {
    if (!pipeline && selected.empty()) {
      message(L"Select a step to save its tool settings.");
      return;
    }
    Modal m;
    m.owner = window;
    m.font = font;
    m.mode = 1;
    m.title = pipeline ? L"Save pipeline" : L"Save tool settings";
    m.message = L"Choose a name for reuse. File bindings are excluded.";
    m.value =
        pipeline ? control_text(name) : wt(state.get("inspector"), "name");
    m.confirm = L"Save";
    if (!m.show())
      return;
    commit_all();
    Json request = object({{"name", narrow(m.value)},
                           {"kind", pipeline ? "pipeline" : "preset"}});
    if (!pipeline)
      request["nodeId"] = selected;
    send("save", request);
  }
  void load_saved(const Json &data) {
    Modal m;
    m.owner = window;
    m.font = font;
    m.title = L"Load saved analysis or tool settings";
    m.message = L"Pipelines restore the graph; tool settings apply to the "
                L"selected compatible step.";
    m.confirm = L"Load";
    std::vector<std::pair<std::string, std::string>> items;
    for (const char *kind : {"pipelines", "presets"})
      for (const auto &item : data.get(kind).array_items()) {
        m.labels.push_back(std::wstring(kind == std::string("pipelines")
                                            ? L"Pipeline · "
                                            : L"Tool settings · ") +
                           wt(item, "name"));
        items.push_back(
            {kind == std::string("pipelines") ? "pipeline" : "preset",
             getstr(item, "id")});
      }
    if (m.show() && !m.selected.empty()) {
      const auto &item = items[static_cast<size_t>(m.selected.front())];
      send("load", object({{"kind", item.first},
                           {"id", item.second},
                           {"node_id", selected}}));
    }
  }
  void history(const Json &data) {
    Modal m;
    m.owner = window;
    m.font = font;
    m.title = L"Run history";
    m.message = data.get("omitted").integer() > 0
                    ? L"Recent runs are shown; older records remain in their "
                      L"result folders."
                    : L"Open a recorded run to inspect its original diagram "
                      L"and status.";
    m.confirm = L"View run";
    const Json &runs = data.is_array() ? data : data.get("runs");
    for (const auto &r : runs.array_items())
      m.labels.push_back(wt(r, "started_at") + L" · " + wt(r, "status") +
                         L" · " + wt(r, "folder"));
    if (m.show() && !m.selected.empty()) {
      send("run/get",
           object({{"run_id", getstr(runs.array_items()[static_cast<size_t>(
                                         m.selected.front())],
                                     "run_id")}}));
    }
  }
  void update_run(const Json &value) {
    runState = value;
    if (getstr(value, "run_id").empty() && value.contains("run"))
      runState = value.get("run");
    const auto status_ = getstr(runState, "status");
    busy = status_ == "preparing" || status_ == "running" ||
           status_ == "cancelling";
    status_text(wide(status_) + L" · " + wt(runState, "message"));
    logs.clear();
    if (runState.get("events").is_array())
      for (const auto &e : runState.get("events").array_items())
        if (!getstr(e, "message").empty())
          logs += wt(e, "message") + L"\n";
    if (runState.get("events_omitted").integer() > 0)
      logs = L"Some earlier events are omitted here. Full step logs remain in "
             L"the recorded results folder.\n\n" +
             logs;
    if (logs.size() > 250000)
      logs = logs.substr(logs.size() - 250000);
    enabled();
    InvalidateRect(dag, nullptr, FALSE);
    if (closing && !busy && !refBusy && !packBusy)
      send("shutdown");
  }
  void response(const Json &response_) {
    long long id = response_.get("id").integer();
    if (id != activeRequest)
      return;
    activeRequest = 0;
    const auto found = pending.find(id);
    std::string method = found == pending.end() ? "" : found->second;
    if (found != pending.end())
      pending.erase(found);
    if (method == "status")
      pollPending = false;
    if (method == "packs/status")
      packPollPending = false;
    if (method.rfind("packs/", 0) == 0 && method != "packs/list" &&
        method != "packs/status")
      packActionPending = false;
    if (method == "references/status")
      refPollPending = false;
    else if (method.rfind("references/", 0) == 0)
      refActionPending = false;
    if (!response_.get("ok").boolean()) {
      if (method.rfind("references/", 0) == 0) {
        refOperation["message"] = getstr(response_, "error", "Reference discovery returned an error.");
        reference_notice();
        if (!refPollFailed || method != "references/status")
          MessageBoxW(refWindow ? refWindow : window,
                      wt(response_, "error", "Reference discovery returned an error.").c_str(),
                      L"References", MB_OK | MB_ICONERROR);
        if (method == "references/status")
          refPollFailed = true;
        enabled();
        return;
      }
      if (method.rfind("packs/", 0) == 0) {
        if (method != "packs/status") {
          packReloadAfterOperation = false;
          packListAfterOperation = false;
        }
        packOperation["message"] = getstr(response_, "error", "The tool manager returned an error.");
        pack_notice();
        if (!packPollFailed || method != "packs/status")
          MessageBoxW(packWindow ? packWindow : window,
                      wt(response_, "error", "The tool manager returned an error.").c_str(),
                      L"Manage tools", MB_OK | MB_ICONERROR);
        if (method == "packs/status")
          packPollFailed = true;
        enabled();
        return;
      }
      if (method == "status" && closing) {
        send("shutdown");
        return;
      }
      reviewThenRun = false;
      submittedFields.clear();
      outgoing.clear();
      pending.clear();
      message(wt(response_, "error", "The local engine returned an error."));
      if (method == "init")
        ready = false;
      enabled();
      return;
    }
    const auto &result = response_.get("result");
    if (method.rfind("packs/", 0) == 0) {
      pack_response(method, result);
    } else if (method.rfind("references/", 0) == 0) {
      reference_response(method, result);
    } else if (method == "init") {
      ready = true;
      if (result.contains("catalog"))
        catalog = result.get("catalog");
      snapshot(result);
      refresh_tasks(true);
      status_text(L"Ready. All computation remains on this computer.");
      if (autoCheck) {
        autoCheck = false;
        send("check",
             object({{"output_folder", narrow(control_text(output))}}));
      }
    } else if (method == "model" || method == "load" || method == "example") {
      submittedFields.clear();
      snapshot(result);
      if (!getstr(state, "pendingSource").empty())
        status_text(L"Task library now shows tools compatible with the "
                    L"selected named output.");
    } else if (method == "review") {
      std::wstring content;
      for (const auto &issue : result.get("issues").array_items())
        content += wt(issue, "severity") + L": " + wt(issue, "message") + L"\n";
      content += L"\n" + wt(result, "methods");
      bool start = reviewThenRun;
      reviewThenRun = false;
      Modal m;
      m.owner = window;
      m.font = font;
      m.mode = 2;
      m.title = L"Review planned methods";
      m.message = L"Review the selected tools, settings and input "
                  L"provenance before running.";
      m.value = content;
      m.confirm =
          start && result.get("valid").boolean() ? L"Run analysis" : L"Done";
      if (m.show() && start && result.get("valid").boolean())
        send("run", object({{"output_folder", narrow(control_text(output))}}));
    } else if (method == "run" || method == "check") {
      runId = getstr(result, "run_id");
      busy = true;
      status_text(L"Preparing local analysis...");
      enabled();
    } else if (method == "run/get") {
      historyRun = result;
      showingHistory = true;
      refresh_steps();
      rebuild_inspector();
      layout();
      status_text(L"Recorded run: " + wt(historyRun, "status") +
                  L". Editable workspace preserved.");
      enabled();
    } else if (method == "status")
      update_run(result);
    else if (method == "cancel")
      update_run(result);
    else if (method == "saved")
      load_saved(result);
    else if (method == "history")
      history(result);
    else if (method == "save")
      status_text(L"Saved for reuse without input file bindings.");
    else if (method == "import") {
      if (result.get("success").boolean()) {
        status_text(L"Tool pack import completed.");
        if (result.contains("model"))
          snapshot(result.get("model"));
        else
          send("init");
      } else
        message(wt(result, "message", "The tool pack could not be imported."));
    } else if (method == "shutdown") {
      if (!result.get("closed").boolean(true))
        MessageBoxW(window,
                    L"The engine could not finish every cleanup operation. "
                    L"Workbench will close the remaining processes; incomplete "
                    L"results stay in their run folders.",
                    L"Local cleanup", MB_OK | MB_ICONWARNING);
      close_host_window();
    }
  }
  void command(int id, int notification) {
    if (rebuilding)
      return;
    if (id >= FIELD_BASE) {
      field_command(id, notification);
      return;
    }
    if (id == SEARCH && notification == EN_CHANGE) {
      refresh_tasks();
      return;
    }
    if (id == CATEGORY && notification == CBN_SELCHANGE) {
      refresh_tasks();
      return;
    }
    // Native edit notifications are not actions. Keep the draft intact while
    // typing; the next explicit operation commits it transactionally.
    if (id == NAME || id == OUTPUT || id == SEARCH || id == CATEGORY)
      return;
    if (id == ADD) {
      add_task();
      return;
    }
    if (id == CLEAR_FILTER) {
      commit_all();
      model("select", object({{"nodeId", selected}}));
      return;
    }
    if (id == BROWSE_OUTPUT) {
      auto path = pick(window, true, false, L"",
                       L"Choose the parent folder for new run results");
      if (!path.empty())
        SetWindowTextW(output, path.c_str());
      return;
    }
    if (id == CANCEL && !runId.empty()) {
      send("cancel", object({{"run_id", runId}}));
      return;
    }
    if (id == BACK_WORKSPACE) {
      showingHistory = false;
      historyRun = Json::object();
      snapshot(state);
      layout();
      return;
    }
    if (id == FILE_EXIT) {
      SendMessageW(window, WM_CLOSE, 0, 0);
      return;
    }
    if (id == VIEW_LOG) {
      show_text(L"Run log", logs.empty() ? L"No run log yet." : logs);
      return;
    }
    if (id == OPEN_RESULTS) {
      const auto identity =
          showingHistory ? getstr(historyRun, "run_id") : runId;
      if (!identity.empty())
        send("open", object({{"run_id", identity}}));
      return;
    }
    if (id == FILE_HISTORY) {
      commit_all();
      send("history");
      return;
    }
    if (id == FILE_SAVE_PIPELINE) {
      save(true);
      return;
    }
    if (id == FILE_SAVE_PRESET) {
      save(false);
      return;
    }
    if ((id == FILE_IMPORT || id == MANAGE_TOOLS) && ready && !busy &&
        !showingHistory && !closing) {
      commit_all();
      show_pack_manager();
      return;
    }
    if (id == MANAGE_REFERENCES && ready && !busy && !showingHistory && !closing) {
      if (!refBusy && !refActionPending && !packBusy && !packActionPending)
        commit_all();
      show_references();
      return;
    }
    if (busy || packBusy || packActionPending || refBusy || refActionPending || showingHistory) {
      if (id == REVIEW || id == VIEW_METHODS)
        show_text(
            L"Recorded methods",
            wt(showingHistory ? historyRun : runState, "methods",
               getstr(showingHistory ? historyRun : runState, "methods_planned",
                      "Methods are saved in the run folder.")));
      return;
    }
    commit_all();
    switch (id) {
    case REMOVE:
      if (!selected.empty())
        model("remove_step", object({{"nodeId", selected}}));
      break;
    case UNDO:
      model("undo");
      break;
    case UP:
    case DOWN:
      if (!selected.empty())
        model("move_step", object({{"nodeId", selected},
                                   {"direction", id == UP ? "up" : "down"}}));
      break;
    case RUN:
      reviewThenRun = true;
      send("review");
      break;
    case REVIEW:
    case VIEW_METHODS:
      reviewThenRun = false;
      send("review");
      break;
    case FILE_NEW:
      model("clear");
      break;
    case FILE_EXAMPLE:
      send("example");
      break;
    case FILE_SAVE_PIPELINE:
      save(true);
      break;
    case FILE_SAVE_PRESET:
      save(false);
      break;
    case FILE_LOAD:
      send("saved");
      break;
    case FILE_CHECK:
      send("check", object({{"output_folder", narrow(control_text(output))}}));
      break;
    default:
      break;
    }
  }
  void paint_dag() {
    PAINTSTRUCT ps{};
    HDC dc = BeginPaint(dag, &ps);
    struct End {
      HWND h;
      PAINTSTRUCT *ps;
      ~End() { EndPaint(h, ps); }
    } end{dag, &ps};
    RECT client{};
    GetClientRect(dag, &client);
    HDC mem = CreateCompatibleDC(dc);
    HBITMAP bitmap = CreateCompatibleBitmap(dc, std::max<LONG>(1, client.right),
                                            std::max<LONG>(1, client.bottom));
    HGDIOBJ old = SelectObject(mem, bitmap);
    FillRect(mem, &client, paper);
    hits.clear();
    int vw = std::max(1, MulDiv(client.right, 96, dpi)),
        vh = std::max(1, MulDiv(client.bottom, 96, dpi));
    auto rank = ranks();
    std::map<int, std::vector<std::string>> levels;
    std::map<std::string, const Json *> nodes;
    std::set<std::string> usedSources;
    for (const auto &node : graph().get("nodes").array_items())
      for (const auto &port : node.get("inputs").object_items())
        for (const auto &ref : port.second.array_items())
          if (text(ref).rfind("input-", 0) == 0)
            usedSources.insert(text(ref));
    for (const auto &s : graph().get("sources").array_items()) {
      const auto id = getstr(s, "id");
      if (!usedSources.count(id))
        continue;
      levels[0].push_back(id);
      nodes[id] = &s;
    }
    for (const auto &n : graph().get("nodes").array_items()) {
      const auto id = getstr(n, "id");
      levels[rank[id]].push_back(id);
      nodes[id] = &n;
    }
    size_t maximum = 1;
    for (const auto &level : levels)
      maximum = std::max(maximum, level.second.size());
    dagWidth = std::max(vw, static_cast<int>(maximum) * 218 + 32);
    int maxRank = levels.empty() ? 0 : levels.rbegin()->first;
    dagHeight = std::max(vh, 98 + maxRank * 112);
    dagX = std::clamp(dagX, 0, std::max(0, dagWidth - vw));
    dagY = std::clamp(dagY, 0, std::max(0, dagHeight - vh));
    for (int bar : {SB_HORZ, SB_VERT}) {
      SCROLLINFO si{sizeof(si), SIF_RANGE | SIF_PAGE | SIF_POS};
      si.nMax = (bar == SB_HORZ ? dagWidth : dagHeight) - 1;
      si.nPage = bar == SB_HORZ ? vw : vh;
      si.nPos = bar == SB_HORZ ? dagX : dagY;
      SetScrollInfo(dag, bar, &si, TRUE);
    }
    std::map<std::string, RECT> boxes;
    for (const auto &level : levels) {
      int total = static_cast<int>(level.second.size()) * 218;
      int start = (dagWidth - total) / 2 + 9;
      for (size_t i = 0; i < level.second.size(); ++i) {
        int x = start + static_cast<int>(i) * 218, y = 16 + level.first * 112;
        boxes[level.second[i]] = {x, y, x + 200,
                                  y + (level.first == 0 ? 64 : 82)};
      }
    }
    {
      Gdiplus::Graphics g(mem);
      g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
      g.ScaleTransform(dpi / 96.f, dpi / 96.f);
      g.TranslateTransform(static_cast<float>(-dagX),
                           static_cast<float>(-dagY));
      for (const auto &n : graph().get("nodes").array_items()) {
        auto target = boxes.find(getstr(n, "id"));
        if (target == boxes.end())
          continue;
        for (const auto &port : n.get("inputs").object_items())
          for (const auto &r : port.second.array_items()) {
            std::string ref = text(r), source = ref.substr(0, ref.find("::"));
            auto from = boxes.find(source);
            if (from == boxes.end())
              continue;
            bool highlight = getstr(n, "id") == selected || source == selected;
            Gdiplus::Pen pen(highlight ? Gdiplus::Color(255, 58, 93, 140)
                                       : Gdiplus::Color(255, 177, 191, 207),
                             highlight ? 2.4f : 1.3f);
            float x1 = (from->second.left + from->second.right) / 2.f,
                  y1 = static_cast<float>(from->second.bottom),
                  x2 = (target->second.left + target->second.right) / 2.f,
                  y2 = static_cast<float>(target->second.top);
            g.DrawBezier(&pen, x1, y1, x1, (y1 + y2) / 2, x2, (y1 + y2) / 2, x2,
                         y2);
            g.DrawLine(&pen, x2, y2, x2 - 4, y2 - 7);
            g.DrawLine(&pen, x2, y2, x2 + 4, y2 - 7);
          }
      }
      for (const auto &entry : boxes) {
        const auto &box = entry.second;
        bool isSource = entry.first.rfind("input-", 0) == 0;
        bool active = entry.first == selected;
        rounded(g, static_cast<float>(box.left), static_cast<float>(box.top),
                static_cast<float>(box.right - box.left),
                static_cast<float>(box.bottom - box.top), 10,
                active     ? RGB(229, 236, 246)
                : isSource ? RGB(240, 244, 249)
                           : PAPER,
                active ? ACCENT : BORDER);
        RECT screen{px(box.left - dagX), px(box.top - dagY),
                    px(box.right - dagX), px(box.bottom - dagY)};
        hits.push_back({screen, entry.first, isSource});
      }
    }
    SetBkMode(mem, TRANSPARENT);
    SetTextColor(mem, INK);
    for (const auto &entry : boxes) {
      const auto &n = *nodes[entry.first];
      bool source = entry.first.rfind("input-", 0) == 0;
      auto box = entry.second;
      RECT line{px(box.left + 10 - dagX), px(box.top + 7 - dagY),
                px(box.right - 10 - dagX), px(box.bottom - 7 - dagY)};
      std::wstring title =
          wide(display_id(entry.first) + " · " +
               (source ? getstr(n, "label", getstr(n, "type")) : node_name(n)));
      SelectObject(mem, bold);
      DrawTextW(mem, title.c_str(), -1, &line,
                DT_WORDBREAK | DT_NOPREFIX | DT_END_ELLIPSIS);
    }
    if (nodes.empty()) {
      SelectObject(mem, font);
      SetTextColor(mem, MUTED);
      RECT textBox{px(22), px(20), client.right - px(22),
                   client.bottom - px(10)};
      const wchar_t *prompt =
          L"Your pipeline diagram\n\nAdd a task to begin. Branches sharing "
          L"an input stay on the same dependency level.";
      DrawTextW(mem, prompt, -1, &textBox, DT_WORDBREAK | DT_NOPREFIX);
    }
    BitBlt(dc, 0, 0, client.right, client.bottom, mem, 0, 0, SRCCOPY);
    SelectObject(mem, old);
    DeleteObject(bitmap);
    DeleteDC(mem);
  }
  void scroll(HWND h, int bar, int action, int delta = 0) {
    RECT r{};
    GetClientRect(h, &r);
    int extent = h == form        ? formExtent
                 : bar == SB_HORZ ? dagWidth
                                  : dagHeight,
        page = MulDiv(bar == SB_HORZ ? r.right : r.bottom, 96, dpi),
        *value = h == form        ? &formScroll
                 : bar == SB_HORZ ? &dagX
                                  : &dagY;
    SCROLLINFO si{sizeof(si), SIF_TRACKPOS};
    GetScrollInfo(h, bar, &si);
    if (delta)
      *value += delta;
    else
      switch (action) {
      case SB_LINEUP:
        *value -= 32;
        break;
      case SB_LINEDOWN:
        *value += 32;
        break;
      case SB_PAGEUP:
        *value -= page;
        break;
      case SB_PAGEDOWN:
        *value += page;
        break;
      case SB_THUMBTRACK:
      case SB_THUMBPOSITION:
        *value = si.nTrackPos;
        break;
      case SB_TOP:
        *value = 0;
        break;
      case SB_BOTTOM:
        *value = extent;
        break;
      default:
        break;
      }
    *value = std::clamp(*value, 0, std::max(0, extent - page));
    if (h == form)
      layout_fields();
    else
      InvalidateRect(dag, nullptr, FALSE);
  }
  static LRESULT CALLBACK surface(HWND h, UINT m, WPARAM w, LPARAM l) {
    auto *app =
        reinterpret_cast<Workspace *>(GetWindowLongPtrW(h, GWLP_USERDATA));
    if (m == WM_NCCREATE) {
      app = static_cast<Workspace *>(
          reinterpret_cast<CREATESTRUCTW *>(l)->lpCreateParams);
      SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(app));
    }
    if (!app)
      return DefWindowProcW(h, m, w, l);
    try {
      if (m == WM_PAINT && GetDlgCtrlID(h) == DAG) {
        app->paint_dag();
        return 0;
      }
      if (m == WM_ERASEBKGND) {
        RECT r{};
        GetClientRect(h, &r);
        FillRect(reinterpret_cast<HDC>(w), &r, app->paper);
        return 1;
      }
      if (m == WM_VSCROLL || m == WM_HSCROLL) {
        app->scroll(h, m == WM_HSCROLL ? SB_HORZ : SB_VERT, LOWORD(w));
        return 0;
      }
      if (m == WM_MOUSEWHEEL) {
        app->scroll(h, (GET_KEYSTATE_WPARAM(w) & MK_SHIFT) ? SB_HORZ : SB_VERT,
                    0, -GET_WHEEL_DELTA_WPARAM(w) * 48 / WHEEL_DELTA);
        return 0;
      }
      if (m == WM_LBUTTONUP && h == app->dag) {
        POINT p{GET_X_LPARAM(l), GET_Y_LPARAM(l)};
        for (const auto &hit : app->hits)
          if (PtInRect(&hit.box, p)) {
            if (!hit.source && !app->showingHistory) {
              app->commit_all();
              app->model("select", object({{"nodeId", hit.id}}));
            } else if (hit.source)
              app->status_text(wide(display_id(hit.id)) +
                               L" is a named shared input. Select a "
                               L"consuming step to edit its binding.");
            return 0;
          }
      }
      if (m == WM_COMMAND || m == WM_CTLCOLORSTATIC || m == WM_CTLCOLOREDIT ||
          m == WM_CTLCOLORBTN)
        return SendMessageW(app->window, m, w, l);
    } catch (const std::exception &e) {
      app->message(wide(e.what()));
    }
    return DefWindowProcW(h, m, w, l);
  }
  LRESULT handle(UINT m, WPARAM w, LPARAM l) {
    switch (m) {
    case WM_CREATE:
      dpi = GetDpiForWindow(window);
      fonts();
      controls();
      PostMessageW(window, WM_APP + 1, 0, 0);
      return 0;
    case WM_APP + 1:
      host.start(root, window, HOST_MESSAGE);
      send("init");
      return 0;
    case HOST_MESSAGE: {
      std::unique_ptr<std::string> bytes(reinterpret_cast<std::string *>(l));
      if (w) {
        ready = false;
        busy = false;
        packBusy = false;
        packActionPending = false;
        refBusy = false;
        refActionPending = false;
        status_text(L"The local engine stopped. Restart Workbench; "
                    L"incomplete runs remain recorded.");
        if (closing)
          close_host_window();
        else
          message(L"The local analysis engine stopped unexpectedly.\n\nRestart "
                  L"Workbench. Diagnostic information is saved in "
                  L"user-data\\desktop-host.stderr.txt.");
        enabled();
      } else {
        response(Json::parse(*bytes));
        if (IsWindow(window)) {
          pump();
          enabled();
        }
      }
      return 0;
    }
    case WM_SIZE:
      layout();
      return 0;
    case WM_DPICHANGED:
      dpi = HIWORD(w);
      fonts();
      {
        auto *r = reinterpret_cast<RECT *>(l);
        SetWindowPos(window, nullptr, r->left, r->top, r->right - r->left,
                     r->bottom - r->top, SWP_NOZORDER | SWP_NOACTIVATE);
      }
      layout();
      return 0;
    case WM_GETMINMAXINFO: {
      auto *p = reinterpret_cast<MINMAXINFO *>(l);
      p->ptMinTrackSize = {px(800), px(560)};
      return 0;
    }
    case WM_KEYDOWN:
      if (w == VK_ESCAPE && !busy && !showingHistory &&
          !getstr(state, "pendingSource").empty()) {
        model("select", object({{"nodeId", selected}}));
        status_text(L"Showing all tasks.");
        return 0;
      }
      break;
    case WM_COMMAND:
      command(LOWORD(w), HIWORD(w));
      return 0;
    case WM_NOTIFY: {
      auto *n = reinterpret_cast<NMHDR *>(l);
      if (n->idFrom == TASKS && n->code == NM_DBLCLK) {
        add_task();
        return 0;
      }
      if (n->idFrom == TASKS && n->code == LVN_BEGINDRAG) {
        int i = reinterpret_cast<NMLISTVIEW *>(l)->iItem;
        if (i >= 0 && static_cast<size_t>(i) < taskIds.size()) {
          dragTool = taskIds[static_cast<size_t>(i)];
          SetCapture(window);
          status_text(L"Drop in the diagram or step list to add this task.");
        }
        return 0;
      }
      if (n->idFrom == STEPS && n->code == LVN_ITEMCHANGED && !rebuilding &&
          !showingHistory) {
        auto *item = reinterpret_cast<NMLISTVIEW *>(l);
        if ((item->uNewState & LVIS_SELECTED) &&
            !(item->uOldState & LVIS_SELECTED) && item->iItem >= 0 &&
            static_cast<size_t>(item->iItem) < stepIds.size()) {
          commit_all();
          model(
              "select",
              object({{"nodeId", stepIds[static_cast<size_t>(item->iItem)]}}));
        }
      }
      return 0;
    }
    case WM_LBUTTONUP:
      if (!dragTool.empty()) {
        const auto droppedTool = dragTool;
        ReleaseCapture();
        POINT p{GET_X_LPARAM(l), GET_Y_LPARAM(l)};
        ClientToScreen(window, &p);
        RECT r{};
        GetWindowRect(dag, &r);
        RECT s{};
        GetWindowRect(steps, &s);
        if (PtInRect(&r, p) || PtInRect(&s, p)) {
          commit_all();
          model("add_tool", object({{"toolId", droppedTool}}));
        }
        dragTool.clear();
        return 0;
      }
      break;
    case WM_CAPTURECHANGED:
      dragTool.clear();
      return 0;
    case WM_TIMER:
      if (closing && closeStarted && GetTickCount64() - closeStarted > 25000) {
        status_text(L"The engine did not finish shutting down. Forcing "
                    L"cleanup; this run remains interrupted.");
        MessageBoxW(
            window,
            L"The local operation did not stop within 25 seconds. Workbench will "
            L"close its process group now.\n\nCompleted references are preserved. "
            L"Incomplete analysis runs will be marked interrupted when reopened.",
            L"Force local cleanup", MB_OK | MB_ICONWARNING);
        close_host_window();
        return 0;
      }
      if (ready && !runId.empty() && busy && !pollPending &&
          GetTickCount64() - lastPoll > 350) {
        lastPoll = GetTickCount64();
        pollPending = true;
        send("status", object({{"run_id", runId}}));
      }
      if (ready && packBusy && !packPollPending && !packActionPending &&
          GetTickCount64() - lastPackPoll > (packPollFailed ? 3000 : 650)) {
        lastPackPoll = GetTickCount64();
        pack_send("packs/status");
      }
      if (ready && refBusy && !refPollPending && !refActionPending &&
          GetTickCount64() - lastRefPoll > (refPollFailed ? 3000 : 650)) {
        lastRefPoll = GetTickCount64();
        reference_send("references/status");
      }
      return 0;
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORBTN: {
      HDC dc = reinterpret_cast<HDC>(w);
      SetTextColor(dc, INK);
      SetBkMode(dc, TRANSPARENT);
      return reinterpret_cast<LRESULT>(
          GetParent(reinterpret_cast<HWND>(l)) == form ? paper : background);
    }
    case WM_PAINT: {
      PAINTSTRUCT ps{};
      HDC dc = BeginPaint(window, &ps);
      RECT r{};
      GetClientRect(window, &r);
      FillRect(dc, &r, background);
      Gdiplus::Graphics g(dc);
      g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
      g.ScaleTransform(dpi / 96.f, dpi / 96.f);
      rounded(g, 230, 100, static_cast<float>(width - 240),
              static_cast<float>(height - 142), 12, PAPER);
      EndPaint(window, &ps);
      return 0;
    }
    case WM_ERASEBKGND:
      return 1;
    case WM_CLOSE:
      if (closing)
        return 0;
      if (refBusy || refActionPending) {
        if (refBusy && !refOperation.get("cancellable").boolean(true)) {
          MessageBoxW(window, L"The reference download record is being saved. Please wait "
                      L"for it to finish before closing Workbench.",
                      L"Finishing reference download", MB_OK | MB_ICONINFORMATION);
          return 0;
        }
        if (MessageBoxW(window, L"A reference operation is in progress. Cancel it and close "
                        L"Workbench?\n\nCompleted references will be preserved.",
                        L"Close Native Workbench",
                        MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES)
          return 0;
        closing = true;
        closeStarted = GetTickCount64();
        reference_send("references/cancel");
        status_text(L"Cancelling the reference operation before closing...");
        enabled();
        return 0;
      }
      if (packBusy || packActionPending) {
        if (packBusy && !packOperation.get("cancellable").boolean(true)) {
          MessageBoxW(window,
                      L"Installation is being committed. Please wait for it to finish "
                      L"before closing Workbench.",
                      L"Finishing tool installation", MB_OK | MB_ICONINFORMATION);
          return 0;
        }
        if (MessageBoxW(window,
                        L"Tools are being managed. Cancel the operation and close "
                        L"Workbench?\n\nInstalled tools will be preserved.",
                        L"Close Native Workbench",
                        MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES)
          return 0;
        closing = true;
        closeStarted = GetTickCount64();
        pack_send("packs/cancel");
        status_text(L"Cancelling the tool operation before closing...");
        enabled();
        return 0;
      }
      if (busy) {
        if (MessageBoxW(window,
                        L"An analysis is running. Cancel it and close "
                        L"Workbench?\n\nChoose No to keep the analysis and "
                        L"window open.",
                        L"Close Native Workbench",
                        MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES)
          return 0;
        closing = true;
        closeStarted = GetTickCount64();
        send("cancel", object({{"run_id", runId}}));
        status_text(
            L"Cancelling and saving the interrupted run before closing...");
        enabled();
        return 0;
      }
      closing = true;
      closeStarted = GetTickCount64();
      if (ready)
        send("shutdown");
      else
        DestroyWindow(window);
      return 0;
    case WM_DESTROY:
      host.stop();
      KillTimer(window, 1);
      PostQuitMessage(0);
      return 0;
    default:
      break;
    }
    return DefWindowProcW(window, m, w, l);
  }
  static LRESULT CALLBACK proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    auto *app =
        reinterpret_cast<Workspace *>(GetWindowLongPtrW(h, GWLP_USERDATA));
    if (m == WM_NCCREATE) {
      app = static_cast<Workspace *>(
          reinterpret_cast<CREATESTRUCTW *>(l)->lpCreateParams);
      app->window = h;
      SetWindowLongPtrW(h, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(app));
    }
    if (!app)
      return DefWindowProcW(h, m, w, l);
    try {
      return app->handle(m, w, l);
    } catch (const std::exception &e) {
      app->message(wide(e.what()));
      return m == WM_CREATE ? -1 : 0;
    } catch (...) {
      app->message(L"The interface encountered an unexpected error.");
      return m == WM_CREATE ? -1 : 0;
    }
  }

public:
  ~Workspace() {
    host.stop();
    for (HFONT f : {font, bold, small, refFont})
      if (f)
        DeleteObject(f);
    if (paper)
      DeleteObject(paper);
    if (background)
      DeleteObject(background);
    MSG msg{};
    while (PeekMessageW(&msg, nullptr, HOST_MESSAGE, HOST_MESSAGE, PM_REMOVE))
      delete reinterpret_cast<std::string *>(msg.lParam);
  }
  int run_app(HINSTANCE inst, bool check, const std::wstring &windowClass) {
    instance = inst;
    autoCheck = check;
    root = bw::executable_folder();
    CreateDirectoryW(bw::native_path(root + L"\\results").c_str(), nullptr);
    paper = CreateSolidBrush(PAPER);
    background = CreateSolidBrush(BACK);
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = proc;
    wc.hInstance = inst;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hIcon = LoadIconW(nullptr, IDI_APPLICATION);
    wc.hbrBackground = background;
    wc.lpszClassName = windowClass.c_str();
    if (!RegisterClassExW(&wc))
      throw std::runtime_error("Could not register workspace window.");
    wc.lpfnWndProc = surface;
    wc.lpszClassName = L"WorkbenchNativeSurface051";
    if (!RegisterClassExW(&wc))
      throw std::runtime_error("Could not register workspace surface.");
    RECT area{};
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &area, 0);
    HWND h = CreateWindowExW(
        WS_EX_CONTROLPARENT, windowClass.c_str(), L"Native Workbench",
        WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, CW_USEDEFAULT, CW_USEDEFAULT,
        std::min<LONG>(1240, area.right - area.left),
        std::min<LONG>(880, area.bottom - area.top), nullptr, nullptr, inst,
        this);
    if (!h)
      return 1;
    ShowWindow(h, SW_SHOW);
    UpdateWindow(h);
    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
      if (!(refWindow && IsDialogMessageW(refWindow, &msg)) &&
          !(packWindow && IsDialogMessageW(packWindow, &msg)) &&
          !IsDialogMessageW(h, &msg)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
      }
    }
    return static_cast<int>(msg.wParam);
  }
};
} // namespace
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
  SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX |
               SEM_NOOPENFILEERRORBOX);
  int count = 0;
  LPWSTR *args = CommandLineToArgvW(GetCommandLineW(), &count);
  bool check = false, classic = false, valid = args && count <= 2;
  if (valid && count == 2) {
    check = std::wstring(args[1]) == L"--check";
    classic = std::wstring(args[1]) == L"--classic";
    valid = check || classic;
  }
  if (args)
    LocalFree(args);
  if (!valid) {
    MessageBoxW(nullptr, L"Supported options are --check and --classic.",
                L"Native Workbench", MB_ICONERROR);
    return 1;
  }
  try {
    if (classic) {
      const auto root = bw::executable_folder(),
                 exe = root + L"\\NativeWorkbenchClassic.exe";
      auto command = quote(exe);
      STARTUPINFOW s{};
      s.cb = sizeof(s);
      PROCESS_INFORMATION p{};
      if (!CreateProcessW(bw::native_path(exe).c_str(), command.data(), nullptr,
                          nullptr, FALSE, 0, nullptr, root.c_str(), &s, &p))
        throw std::runtime_error("Could not start the classic interface.");
      CloseHandle(p.hThread);
      CloseHandle(p.hProcess);
      return 0;
    }
    desktop::SingleInstance single(bw::executable_folder());
    if (!single.owns()) {
      for (int i = 0; i < 20; ++i) {
        if (single.show_existing())
          return 0;
        Sleep(100);
      }
      MessageBoxW(nullptr,
                  L"Native Workbench is already starting or running for this "
                  L"installation. Check the taskbar and try again shortly.",
                  L"Native Workbench", MB_OK | MB_ICONINFORMATION);
      return 0;
    }
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    HRESULT com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED |
                                              COINIT_DISABLE_OLE1DDE);
    if (FAILED(com))
      throw std::runtime_error(
          "Windows could not initialize native file dialogs.");
    Gdiplus::GdiplusStartupInput input;
    ULONG_PTR token = 0;
    if (Gdiplus::GdiplusStartup(&token, &input, nullptr) != Gdiplus::Ok) {
      CoUninitialize();
      throw std::runtime_error("Windows could not initialize drawing.");
    }
    INITCOMMONCONTROLSEX controls{sizeof(controls), ICC_LISTVIEW_CLASSES |
                                                        ICC_STANDARD_CLASSES |
                                                        ICC_TAB_CLASSES |
                                                        ICC_PROGRESS_CLASS};
    InitCommonControlsEx(&controls);
    int result;
    {
      Workspace app;
      result = app.run_app(instance, check, single.window_class());
    }
    Gdiplus::GdiplusShutdown(token);
    CoUninitialize();
    return result;
  } catch (const std::exception &e) {
    MessageBoxW(nullptr, wide(e.what()).c_str(), L"Native Workbench",
                MB_OK | MB_ICONERROR);
    return 1;
  }
}
