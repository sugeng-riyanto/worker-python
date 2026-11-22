-- Normalise generated chapters before the box filter runs.
--
-- 1. Math rescue: Google Docs' Markdown export escapes "$", so "$v = s/t$"
--    arrives as literal text. Literal $...$ / $$...$$ runs become real math.
-- 2. Heading clean-up: "CHAPTER 2: KINEMATICS" -> "Kinematics", "MODULE 8: ..."
--    -> unnumbered, "2.1 Speed ..." -> "Speed ..." (the template numbers it).
-- 3. Structure recovery for drafts written before the fenced-div conventions:
--    scaffold headings and labelled blockquotes become the matching boxes
--    (objectives, worked-example, workspace, qr, figure-brief, teacher-note ...).
-- Explicit ::: {.class} divs written by the generator are left alone.

local stringify = pandoc.utils.stringify
local is_id = true

-- ---------------------------------------------------------------- math
local function plain_text(inl)
  if inl.t == "Str" then return inl.text end
  if inl.t == "Space" then return " " end
  if inl.t == "SoftBreak" then return " " end
  return nil
end

local function text_to_inlines(s)
  local out = pandoc.List()
  if s == "" then return out end
  local first = true
  for piece in (s .. " "):gmatch("(.-) ") do
    if not first then out:insert(pandoc.Space()) end
    if piece ~= "" then out:insert(pandoc.Str(piece)) end
    first = false
  end
  -- collapse a trailing Space introduced by a trailing blank
  return out
end

local function valid_inline_math(tex)
  if tex == "" then return false end
  if tex:match("^%s") or tex:match("%s$") then return false end
  -- "costs $5 and $10" is money, not math
  if tex:match("^%d+[%.,]?%d*%s") and not tex:match("[=\\^_{}]") then return false end
  return true
end

local function split_math(s)
  -- returns list of inlines, or nil when nothing changed
  if not s:find("%$") then return nil end
  local out = pandoc.List()
  local i, changed = 1, false
  local n = #s
  local buf = ""
  while i <= n do
    local c = s:sub(i, i)
    if c == "$" then
      local display = s:sub(i + 1, i + 1) == "$"
      local open_len = display and 2 or 1
      local close = display and s:find("%$%$", i + 2) or s:find("%$", i + 1)
      if close then
        local tex = s:sub(i + open_len, close - 1)
        if display and tex:match("%S") or (not display and valid_inline_math(tex)) then
          out:extend(text_to_inlines(buf))
          buf = ""
          out:insert(pandoc.Math(display and "DisplayMath" or "InlineMath", (tex:gsub("^%s+", ""):gsub("%s+$", ""))))
          i = close + open_len
          changed = true
        else
          buf = buf .. c
          i = i + 1
        end
      else
        buf = buf .. c
        i = i + 1
      end
    else
      buf = buf .. c
      i = i + 1
    end
  end
  if not changed then return nil end
  out:extend(text_to_inlines(buf))
  return out
end

local function rescue_math(inlines)
  local out = pandoc.List()
  local run = {}
  local function flush()
    if #run == 0 then return end
    local s = table.concat(run)
    local replaced = split_math(s)
    if replaced then
      out:extend(replaced)
    else
      out:extend(text_to_inlines(s))
    end
    run = {}
  end
  local touched = false
  for _, inl in ipairs(inlines) do
    local t = plain_text(inl)
    if t then
      run[#run + 1] = t
      if t:find("%$") then touched = true end
    else
      flush()
      out:insert(inl)
    end
  end
  flush()
  if not touched then return nil end
  return out
end

-- inline code from Docs drafts is used for emphasis (`DEFINE`, `pp. 41-85`)
local function soften_code(el)
  local text = el.text
  if #text <= 48 then
    return pandoc.Strong({ pandoc.Str(text) })
  end
  return pandoc.Str(text)
end

-- ---------------------------------------------------------------- headings
local KEEP_UPPER = {
  SI = true, IGCSE = true, BSKAP = true, CAIE = true, AS = true, DC = true, AC = true,
  ["A0"] = true, ["A1"] = true, ["A2"] = true, ["B1"] = true, ["B2"] = true, ["C1"] = true, ["C2"] = true,
  PHET = false, QR = true, IPA = true, STEM = true, UV = true, LED = true, GPS = true, EM = true,
}
local SMALL = { ["and"] = true, ["or"] = true, ["of"] = true, ["the"] = true, ["in"] = true, ["on"] = true,
  ["to"] = true, ["a"] = true, ["an"] = true, ["for"] = true, ["vs."] = true, ["dan"] = true, ["di"] = true,
  ["ke"] = true, ["yang"] = true, ["dari"] = true, ["pada"] = true, ["dengan"] = true }

local function is_shouting(s)
  local letters = s:gsub("[^%a]", "")
  if #letters < 4 then return false end
  local upper = letters:gsub("[^%u]", "")
  return #upper / #letters >= 0.7
end

local function title_word(w, first)
  local core = w:gsub("[^%w]", "")
  if KEEP_UPPER[core] then return w end
  if core:match("%d") then return w end
  local lower = w:lower()
  if not first and SMALL[lower] then return lower end
  return (lower:gsub("^(%W*)(%a)", function(p, c) return p .. c:upper() end))
end

local function title_case_inlines(inlines)
  local first = true
  return inlines:walk({
    Str = function(s)
      local r = title_word(s.text, first)
      first = false
      return pandoc.Str(r)
    end,
  })
end

local function strip_prefix(inlines, patterns)
  local text = stringify(inlines)
  for _, pat in ipairs(patterns) do
    local rest = text:match(pat)
    if rest then
      return pandoc.Inlines(pandoc.read(rest, "markdown").blocks[1] and pandoc.utils.blocks_to_inlines(pandoc.read(rest, "markdown").blocks) or {}), true
    end
  end
  return inlines, false
end

local CHAPTER_PREFIX = {
  "^%s*[Cc][Hh][Aa][Pp][Tt][Ee][Rr]%s+%d+%s*[:.%-–—]+%s*(.+)$",
  "^%s*[Bb][Aa][Bb]%s+%d+%s*[:.%-–—]+%s*(.+)$",
}
local MODULE_PREFIX = { "^%s*[Mm][Oo][Dd][Uu][Ll][Ee]%s+%d+%s*[:.%-–—]+%s*(.+)$" }
local NUMBER_PREFIX = { "^%s*%d+%.%d+%s+(.+)$" }

local function add_class(el, class)
  if not el.classes:includes(class) then el.classes:insert(class) end
end

local clean_header

local function clean_chapter_spans(el)
  -- Quarto HTML books wrap the title as [n]{.chapter-number} [title]{.chapter-title}.
  local found = false
  el.content = el.content:walk({ Span = function(sp)
    if sp.classes:includes("chapter-title") then
      found = true
      local h = clean_header(pandoc.Header(el.level, sp.content))
      if h and h.content then sp.content = h.content end
      return sp
    end
  end })
  return found
end

clean_header = function(el)
  if clean_chapter_spans(el) then return el end
  local text = stringify(el.content)
  if el.level == 1 then
    if text:upper():match("^%s*FRONT MATTER") or text:upper():match("^%s*PRAKATA") then
      add_class(el, "unnumbered")
    end
    local stripped, did = strip_prefix(el.content, CHAPTER_PREFIX)
    if did then el.content = stripped end
  elseif el.level == 2 then
    local stripped, did = strip_prefix(el.content, MODULE_PREFIX)
    if did and stringify(stripped):lower():find("chapter opener") then
      return {}
    end
    if did then
      el.content = stripped
      add_class(el, "unnumbered")
    else
      local s2, d2 = strip_prefix(el.content, NUMBER_PREFIX)
      if d2 then el.content = s2 end
    end
  end
  if is_shouting(stringify(el.content)) then
    el.content = title_case_inlines(el.content)
  end
  -- "Exercise (`Let's Map It`)" style code spans in headings
  el.content = el.content:walk({ Code = function(c) return pandoc.Str(c.text) end })
  return el
end

-- ---------------------------------------------------------------- structure recovery
local function lower(s) return s:lower() end

-- scaffold H3/H4 headings -> what to do with their section
local SCAFFOLD = {
  { "sub%-section pedagogical header", "teacher-note" },
  { "pedagogical header", "teacher-note" },
  { "coherent prose", "drop" },
  { "dual concrete examples", "drop" },
  { "inline active learning workspace", "drop" },
  { "active learning workspace", "drop" },
  { "real%-world phenomenon hook", "hook" },
  { "phenomenon hook", "hook" },
  { "trigger questions", "think" },
  { "pertanyaan pemantik", "think" },
  { "learning objectives", "objectives" },
  { "tujuan pembelajaran", "objectives" },
  { "mark%-scheme decoder", "summary" },
  { "worked exemplar", "worked-example" },
  { "worked example", "worked-example" },
  { "contoh soal", "worked-example" },
  { "common mistaken errors", "exam-trap" },
  { "common mistakes", "exam-trap" },
  { "trap matrix", "summary" },
  { "high%-yield equation", "summary" },
  { "mind map", "summary" },
  { "practical bridge", "practical" },
  { "practical", "practical" },
  { "tiered exam practice", "review" },
  { "past paper exam challenge", "practice" },
  { "end%-of%-sub%-section checkpoint", "practice" },
  { "self%-diagnostic checklist", "workspace" },
}

local function scaffold_kind(text)
  local t = lower(text)
  for _, pair in ipairs(SCAFFOLD) do
    if t:find(pair[1]) then return pair[2] end
  end
  return nil
end

local function clean_title(text)
  -- "Real-World Phenomenon Hook: Braking Distance" -> "Braking Distance"
  local after = text:match(":%s*(.+)$")
  return after
end

-- labelled blockquotes from Docs drafts
local QUOTE_KINDS = {
  { "qr watch", "qr" },
  { "qr code", "qr" },
  { "diagram prompt", "figure-brief" },
  { "diagram brief", "figure-brief" },
  { "figure placeholder", "figure-brief" },
  { "active learning workspace", "workspace" },
  { "g%.i%.v%.e%.n%.s", "givens" },
  { "teacher verification stamp", "continue" },
  { "exam trap", "exam-trap" },
  { "examiner tip", "remember" },
  { "remember", "remember" },
  { "ingat", "remember" },
  { "did you know", "info" },
  { "tahukah kamu", "info" },
}

local function quote_kind(el)
  local first = el.content[1]
  if not first then return nil end
  local t = lower(stringify(first)):gsub("^[%s%p★✎☆✓]+", "")
  for _, pair in ipairs(QUOTE_KINDS) do
    if t:find("^" .. pair[1]) or t:sub(1, 60):find(pair[1]) then return pair[2] end
  end
  return nil
end

local SIDE_KINDS = { qr = true, ["teacher-note"] = true, ["quick-check"] = false, remember = true, info = true }

local function make_div(kind, blocks, title)
  local attrs = {}
  if title and title ~= "" then attrs = { { "title", title } } end
  return pandoc.Div(blocks, pandoc.Attr("", { kind }, attrs))
end

-- Drop a leading bold label paragraph ("**QR WATCH (...):**") from recovered blocks.
local function drop_label(blocks)
  local first = blocks[1]
  if first and (first.t == "Para" or first.t == "Plain") and first.content[1]
    and (first.content[1].t == "Strong" or first.content[1].t == "Emph") then
    local label = stringify(first.content[1])
    local rest = pandoc.List()
    local started = false
    for i = 2, #first.content do
      local inl = first.content[i]
      if started or not (inl.t == "LineBreak" or inl.t == "Space" or inl.t == "SoftBreak") then
        started = true
        rest:insert(inl)
      end
    end
    local out = pandoc.List()
    if #rest > 0 then out:insert(pandoc.Para(rest)) end
    for i = 2, #blocks do out:insert(blocks[i]) end
    return out, label
  end
  return blocks, nil
end

local function strip_brackets(blocks)
  -- "`[DIAGRAM BRIEF — Fig 2.1: ...]`" -> plain description
  return pandoc.Blocks(blocks):walk({
    Str = function(s)
      local t = s.text:gsub("^%[", ""):gsub("%]$", "")
      return pandoc.Str(t)
    end,
  })
end

local function recover_quotes(blocks)
  local out = pandoc.List()
  local last_kind, last_div = nil, nil
  for _, b in ipairs(blocks) do
    if b.t == "BlockQuote" then
      local kind = quote_kind(b)
      if kind == "continue" and last_div then
        last_div.content:extend(b.content)
      elseif kind == nil and last_div and (last_kind == "workspace" or last_kind == "givens") then
        last_div.content:extend(b.content)
      elseif kind then
        local content, label = b.content, nil
        if kind == "qr" or kind == "figure-brief" then
          content, label = drop_label(b.content)
          content = strip_brackets(content)
        elseif kind == "workspace" or kind == "givens" then
          content, label = drop_label(b.content)
        end
        local title = nil
        if kind == "workspace" and label then
          title = label:gsub("^[%s✎]+", ""):gsub("^[Aa][Cc][Tt][Ii][Vv][Ee] [Ll][Ee][Aa][Rr][Nn][Ii][Nn][Gg] [Ww][Oo][Rr][Kk][Ss][Pp][Aa][Cc][Ee]%s*", "")
          title = title:gsub("^[%d%.]+[A-Z]?%s*[—–%-]+%s*", "")
          if title == "" then title = nil end
        end
        local div = make_div(kind, content, title)
        out:insert(div)
        last_kind, last_div = kind, div
      else
        out:insert(b)
        last_kind, last_div = nil, nil
      end
    else
      out:insert(b)
      if b.t ~= "HorizontalRule" then last_kind, last_div = nil, nil end
    end
  end
  return out
end

-- Group the blocks after a scaffold heading (until the next heading of the
-- same or higher level) into the matching box.
local function recover_sections(blocks)
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    if b.t == "Header" and b.level >= 3 then
      local text = stringify(b.content)
      local kind = scaffold_kind(text)
      if kind then
        local j = i + 1
        local body = pandoc.List()
        while j <= #blocks and not (blocks[j].t == "Header" and blocks[j].level <= b.level) do
          body:insert(blocks[j])
          j = j + 1
        end
        if kind == "drop" then
          out:extend(body)
        else
          local title = nil
          if kind == "summary" or kind == "practical" or kind == "exam-trap" or kind == "hook" then
            title = clean_title(text) or text
            title = title:gsub("%s*%(%s*[Ss]ub%-[Ss]ections.-%)%s*$", "")
            title = title:gsub("^[Ee]xemplar%s+A%*%s*", ""):gsub("^%s*[Aa]bstract%-to%-[Cc]oncrete%s+", "")
          elseif kind == "objectives" then
            title = is_id and "Tujuan Pembelajaran" or "Learning Objectives"
          end
          if kind == "worked-example" then
            -- a G.I.V.E.N.S. box inside a worked example is the solution itself
            body = pandoc.Blocks(body):walk({ Div = function(d)
              if d.classes:includes("givens") then
                return d.content
              end
            end })
          end
          out:insert(make_div(kind, body, title))
        end
        i = j
      else
        out:insert(b)
        i = i + 1
      end
    else
      out:insert(b)
      i = i + 1
    end
  end
  return out
end

local function has_explicit_boxes(doc)
  local found = false
  doc:walk({ Div = function(d)
    for _, c in ipairs(d.classes) do
      if c ~= "cell" then found = true end
    end
  end })
  return found
end

function Pandoc(doc)
  local lang = doc.meta.lang and stringify(doc.meta.lang) or "id"
  is_id = lang:sub(1, 2) == "id"
  -- math + code first (everywhere)
  doc = doc:walk({
    Inlines = function(inl) return rescue_math(inl) end,
  })
  doc = doc:walk({
    Code = soften_code,
    Header = clean_header,
    HorizontalRule = function() return {} end,
  })
  -- Quarto HTML books lift each chapter's H1 into the page title first.
  if doc.meta.title and pandoc.utils.type(doc.meta.title) == "Inlines" then
    local h = clean_header(pandoc.Header(1, doc.meta.title))
    if h and h.content then doc.meta.title = h.content end
  end
  -- A line that is only display math: "$$ ... $$" ends up as Para{Math Display}
  local blocks = recover_quotes(doc.blocks)
  blocks = recover_sections(blocks)
  doc.blocks = blocks
  return doc
end
