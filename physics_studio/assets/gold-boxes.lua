-- Render learning boxes (fenced divs) in every Quarto format.
--
-- Main-column boxes:  ::: {.objectives} {.worked-example} {.givens} {.practice}
--   {.review} {.summary} {.definition} {.key-equation} {.workspace}
--   {.exam-trap} {.hook} {.practical} {.think} {.figure-brief} {.note}
-- Sidebar notes (PDF outer margin, floated in HTML):
--   {.quick-check} {.remember} {.key-terms} {.qr} {.teacher-note}
--   {.enrichment} {.info} {.link}
-- Indonesian aliases are accepted (e.g. .contoh-soal, .latihan, .tujuan).
-- An optional title="..." attribute overrides the default label.

local ALIAS = {
  workspace = "workspace", ["active-workspace"] = "workspace", ["ruang-kerja"] = "workspace",
  givens = "givens", ["givens-box"] = "givens",
  ["exam-trap"] = "exam-trap", examtrap = "exam-trap", ["jebakan"] = "exam-trap", ["common-mistake"] = "exam-trap",
  objectives = "objectives", ["learning-objectives"] = "objectives", ["learning-outcomes"] = "objectives", tujuan = "objectives",
  ["worked-example"] = "worked-example", example = "worked-example", ["contoh-soal"] = "worked-example",
  practice = "practice", ["lets-practise"] = "practice", latihan = "practice", exercise = "practice",
  review = "review", ["lets-review"] = "review", ["uji-kompetensi"] = "review", ["end-of-chapter"] = "review",
  summary = "summary", rangkuman = "summary", ["key-points"] = "summary",
  definition = "definition", definisi = "definition", ["key-concept"] = "definition",
  ["key-equation"] = "key-equation", equation = "key-equation", rumus = "key-equation",
  hook = "hook", fenomena = "hook", phenomenon = "hook",
  practical = "practical", praktikum = "practical", activity = "practical", kegiatan = "practical",
  think = "think", ["pertanyaan-pemantik"] = "think", ["trigger-questions"] = "think",
  ["figure-brief"] = "figure-brief", ilustrasi = "figure-brief", ["diagram-brief"] = "figure-brief",
  note = "note", catatan = "note",
  ["quick-check"] = "quick-check", ["cek-cepat"] = "quick-check",
  remember = "remember", ingat = "remember", tip = "remember",
  ["key-terms"] = "key-terms", istilah = "key-terms", glossary = "key-terms",
  qr = "qr", ["qr-watch"] = "qr",
  ["teacher-note"] = "teacher-note", ["catatan-guru"] = "teacher-note",
  enrichment = "enrichment", pengayaan = "enrichment",
  info = "info", ["did-you-know"] = "info", tahukah = "info",
  link = "link", tautan = "link",
}

-- label = { id, en }; numbered boxes get "<label> <chapter>.<n>" in the PDF.
local SPECS = {
  objectives = { label = { "Dalam subbab ini, kamu akan mempelajari:", "In this section, you will learn the following:" }, style = "BoxObjectives", fill = "#FDE3CC", accent = "#F47415" },
  ["worked-example"] = { label = { "Contoh Soal", "Worked Example" }, numbered = "example", style = "BoxWorkedExample", fill = "#FFFFFF", accent = "#D5164F" },
  givens = { label = { "Contoh Soal", "Worked Example" }, numbered = "example", style = "GivensBox", fill = "#FFFFFF", accent = "#D5164F" },
  practice = { label = { "Ayo Berlatih", "Let's Practise" }, numbered = "practice", style = "BoxPractice", fill = "#FFFFFF", accent = "#1B4F8A" },
  review = { label = { "Ayo Mengulang", "Let's Review" }, wide = true, style = "BoxReview", fill = "#FFFFFF", accent = "#F47415" },
  summary = { label = { "Ringkasan", "Summary" }, style = "BoxSummary", fill = "#F1F8FC", accent = "#0089C0" },
  definition = { label = nil, style = "BoxDefinition", fill = "#E1F1FA", accent = "#1B4F8A" },
  ["key-equation"] = { label = nil, style = "BoxDefinition", fill = "#E1F1FA", accent = "#1B4F8A" },
  workspace = { label = { "Ruang Kerja Aktif", "Active Learning Workspace" }, style = "WorkspaceBox", fill = "#E5F3E3", accent = "#3E9B46" },
  ["exam-trap"] = { label = { "Jebakan Ujian", "Exam Trap" }, style = "ExamTrap", fill = "#FCE7E6", accent = "#D62828" },
  hook = { label = { "Fenomena", "Real-World Hook" }, style = "BoxHook", fill = "#F1F8FC", accent = "#F47415" },
  practical = { label = { "Kegiatan Praktikum", "Practical Activity" }, style = "BoxPractical", fill = "#EFE6F6", accent = "#7A4FA0" },
  think = { label = { "Pertanyaan Pemantik", "Think About It" }, box = "workspace", style = "BoxThink", fill = "#E5F3E3", accent = "#3E9B46" },
  ["figure-brief"] = { label = { "Ilustrasi", "Illustration" }, style = "BoxFigureBrief", fill = "#FFFFFF", accent = "#6B7280" },
  note = { label = nil, style = "BoxNote", fill = "#F2F2F2", accent = "#6B7280" },
  ["quick-check"] = { label = { "Cek Cepat", "Quick Check" }, aside = true, style = "BoxAside", fill = "#E5F3E3", accent = "#3E9B46" },
  remember = { label = { "Ingat!", "Remember" }, aside = true, style = "BoxAside", fill = "#FDE3CC", accent = "#F47415" },
  ["key-terms"] = { label = { "Istilah Kunci", "Key Terms" }, aside = true, style = "BoxAside", fill = "#E1F1FA", accent = "#1B4F8A" },
  qr = { label = { "Pindai", "Scan" }, aside = true, style = "BoxAside", fill = "#FFFFFF", accent = "#1B4F8A" },
  ["teacher-note"] = { label = { "Catatan Guru", "Teacher Note" }, aside = true, style = "BoxAside", fill = "#F2F2F2", accent = "#6B7280" },
  enrichment = { label = { "Pengayaan", "Enrichment" }, aside = true, style = "BoxAside", fill = "#EFE6F6", accent = "#7A4FA0" },
  info = { label = { "Tahukah Kamu?", "Did You Know?" }, aside = true, style = "BoxAside", fill = "#F1F8FC", accent = "#0089C0" },
  link = { label = { "Tautan", "Link" }, aside = true, style = "BoxAside", fill = "#FCE7E6", accent = "#D5164F" },
}

-- Sidebar notes longer than this stay in the main column (the sidebar is 34 mm).
local ASIDE_LIMIT = 420

local is_indonesian = true

local function kind_of(el)
  for _, class in ipairs(el.classes) do
    local kind = ALIAS[class]
    if kind then return kind end
  end
  return nil
end

local function is_typst()
  return FORMAT == "typst" or FORMAT:match("^typst") ~= nil
end

local function label_for(spec)
  if not spec.label then return nil end
  return is_indonesian and spec.label[1] or spec.label[2]
end

local function typst_inline(text)
  local doc = pandoc.read(text, "markdown")
  local out = pandoc.write(doc, "typst")
  return (out:gsub("%s+$", ""))
end

local function typst_open(kind, spec, title_text, explicit, as_aside)
  local title
  if title_text and title_text ~= "" then
    title = "[" .. typst_inline(title_text) .. "]"
    if spec.numbered and not explicit then
      title = "[" .. typst_inline(title_text) .. " #bc-number(\"" .. spec.numbered .. "\")]"
    end
  else
    title = "none"
  end
  if as_aside then
    return "#bc-aside(kind: \"" .. kind .. "\", title: " .. title .. ")["
  end
  local box_kind = kind == "think" and "workspace" or kind
  local wide = spec.wide and "true" or "false"
  return "#bc-box(kind: \"" .. box_kind .. "\", title: " .. title .. ", wide: " .. wide .. ")["
end

local function label_paragraph(text)
  return pandoc.Para({
    pandoc.Span(pandoc.Strong(text), pandoc.Attr("", { "box-label" }, {})),
  })
end

function Meta(meta)
  local lang = meta.lang and pandoc.utils.stringify(meta.lang) or "id"
  is_indonesian = lang:sub(1, 2) == "id"
end

local function render(el)
  if el.classes:includes("gold-box-done") then return nil end
  local kind = kind_of(el)
  if not kind then return nil end
  local spec = SPECS[kind]
  local explicit = el.attributes.title ~= nil and el.attributes.title ~= ""
  local title_text = explicit and el.attributes.title or label_for(spec)
  local as_aside = spec.aside and #pandoc.utils.stringify(el.content) <= ASIDE_LIMIT
  if spec.aside and not as_aside then
    kind = kind == "quick-check" and "think" or "note"
    spec = SPECS[kind]
    if not explicit then title_text = label_for(SPECS[ALIAS[el.classes[1]] or "note"]) or label_for(spec) end
  end

  if is_typst() then
    -- Open and close the Typst call around the native blocks, so Quarto still
    -- resolves cross-references, figures, and math inside the box.
    local blocks = pandoc.List({ pandoc.RawBlock("typst", typst_open(kind, spec, title_text, explicit, as_aside)) })
    blocks:extend(el.content)
    blocks:insert(pandoc.RawBlock("typst", "]"))
    return pandoc.Div(blocks, pandoc.Attr("", { "gold-box-done" }, {}))
  end

  local blocks = pandoc.List()
  if title_text and title_text ~= "" then blocks:insert(label_paragraph(title_text)) end
  blocks:extend(el.content)
  if FORMAT == "docx" then
    return pandoc.Div(blocks, pandoc.Attr("", { "gold-box-done" }, { { "custom-style", spec.style } }))
  end
  local classes = { kind, as_aside and "bc-aside" or "bc-box", "gold-box-done" }
  if spec.numbered then classes[#classes + 1] = "bc-numbered-" .. spec.numbered end
  if explicit then classes[#classes + 1] = "bc-explicit-title" end
  return pandoc.Div(blocks, pandoc.Attr("", classes, {}))
end

-- Render inner boxes first so nested boxes keep their own style.
return {
  { Meta = Meta },
  { Div = render },
}
