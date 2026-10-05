// Included inside Workspace. Native workflow presentation and pointer gestures
// live here; the desktop model remains the authority for every connection.
struct CanvasPort {
  POINT point{}; // Logical canvas coordinates, before scrolling / DPI scaling.
  std::string node, port, ref, label, type;
  bool output = false;
};
struct CanvasCard {
  RECT box{};
  std::string id, title, subtitle;
  bool source = false, unavailable = false;
  std::vector<CanvasPort> inputs, outputs;
};
std::map<std::string, POINT> canvasPositions;
std::vector<CanvasCard> canvasCards;
std::vector<CanvasPort> canvasPorts;
std::string canvasDragNode, canvasDragRef;
Json canvasTargets = Json::object();
POINT canvasDragStart{}, canvasNodeStart{}, canvasPointer{};
POINT canvasWorkspaceScroll{-1, -1};
bool canvasNodeMoved = false;

POINT canvas_world(POINT p) const {
  return {MulDiv(p.x, 96, dpi) + dagX, MulDiv(p.y, 96, dpi) + dagY};
}
bool canvas_editable() const {
  return ready && !busy && !packBusy && !packActionPending && !refBusy &&
         !refActionPending && !showingHistory && !closing && workflowMode;
}
bool canvas_positioned(const std::string &id) const {
  return !showingHistory && canvasPositions.count(id);
}
const Json &canvas_input(const std::string &node,
                         const std::string &port) const {
  static const Json missing;
  if (!state.get("nodes").is_array())
    return missing;
  for (const auto &item : state.get("nodes").array_items())
    if (getstr(item, "id") == node && item.get("inputs").is_array())
      for (const auto &input : item.get("inputs").array_items())
        if (getstr(input, "id") == port)
          return input;
  return missing;
}
bool canvas_connected(const Json &input, const std::string &ref) const {
  if (!input.get("refs").is_array())
    return false;
  for (const auto &item : input.get("refs").array_items())
    if (getstr(item, "ref") == ref)
      return true;
  return false;
}
bool canvas_accepts(const CanvasPort &target,
                    const std::string &ref) const {
  if (target.output || ref.empty())
    return false;
  // The bounded host query applies the model's semantic state, cycle and
  // capacity checks. Never substitute extension or type-only inference.
  if (getstr(canvasTargets, "ref") != ref || !canvasTargets.get("targets").is_array())
    return false;
  for (const auto &choice : canvasTargets.get("targets").array_items())
    if (getstr(choice, "nodeId") == target.node &&
        getstr(choice, "portId") == target.port)
      return true;
  return false;
}
void canvas_set_targets(const Json &result) {
  if (getstr(result, "ref") != canvasDragRef || canvasDragRef.empty())
    return;
  canvasTargets = result;
  InvalidateRect(dag, nullptr, FALSE);
}
const CanvasPort *canvas_port_at(POINT screen) const {
  const auto p = canvas_world(screen);
  for (auto it = canvasPorts.rbegin(); it != canvasPorts.rend(); ++it) {
    const long long dx = static_cast<long long>(p.x) - it->point.x,
                    dy = static_cast<long long>(p.y) - it->point.y;
    if (dx * dx + dy * dy <= 12 * 12)
      return &*it;
  }
  return nullptr;
}
void canvas_cancel_drag() {
  if (canvasDragNode.empty() && canvasDragRef.empty())
    return;
  // Escape and capture loss cancel the visual move as well as a pending link.
  if (!canvasDragNode.empty() && canvasNodeMoved)
    canvasPositions[canvasDragNode] = canvasNodeStart;
  canvasDragNode.clear();
  canvasDragRef.clear();
  canvasTargets = Json::object();
  canvasNodeMoved = false;
  if (GetCapture() == dag)
    ReleaseCapture();
  InvalidateRect(dag, nullptr, FALSE);
}
void canvas_reset_positions() {
  canvas_cancel_drag();
  canvasPositions.clear();
  canvasCards.clear();
  canvasPorts.clear();
  dagX = dagY = 0;
  canvasWorkspaceScroll = {-1, -1};
  InvalidateRect(dag, nullptr, FALSE);
}
void canvas_enter_history() {
  canvas_cancel_drag();
  if (canvasWorkspaceScroll.x < 0)
    canvasWorkspaceScroll = {dagX, dagY};
  dagX = dagY = 0;
}
void canvas_leave_history() {
  if (canvasWorkspaceScroll.x >= 0) {
    dagX = static_cast<int>(canvasWorkspaceScroll.x);
    dagY = static_cast<int>(canvasWorkspaceScroll.y);
  }
  canvasWorkspaceScroll = {-1, -1};
  InvalidateRect(dag, nullptr, FALSE);
}
void canvas_place_new_node(const std::string &id, POINT screen) {
  auto p = canvas_world(screen);
  // Match the pointer to the card header, leaving sockets inside the canvas.
  p.x = std::max<LONG>(24, p.x - 120);
  p.y = std::max<LONG>(24, p.y - 20);
  canvasPositions[id] = p;
  InvalidateRect(dag, nullptr, FALSE);
}
bool canvas_mouse_down(POINT screen) {
  if (!canvas_editable() || activeRequest || !outgoing.empty())
    return false;
  SetFocus(dag);
  canvas_cancel_drag();
  canvasPointer = canvas_world(screen);
  if (const auto *hit = canvas_port_at(screen)) {
    const auto port = *hit;
    if (port.output) {
      commit_all();
      canvasDragRef = port.ref;
      canvasTargets = Json::object();
      send("workspace/connection-targets", object({{"ref", canvasDragRef}}));
      SetCapture(dag);
      status_text(L"Drag to a highlighted input socket. Compatible inputs are green.");
      InvalidateRect(dag, nullptr, FALSE);
    } else {
      generalVisible = false;
      layout();
      commit_all();
      model("select", object({{"nodeId", port.node}}));
      status_text(L"Drag an output socket onto this input, or choose its source in Tool options.");
    }
    return true;
  }
  const auto p = canvas_world(screen);
  for (auto it = canvasCards.rbegin(); it != canvasCards.rend(); ++it)
    if (PtInRect(&it->box, p)) {
      const auto id = it->id;
      canvasDragNode = id;
      canvasDragStart = p;
      canvasNodeStart = {it->box.left, it->box.top};
      canvasNodeMoved = false;
      SetCapture(dag);
      if (!it->source) {
        generalVisible = false;
        layout();
        commit_all();
        if (id != selected)
          model("select", object({{"nodeId", id}}));
      } else
        status_text(wide(display_id(id)) + L" is a shared local input. Select a consuming tool to choose its files.");
      return true;
    }
  return false;
}
bool canvas_mouse_move(POINT screen) {
  canvasPointer = canvas_world(screen);
  if (!canvasDragNode.empty()) {
    const LONG dx = canvasPointer.x - canvasDragStart.x,
               dy = canvasPointer.y - canvasDragStart.y;
    if (dx > 3 || dx < -3 || dy > 3 || dy < -3)
      canvasNodeMoved = true;
    if (canvasNodeMoved) {
      canvasPositions[canvasDragNode] = {
          std::max<LONG>(24, canvasNodeStart.x + dx),
          std::max<LONG>(24, canvasNodeStart.y + dy)};
      InvalidateRect(dag, nullptr, FALSE);
    }
    SetCursor(LoadCursorW(nullptr, IDC_SIZEALL));
    return true;
  }
  if (!canvasDragRef.empty()) {
    const auto *target = canvas_port_at(screen);
    SetCursor(LoadCursorW(nullptr, target && !canvas_accepts(*target, canvasDragRef)
                                      ? IDC_NO : IDC_CROSS));
    InvalidateRect(dag, nullptr, FALSE);
    return true;
  }
  if (const auto *port = canvas_port_at(screen)) {
    SetCursor(LoadCursorW(nullptr, port->output ? IDC_CROSS : IDC_HAND));
    return true;
  }
  return false;
}
bool canvas_mouse_up(POINT screen) {
  if (canvasDragNode.empty() && canvasDragRef.empty())
    return false;
  const auto ref = canvasDragRef;
  const auto *at = canvas_port_at(screen);
  const auto target = at ? *at : CanvasPort{};
  const bool hasTarget = at && !at->output;
  const bool previewReady = getstr(canvasTargets, "ref") == ref &&
                            canvasTargets.get("targets").is_array();
  const bool accepted = hasTarget && canvas_accepts(target, ref);
  // Clear before releasing capture: WM_CAPTURECHANGED is synchronous.
  canvasDragNode.clear();
  canvasDragRef.clear();
  canvasTargets = Json::object();
  canvasNodeMoved = false;
  if (GetCapture() == dag)
    ReleaseCapture();
  InvalidateRect(dag, nullptr, FALSE);
  if (ref.empty())
    return true;
  if (!canvas_editable())
    return true;
  if (!hasTarget) {
    status_text(L"Connection cancelled. Drop onto a highlighted input socket to connect tools.");
    return true;
  }
  if (previewReady && !accepted) {
    status_text(L"These ports cannot connect: check the input type, required state, available slots and workflow direction.");
    return true;
  }
  const auto &input = canvas_input(target.node, target.port);
  if (!input.get("refs").is_array())
    return true;
  if (canvas_connected(input, ref)) {
    status_text(L"This output is already connected to that input.");
    return true;
  }
  Json refs = Json::array();
  if (input.get("max").integer(1) > 1)
    for (const auto &item : input.get("refs").array_items())
      refs.array_items().push_back(item.get("ref"));
  refs.array_items().push_back(ref);
  model("connect", object({{"nodeId", target.node}, {"portId", target.port},
                            {"refs", std::move(refs)}}));
  return true;
}
void canvas_layout(int vw, int vh) {
  canvasCards.clear();
  canvasPorts.clear();
  hits.clear();
  const auto rank = ranks();
  std::map<int, int> nextY;
  std::set<std::string> usedSources, activeIds;
  for (const auto &node : graph().get("nodes").array_items())
    for (const auto &port : node.get("inputs").object_items())
      for (const auto &ref : port.second.array_items())
        if (text(ref).find("::") == std::string::npos)
          usedSources.insert(text(ref));
  auto card = [&](const Json &node, bool source) {
    CanvasCard item;
    item.id = getstr(node, "id");
    item.source = source;
    activeIds.insert(item.id);
    item.title = display_id(item.id) + " · " +
                 (source ? getstr(node, "label", "Local input") : node_name(node));
    const auto &metadata = tool(node);
    item.unavailable = !source && metadata.is_null();
    item.subtitle = source ? "Local input · " + getstr(node, "type")
                           : getstr(metadata, "packId") + " " + getstr(metadata, "packVersion");
    if (!source && metadata.get("id").is_null()) {
      item.unavailable = true;
      item.subtitle = "Exact tool version unavailable";
    }
    if (source) {
      CanvasPort port;
      port.node = item.id;
      port.ref = item.id;
      port.label = "Files";
      port.type = getstr(node, "type");
      port.output = true;
      item.outputs.push_back(port);
    } else {
      if (metadata.get("ports").is_array())
        for (const auto &input : metadata.get("ports").array_items()) {
          CanvasPort port;
          port.node = item.id;
          port.port = getstr(input, "id");
          port.label = getstr(input, "label", port.port);
          port.type = getstr(input, "type");
          item.inputs.push_back(port);
        }
      if (metadata.get("outputs").is_array())
        for (const auto &output : metadata.get("outputs").array_items()) {
          CanvasPort port;
          port.node = item.id;
          port.port = getstr(output, "id");
          port.ref = item.id + "::" + port.port;
          port.label = getstr(output, "label", port.port);
          port.type = getstr(output, "type");
          port.output = true;
          item.outputs.push_back(port);
        }
    }
    const int level = source ? 0 : rank.at(item.id);
    const int h = 64 + static_cast<int>(item.inputs.size() + item.outputs.size()) * 34 +
                  (!item.inputs.empty() && !item.outputs.empty() ? 8 : 0);
    int x = 32 + level * 310, y = nextY.count(level) ? nextY[level] : 32;
    if (canvas_positioned(item.id)) {
      const auto &position = canvasPositions.at(item.id);
      x = static_cast<int>(position.x);
      y = static_cast<int>(position.y);
    }
    nextY[level] = std::max(nextY[level], y + h + 36);
    item.box = {x, y, x + 242, y + h};
    int row = y + 65;
    for (auto &port : item.inputs) {
      port.point = {x, row};
      row += 34;
    }
    if (!item.inputs.empty() && !item.outputs.empty())
      row += 8;
    for (auto &port : item.outputs) {
      port.point = {x + 242, row};
      row += 34;
    }
    canvasCards.push_back(std::move(item));
  };
  for (const auto &source : graph().get("sources").array_items())
    if (usedSources.count(getstr(source, "id")))
      card(source, true);
  for (const auto &node : graph().get("nodes").array_items())
    card(node, false);
  // Automatically placed inputs must not cover a tool dropped near the left
  // edge. Move only automatic cards; a user's positions stay at their pointer.
  for (size_t i = 0; i < canvasCards.size(); ++i) {
    auto &item = canvasCards[i];
    if (canvas_positioned(item.id))
      continue;
    for (size_t retry = 0; retry < canvasCards.size(); ++retry) {
      LONG shift = 0;
      for (size_t j = 0; j < canvasCards.size(); ++j) {
        if (j == i || (j > i && !canvas_positioned(canvasCards[j].id)))
          continue;
        const auto &other = canvasCards[j].box;
        const auto &box = item.box;
        if (box.left < other.right + 18 && box.right + 18 > other.left &&
            box.top < other.bottom + 18 && box.bottom + 18 > other.top)
          shift = std::max(shift, other.bottom + 36 - box.top);
      }
      if (!shift)
        break;
      item.box.top += shift;
      item.box.bottom += shift;
      for (auto &port : item.inputs)
        port.point.y += shift;
      for (auto &port : item.outputs)
        port.point.y += shift;
    }
  }
  for (const auto &item : canvasCards) {
    canvasPorts.insert(canvasPorts.end(), item.inputs.begin(), item.inputs.end());
    canvasPorts.insert(canvasPorts.end(), item.outputs.begin(), item.outputs.end());
  }
  // A removed node must not leave a position for a later, unrelated graph.
  if (!showingHistory) {
    for (auto it = canvasPositions.begin(); it != canvasPositions.end();)
      if (!activeIds.count(it->first))
        it = canvasPositions.erase(it);
      else
        ++it;
  }
  dagWidth = vw;
  dagHeight = vh;
  for (const auto &item : canvasCards) {
    dagWidth = std::max(dagWidth, static_cast<int>(item.box.right) + 48);
    dagHeight = std::max(dagHeight, static_cast<int>(item.box.bottom) + 48);
  }
  dagX = std::clamp(dagX, 0, std::max(0, dagWidth - vw));
  dagY = std::clamp(dagY, 0, std::max(0, dagHeight - vh));
  for (const auto &item : canvasCards) {
    const auto &box = item.box;
    hits.push_back({{px(box.left - dagX), px(box.top - dagY),
                     px(box.right - dagX), px(box.bottom - dagY)},
                    item.id, item.source});
  }
  for (int bar : {SB_HORZ, SB_VERT}) {
    SCROLLINFO si{sizeof(si), SIF_RANGE | SIF_PAGE | SIF_POS};
    si.nMax = (bar == SB_HORZ ? dagWidth : dagHeight) - 1;
    si.nPage = bar == SB_HORZ ? vw : vh;
    si.nPos = bar == SB_HORZ ? dagX : dagY;
    SetScrollInfo(dag, bar, &si, TRUE);
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
  HBRUSH gridBackground = CreateSolidBrush(RGB(246, 248, 251));
  FillRect(mem, &client, gridBackground);
  DeleteObject(gridBackground);
  const int vw = std::max(1, MulDiv(client.right, 96, dpi)),
            vh = std::max(1, MulDiv(client.bottom, 96, dpi));
  canvas_layout(vw, vh);
  {
    Gdiplus::Graphics g(mem);
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.ScaleTransform(dpi / 96.f, dpi / 96.f);
    g.TranslateTransform(static_cast<float>(-dagX), static_cast<float>(-dagY));
    Gdiplus::SolidBrush grid(Gdiplus::Color(255, 215, 224, 234));
    for (int y = dagY / 20 * 20; y <= dagY + vh; y += 20)
      for (int x = dagX / 20 * 20; x <= dagX + vw; x += 20)
        g.FillEllipse(&grid, static_cast<float>(x), static_cast<float>(y), 1.5f, 1.5f);
    auto curve = [&](POINT a, POINT b, Gdiplus::Color color, float weight, bool pending) {
      Gdiplus::Pen pen(color, weight);
      if (pending)
        pen.SetDashStyle(Gdiplus::DashStyleDash);
      const float lead = std::max(60.f, (b.x - a.x) / 2.f);
      g.DrawBezier(&pen, static_cast<float>(a.x), static_cast<float>(a.y),
                   a.x + lead, static_cast<float>(a.y), b.x - lead,
                   static_cast<float>(b.y), static_cast<float>(b.x), static_cast<float>(b.y));
    };
    for (const auto &target : canvasPorts) {
      if (target.output)
        continue;
      for (const auto &node : graph().get("nodes").array_items()) {
        if (getstr(node, "id") != target.node)
          continue;
        if (!node.get("inputs").get(target.port).is_array())
          continue;
        for (const auto &ref : node.get("inputs").get(target.port).array_items())
          for (const auto &source : canvasPorts)
            if (source.output && source.ref == text(ref)) {
              const bool active = source.node == selected || target.node == selected || source.ref == canvasDragRef;
              curve(source.point, target.point,
                    active ? Gdiplus::Color(255, 45, 106, 166) : Gdiplus::Color(255, 151, 169, 190),
                    active ? 2.4f : 1.7f, false);
            }
      }
    }
    if (!canvasDragRef.empty())
      for (const auto &source : canvasPorts)
        if (source.output && source.ref == canvasDragRef) {
          POINT endpoint = canvasPointer;
          bool compatible = false;
          for (const auto &target : canvasPorts) {
            const long long dx = static_cast<long long>(canvasPointer.x) - target.point.x,
                            dy = static_cast<long long>(canvasPointer.y) - target.point.y;
            if (!target.output && dx * dx + dy * dy <= 12 * 12) {
              endpoint = target.point;
              compatible = canvas_accepts(target, canvasDragRef);
              break;
            }
          }
          curve(source.point, endpoint,
                compatible ? Gdiplus::Color(255, 33, 135, 94) : Gdiplus::Color(255, 45, 106, 166),
                2.5f, true);
          break;
        }
    for (const auto &item : canvasCards) {
      const auto &box = item.box;
      const bool active = item.id == selected;
      rounded(g, static_cast<float>(box.left + 2), static_cast<float>(box.top + 3),
              static_cast<float>(box.right - box.left), static_cast<float>(box.bottom - box.top),
              5, RGB(230, 235, 241), RGB(230, 235, 241));
      rounded(g, static_cast<float>(box.left), static_cast<float>(box.top),
              static_cast<float>(box.right - box.left), static_cast<float>(box.bottom - box.top),
              5, PAPER, active ? RGB(33, 102, 172) : RGB(188, 203, 219));
      Gdiplus::SolidBrush header(item.unavailable ? Gdiplus::Color(255, 137, 84, 59)
                                    : item.source ? Gdiplus::Color(255, 87, 111, 138)
                                                  : Gdiplus::Color(255, 43, 90, 139));
      g.FillRectangle(&header, static_cast<float>(box.left + 1), static_cast<float>(box.top + 1),
                      static_cast<float>(box.right - box.left - 2), 43.f);
      if (!item.inputs.empty() && !item.outputs.empty()) {
        Gdiplus::Pen separator(Gdiplus::Color(255, 224, 231, 239), 1.f);
        const float y = item.outputs.front().point.y - 23.f;
        g.DrawLine(&separator, box.left + 12.f, y, box.right - 12.f, y);
      }
    }
    for (const auto &port : canvasPorts) {
      const bool candidate = !canvasDragRef.empty() && !port.output;
      const bool accepted = candidate && canvas_accepts(port, canvasDragRef);
      const bool active = port.ref == canvasDragRef || port.node == selected;
      Gdiplus::Color color = accepted ? Gdiplus::Color(255, 32, 136, 92)
                              : candidate ? Gdiplus::Color(255, 177, 186, 197)
                              : active ? Gdiplus::Color(255, 40, 101, 166)
                                       : Gdiplus::Color(255, 86, 112, 145);
      if (accepted) {
        Gdiplus::SolidBrush halo(Gdiplus::Color(55, 32, 136, 92));
        g.FillEllipse(&halo, port.point.x - 11.f, port.point.y - 11.f, 22.f, 22.f);
      }
      Gdiplus::Pen border(color, 2.f);
      Gdiplus::SolidBrush fill(port.output || accepted ? color : Gdiplus::Color(255, 255, 255, 255));
      g.FillEllipse(&fill, port.point.x - 5.f, port.point.y - 5.f, 10.f, 10.f);
      g.DrawEllipse(&border, port.point.x - 5.f, port.point.y - 5.f, 10.f, 10.f);
    }
  }
  SetBkMode(mem, TRANSPARENT);
  auto label = [&](const std::wstring &value, RECT r, HFONT face, COLORREF color, UINT flags) {
    RECT screen{px(r.left - dagX), px(r.top - dagY), px(r.right - dagX), px(r.bottom - dagY)};
    SelectObject(mem, face);
    SetTextColor(mem, color);
    DrawTextW(mem, value.c_str(), -1, &screen, flags | DT_NOPREFIX | DT_SINGLELINE | DT_END_ELLIPSIS);
  };
  for (const auto &item : canvasCards) {
    const auto &box = item.box;
    label(wide(item.title), {box.left + 12, box.top + 5, box.right - 12, box.top + 25}, bold, PAPER, DT_LEFT | DT_VCENTER);
    label(wide(item.subtitle), {box.left + 12, box.top + 25, box.right - 12, box.top + 42}, small, RGB(223, 235, 247), DT_LEFT | DT_VCENTER);
    auto portLabel = [&](const CanvasPort &port) {
      const UINT align = port.output ? DT_RIGHT : DT_LEFT;
      label(wide(port.label), {box.left + 14, port.point.y - 14, box.right - 14, port.point.y + 3}, font, INK, align | DT_VCENTER);
      label(wide(port.type), {box.left + 14, port.point.y + 3, box.right - 14, port.point.y + 18}, small, MUTED, align | DT_VCENTER);
    };
    for (const auto &port : item.inputs)
      portLabel(port);
    for (const auto &port : item.outputs)
      portLabel(port);
  }
  if (canvasCards.empty()) {
    SelectObject(mem, bold);
    SetTextColor(mem, INK);
    RECT title{px(32), px(40), client.right - px(32), px(75)};
    DrawTextW(mem, L"Build your workflow", -1, &title, DT_LEFT | DT_WORDBREAK | DT_NOPREFIX);
    SelectObject(mem, font);
    SetTextColor(mem, MUTED);
    RECT help{px(32), px(88), client.right - px(32), client.bottom - px(24)};
    DrawTextW(mem, L"Drag tools from the Tool shed onto this canvas.\n\nConnect an output socket to a compatible input socket. Select a tool to edit its options on the right.\n\nYou can also add a selected tool with the Add to workflow button and choose connections in Tool options.", -1, &help, DT_LEFT | DT_WORDBREAK | DT_NOPREFIX);
  }
  BitBlt(dc, 0, 0, client.right, client.bottom, mem, 0, 0, SRCCOPY);
  SelectObject(mem, old);
  DeleteObject(bitmap);
  DeleteDC(mem);
}
