-- v14.2 textbook extras (runs after textbook.lua, before gold-boxes.lua).
--
-- 1. Math normalisation for every format: siunitx-style units (\SI, \si, \qty,
--    \unit, \num), \degree, \celsius, \ohm, \tfrac, stray Docs escapes (\_ \*),
--    and \( \) / \[ \] delimiters left in text.
-- 2. ::: {.figure-frame height="45mm" caption="..."} brief ::: -> a rounded,
--    dashed image placeholder with the figure brief and a numbered caption.
-- 3. ::: {.graph-paper width="110mm" height="70mm" x-label="t / s" y-label="v / m s⁻¹"
--    x-max="5" y-max="10" points="0,0 1,2" line="best-fit|join" caption="..."} :::
--    -> graph paper with 1 mm minor and 1 cm major gridlines (Typst in the PDF,
--    inline SVG in HTML/EPUB, an embedded SVG image in DOCX). With points= it is a
--    generated plot on the same major + minor grid.

local stringify = pandoc.utils.stringify
local is_id = false

local function is_typst() return FORMAT == "typst" or FORMAT:match("^typst") ~= nil end
local function is_html() return FORMAT:match("html") ~= nil or FORMAT:match("epub") ~= nil end
local function is_epub() return FORMAT:match("epub") ~= nil end

-- ------------------------------------------------------------- math
local PREFIX = { kilo = "k", mega = "M", giga = "G", milli = "m", micro = "\\mu ", nano = "n", centi = "c", pico = "p", tera = "T" }
local UNIT = {
  metre = "m", meter = "m", second = "s", gram = "g", newton = "N", joule = "J", watt = "W",
  pascal = "Pa", hertz = "Hz", volt = "V", ampere = "A", coulomb = "C", kelvin = "K", mole = "mol",
  ohm = "\\Omega ", celsius = "°C", degree = "°", hour = "h", minute = "min",
  litre = "L", liter = "L", tesla = "T", weber = "Wb", farad = "F", electronvolt = "eV", percent = "\\%",
}

local function siunit(u)
  u = u:gsub("^%s+", ""):gsub("%s+$", "")
  if not u:find("\\") then
    -- plain units: "m/s^2", "kg m s^-1", "m.s^{-1}"
    u = u:gsub("%s*[%.~]%s*", "\\,"):gsub("%s+", "\\,")
    return "\\mathrm{" .. u .. "}"
  end
  local out, pending_per, prefix = {}, false, ""
  for name in u:gmatch("\\(%a+)") do
    if name == "per" then pending_per = true
    elseif name == "squared" or name == "cubed" then
      local p = name == "squared" and "2" or "3"
      if #out > 0 then
        local last = out[#out]
        if last:match("%^{%-1}$") then out[#out] = last:gsub("%^{%-1}$", "^{-" .. p .. "}")
        else out[#out] = last .. "^{" .. p .. "}" end
      end
    elseif PREFIX[name] then prefix = PREFIX[name]
    elseif UNIT[name] then
      local item = prefix .. UNIT[name]
      prefix = ""
      if pending_per then item = item .. "^{-1}"; pending_per = false end
      out[#out + 1] = item
    end
  end
  return "\\mathrm{" .. table.concat(out, "\\,") .. "}"
end

local function sinum(n)
  n = n:gsub("%s+", "")
  local mant, exp = n:match("^([%-%+]?[%d%.]+)[eE]([%-%+]?%d+)$")
  if mant then return mant .. " \\times 10^{" .. exp:gsub("^%+", "") .. "}" end
  return n
end

-- balanced {...} argument starting at position i (s:sub(i,i) == "{")
local function group(s, i)
  if s:sub(i, i) ~= "{" then return nil end
  local depth = 0
  for j = i, #s do
    local c = s:sub(j, j)
    if c == "{" then depth = depth + 1 elseif c == "}" then depth = depth - 1
      if depth == 0 then return s:sub(i + 1, j - 1), j end
    end
  end
  return nil
end

local function expand_si(s)
  local out, i = {}, 1
  while i <= #s do
    local a, b, cmd = s:find("\\(%a+)", i)
    if not a then out[#out + 1] = s:sub(i); break end
    out[#out + 1] = s:sub(i, a - 1)
    local handled = false
    if cmd == "SI" or cmd == "qty" then
      local opt = s:match("^%b[]", b + 1)
      local start = b + 1 + (opt and #opt or 0)
      local num, e1 = group(s, start)
      local unit, e2
      if e1 then unit, e2 = group(s, e1 + 1) end
      if num and unit then out[#out + 1] = sinum(num) .. "\\," .. siunit(unit); i = e2 + 1; handled = true end
    elseif cmd == "si" or cmd == "unit" then
      local unit, e = group(s, b + 1)
      if unit then out[#out + 1] = siunit(unit); i = e + 1; handled = true end
    elseif cmd == "num" then
      local num, e = group(s, b + 1)
      if num then out[#out + 1] = sinum(num); i = e + 1; handled = true end
    end
    if not handled then out[#out + 1] = s:sub(a, b); i = b + 1 end
  end
  return table.concat(out)
end

function normalize_tex(tex)
  local t = tex
  t = expand_si(t)
  t = t:gsub("\\degree%f[%A]", "°")
  t = t:gsub("\\celsius%f[%A]", "\\mathrm{°C}")
  -- Degrees as the plain sign: an empty-base superscript ({}^{\circ}) becomes a
  -- zero-width box in Word / LibreOffice equations.
  t = t:gsub("{}%^{\\circ}", "°"):gsub("{}%^\\circ%f[%A]", "°")
  t = t:gsub("%^{\\circ}", "°"):gsub("%^\\circ%f[%A]", "°")
  t = t:gsub("\\ohm%f[%A]", "\\Omega")
  t = t:gsub("\\tfrac%f[%A]", "\\frac")
  t = t:gsub("\\textrm%f[%A]", "\\mathrm")
  -- Google Docs escapes that survived inside math: \_ and \* are never wanted in TeX here.
  t = t:gsub("\\_", "_"):gsub("\\%*", "*")
  -- an escaped dollar inside math is a stray delimiter
  t = t:gsub("\\%$", "")
  return (t:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function fix_math(m)
  local tex = normalize_tex(m.text)
  if tex ~= m.text then m.text = tex; return m end
end

-- \(...\) and \[...\] that reached the AST as plain text (Docs export / AI output)
local function delimiters(inlines)
  local changed = false
  local s = {}
  for _, inl in ipairs(inlines) do
    if inl.t == "Str" then s[#s + 1] = inl.text
    elseif inl.t == "Space" or inl.t == "SoftBreak" then s[#s + 1] = " "
    else return nil end
  end
  local text = table.concat(s)
  if not text:find("\\[%(%[]") then return nil end
  local out = pandoc.List()
  local i = 1
  while i <= #text do
    local a, b, open = text:find("\\([%(%[])", i)
    if not a then break end
    local close = open == "(" and "\\)" or "\\]"
    local c = text:find(close, b + 1, true)
    if not c then break end
    if a > i then out:extend(pandoc.read(text:sub(i, a - 1), "markdown").blocks[1] and pandoc.utils.blocks_to_inlines(pandoc.read(text:sub(i, a - 1), "markdown").blocks) or {}) end
    out:insert(pandoc.Math(open == "(" and "InlineMath" or "DisplayMath", normalize_tex(text:sub(b + 1, c - 1))))
    i = c + 2
    changed = true
  end
  if not changed then return nil end
  if i <= #text then out:extend(pandoc.utils.blocks_to_inlines(pandoc.read(text:sub(i), "markdown").blocks)) end
  return out
end

-- ------------------------------------------------------------- helpers
local function mm(value, default)
  local v = tostring(value or ""):match("^%s*([%d%.]+)%s*mm%s*$") or tostring(value or ""):match("^%s*([%d%.]+)%s*$")
  local cm = tostring(value or ""):match("^%s*([%d%.]+)%s*cm%s*$")
  local n = tonumber(v) or (tonumber(cm) and tonumber(cm) * 10) or default
  return n
end

local function typst_inline(text)
  if not text or text == "" then return "" end
  local out = pandoc.write(pandoc.read(text, "markdown"), "typst")
  return (out:gsub("%s+$", ""))
end

local function typst_str(s)
  return '"' .. tostring(s or ""):gsub("\\", "\\\\"):gsub('"', '\\"') .. '"'
end

local function xml_escape(s)
  return (tostring(s or ""):gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function label(id, en) return is_id and id or en end

local function caption_blocks(text, kind_label)
  local inl = pandoc.List({ pandoc.Strong(kind_label) })
  if text and text ~= "" then
    inl:insert(pandoc.Space())
    inl:extend(pandoc.utils.blocks_to_inlines(pandoc.read(text, "markdown").blocks))
  end
  return inl
end

-- ------------------------------------------------------------- figure frame
local function figure_frame(el)
  local h = math.max(20, math.min(mm(el.attributes.height, 45), 160))
  local caption = el.attributes.caption or ""
  local tag = label("Gambar", "Figure")
  local hint = label("Tempat gambar", "Image placeholder")
  if is_typst() then
    local blocks = pandoc.List({ pandoc.RawBlock("typst",
      "#bc-figure-frame(height: " .. h .. "mm, hint: " .. typst_str(hint) .. ", caption: [" .. typst_inline(caption) .. "])[") })
    blocks:extend(el.content)
    blocks:insert(pandoc.RawBlock("typst", "]"))
    return pandoc.Div(blocks, pandoc.Attr("", { "bc-extra-done" }))
  end
  if FORMAT == "docx" then
    local blocks = pandoc.List({ pandoc.Para({ pandoc.Strong(hint) }) })
    blocks:extend(el.content)
    -- empty lines reserve roughly the requested height (one line ~ 6 mm)
    for _ = 1, math.max(1, math.floor((h - 12) / 6)) do blocks:insert(pandoc.Para({ pandoc.Str("\u{00A0}") })) end
    local frame = pandoc.Div(blocks, pandoc.Attr("", {}, { { "custom-style", "Figure Frame" } }))
    local cap = pandoc.Div({ pandoc.Para(caption_blocks(caption, tag)) }, pandoc.Attr("", {}, { { "custom-style", "Image Caption" } }))
    return { frame, cap }
  end
  local box = pandoc.Div(pandoc.List({ pandoc.Para({ pandoc.Span(hint, pandoc.Attr("", { "bc-frame-hint" })) }) }) .. el.content,
    pandoc.Attr("", { "bc-frame-box" }, { { "style", "min-height:" .. h .. "mm" } }))
  local cap = pandoc.Div({ pandoc.Para(caption_blocks(caption, tag)) }, pandoc.Attr("", { "bc-frame-caption" }))
  return pandoc.Div({ box, cap }, pandoc.Attr("", { "bc-figure-frame", "bc-extra-done" }))
end

-- ------------------------------------------------------------- graph paper
local function parse_points(s)
  local pts = {}
  for x, y in tostring(s or ""):gmatch("([%-%d%.]+)%s*,%s*([%-%d%.]+)") do
    pts[#pts + 1] = { tonumber(x), tonumber(y) }
  end
  return pts
end

local function best_fit(pts)
  local n = #pts
  if n < 2 then return nil end
  local sx, sy, sxx, sxy = 0, 0, 0, 0
  for _, p in ipairs(pts) do sx = sx + p[1]; sy = sy + p[2]; sxx = sxx + p[1] * p[1]; sxy = sxy + p[1] * p[2] end
  local d = n * sxx - sx * sx
  if d == 0 then return nil end
  local m = (n * sxy - sx * sy) / d
  return m, (sy - m * sx) / n
end

local function fmt(v)
  local s = string.format("%.3f", v):gsub("0+$", ""):gsub("%.$", "")
  return s
end

local function nice_step(raw)
  if not raw or raw <= 0 then return 1 end
  local k = 10 ^ math.floor(math.log(raw, 10))
  for _, m in ipairs({ 1, 2, 2.5, 5, 10 }) do if m * k >= raw - 1e-9 then return m * k end end
  return 10 * k
end

local graph_count = 0

local function graph_svg(w, h, minor, major, xlabel, ylabel, xmax, ymax, pts, fit)
  local L, B, T, R = 14, 12, 4, 4
  local W, H = w + L + R, h + T + B
  local o = {}
  local function add(s) o[#o + 1] = s end
  add(string.format('<svg xmlns="http://www.w3.org/2000/svg" class="bc-graph-svg" width="%smm" height="%smm" viewBox="0 0 %s %s" role="img" aria-label="%s">',
    fmt(W), fmt(H), fmt(W), fmt(H), xml_escape(label("Kertas grafik", "Graph paper"))))
  add(string.format('<rect x="%s" y="%s" width="%s" height="%s" fill="#FFFFFF"/>', L, T, fmt(w), fmt(h)))
  local per = math.max(1, math.floor(major / minor + 0.5))
  local nx, ny = math.floor(w / minor + 1e-6), math.floor(h / minor + 1e-6)
  for pass = 1, 2 do
    for i = 0, nx do
      local is_major = i % per == 0
      if (pass == 1) ~= is_major then
        local x = L + i * minor
        add(string.format('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>', fmt(x), T, fmt(x), fmt(T + h),
          is_major and "#4F86BD" or "#C9DCEE", is_major and "0.3" or "0.1"))
      end
    end
    for j = 0, ny do
      local is_major = j % per == 0
      if (pass == 1) ~= is_major then
        local y = T + h - j * minor
        add(string.format('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>', L, fmt(y), fmt(L + w), fmt(y),
          is_major and "#4F86BD" or "#C9DCEE", is_major and "0.3" or "0.1"))
      end
    end
  end
  add(string.format('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#1F2328" stroke-width="0.5"/>', L, fmt(T + h), fmt(L + w), fmt(T + h)))
  add(string.format('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#1F2328" stroke-width="0.5"/>', L, T, L, fmt(T + h)))
  local font = 'font-family="Source Sans 3, Source Sans Pro, Arial, sans-serif" fill="#1F2328"'
  local mx, my = math.floor(nx / per), math.floor(ny / per)
  local sx = xmax and nice_step(xmax / math.max(mx, 1))
  local sy = ymax and nice_step(ymax / math.max(my, 1))
  if sx then
    for i = 0, mx do
      add(string.format('<text x="%s" y="%s" font-size="2.6" text-anchor="middle" %s>%s</text>', fmt(L + i * major), fmt(T + h + 3.6), font, fmt(i * sx)))
    end
  end
  if sy then
    for j = 0, my do
      add(string.format('<text x="%s" y="%s" font-size="2.6" text-anchor="end" %s>%s</text>', fmt(L - 1.2), fmt(T + h - j * major + 0.9), font, fmt(j * sy)))
    end
  end
  if xlabel ~= "" then add(string.format('<text x="%s" y="%s" font-size="3" text-anchor="middle" font-weight="600" %s>%s</text>', fmt(L + w / 2), fmt(H - 1.5), font, xml_escape(xlabel))) end
  if ylabel ~= "" then add(string.format('<text x="3.2" y="%s" font-size="3" text-anchor="middle" font-weight="600" transform="rotate(-90 3.2 %s)" %s>%s</text>', fmt(T + h / 2), fmt(T + h / 2), font, xml_escape(ylabel))) end
  if sx and sy and #pts > 0 then
    local function px(x) return L + x / sx * major end
    local function py(y) return T + h - y / sy * major end
    if fit == "best-fit" then
      local m, c = best_fit(pts)
      if m then
        local xe = mx * sx
        if m > 0 then xe = math.min(xe, (my * sy - c) / m) end
        add(string.format('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#C8144A" stroke-width="0.45"/>', fmt(px(0)), fmt(py(c)), fmt(px(xe)), fmt(py(m * xe + c))))
      end
    elseif fit == "join" then
      local d = {}
      for k, p in ipairs(pts) do d[#d + 1] = (k == 1 and "M" or "L") .. fmt(px(p[1])) .. " " .. fmt(py(p[2])) end
      add('<path d="' .. table.concat(d, " ") .. '" fill="none" stroke="#C8144A" stroke-width="0.45"/>')
    end
    for _, p in ipairs(pts) do
      local x, y = px(p[1]), py(p[2])
      add(string.format('<path d="M%s %s L%s %s M%s %s L%s %s" stroke="#1B4F8A" stroke-width="0.45"/>', fmt(x - 1), fmt(y - 1), fmt(x + 1), fmt(y + 1), fmt(x - 1), fmt(y + 1), fmt(x + 1), fmt(y - 1)))
    end
  end
  add("</svg>")
  return table.concat(o)
end

local function graph_paper(el)
  local a = el.attributes
  local w = math.max(30, math.min(mm(a.width, 110), 110))
  local h = math.max(20, math.min(mm(a.height, 70), 180))
  local minor = math.max(0.5, mm(a.minor, 1))
  local major = math.max(minor, mm(a.major, 10))
  local xlabel, ylabel = a["x-label"] or a.xlabel or "", a["y-label"] or a.ylabel or ""
  local xmax, ymax = tonumber(a["x-max"] or a.xmax or ""), tonumber(a["y-max"] or a.ymax or "")
  local pts = parse_points(a.points)
  local fit = a.line or (#pts > 0 and "" or "")
  local caption = a.caption or ""
  local tag = label("Grafik", "Graph")
  if is_typst() then
    -- the PDF main column is 110 mm; the frame adds ~19 mm for axis labels
    w = math.min(w, 90)
    local p = {}
    for _, q in ipairs(pts) do p[#p + 1] = "(" .. fmt(q[1]) .. ", " .. fmt(q[2]) .. ")" end
    local fitline = "none"
    if fit == "best-fit" then
      local m, c = best_fit(pts)
      if m then fitline = "(" .. fmt(m) .. ", " .. fmt(c) .. ")" end
    end
    local call = string.format("#bc-graph-paper(width: %smm, height: %smm, minor: %smm, major: %smm, x-label: [%s], y-label: [%s], x-max: %s, y-max: %s, points: (%s), fit: %s, join: %s, caption: [%s])",
      fmt(w), fmt(h), fmt(minor), fmt(major), typst_inline(xlabel), typst_inline(ylabel), xmax and fmt(xmax) or "none", ymax and fmt(ymax) or "none",
      table.concat(p, ", ") .. (#p == 1 and "," or ""), fitline, fit == "join" and "true" or "false", typst_inline(caption))
    local blocks = pandoc.List({ pandoc.RawBlock("typst", call) })
    blocks:extend(el.content)
    return pandoc.Div(blocks, pandoc.Attr("", { "bc-extra-done" }))
  end
  local svg = graph_svg(w, h, minor, major, xlabel, ylabel, xmax, ymax, pts, fit)
  local blocks = pandoc.List()
  if is_html() then
    blocks:insert(pandoc.RawBlock("html", '<div class="bc-graph-frame">' .. svg .. "</div>"))
  else
    graph_count = graph_count + 1
    local name = "bc-graph-" .. graph_count .. ".svg"
    pandoc.mediabag.insert(name, "image/svg+xml", svg)
    blocks:insert(pandoc.Para({ pandoc.Image({}, name, "", pandoc.Attr("", {}, { { "width", fmt(w + 18) .. "mm" } })) }))
  end
  blocks:extend(el.content)
  if caption ~= "" then
    local cap = pandoc.Para(caption_blocks(caption, tag))
    if FORMAT == "docx" then blocks:insert(pandoc.Div({ cap }, pandoc.Attr("", {}, { { "custom-style", "Image Caption" } })))
    else blocks:insert(pandoc.Div({ cap }, pandoc.Attr("", { "bc-frame-caption" }))) end
  end
  return pandoc.Div(blocks, pandoc.Attr("", { "bc-graph-paper", "bc-extra-done" }))
end

local function div(el)
  if el.classes:includes("bc-extra-done") then return nil end
  for _, c in ipairs(el.classes) do
    if c == "figure-frame" or c == "figure-placeholder" or c == "image-placeholder" or c == "image-frame" or c == "gambar" then return figure_frame(el) end
    if c == "graph-paper" or c == "graph" or c == "kertas-grafik" or c == "plot" then return graph_paper(el) end
  end
end

return {
  { Meta = function(meta) local lang = meta.lang and stringify(meta.lang) or "en"; is_id = lang:sub(1, 2) == "id" end },
  { Math = fix_math,
    -- \SI{9.81}{m/s^2} written in prose is parsed as raw TeX and would vanish outside LaTeX.
    RawInline = function(r)
      if not r.format:match("tex") then return nil end
      for _, cmd in ipairs({ "SI", "si", "qty", "unit", "num", "degree", "celsius", "ohm" }) do
        if r.text:match("^\\" .. cmd .. "%f[^%a]") then return pandoc.Math("InlineMath", normalize_tex(r.text)) end
      end
    end },
  { Para = function(p) local r = delimiters(p.content); if r then return pandoc.Para(r) end end,
    Plain = function(p) local r = delimiters(p.content); if r then return pandoc.Plain(r) end end },
  { Div = div },
}
