-- Render Gold Standard fenced divs in every Quarto format.
-- Authors write ::: {.givens}, ::: {.exam-trap}, and ::: {.workspace}.

local ALIAS = {
  workspace = "workspace",
  ["active-workspace"] = "workspace",
  givens = "givens",
  ["givens-box"] = "givens",
  ["exam-trap"] = "exam-trap",
  examtrap = "exam-trap",
}

local SPECS = {
  workspace = {
    label = "Active Learning Workspace",
    style = "WorkspaceBox",
    fill = "#F0F9FF",
    accent = "#0284C7",
  },
  givens = {
    label = "G.I.V.E.N.S. Problem-Solving Protocol",
    style = "GivensBox",
    fill = "#F8FAFC",
    accent = "#0F2942",
  },
  ["exam-trap"] = {
    label = "Exam Trap",
    style = "ExamTrap",
    fill = "#FEF2F2",
    accent = "#DC2626",
  },
}

local function kind_of(el)
  for _, class in ipairs(el.classes) do
    local kind = ALIAS[class]
    if kind then
      return kind
    end
  end
  return nil
end

local function is_typst()
  return FORMAT == "typst" or FORMAT:match("^typst") ~= nil
end

local function typst_box(spec, inner)
  return table.concat({
    "#block(",
    "  width: 100%,",
    "  inset: (x: 10pt, y: 8pt),",
    "  radius: 3pt,",
    "  breakable: false,",
    '  fill: rgb("' .. spec.fill .. '"),',
    '  stroke: (left: 2.6pt + rgb("' .. spec.accent .. '")),',
    ")[",
    "  #text(fill: rgb(\"" .. spec.accent .. "\"), weight: \"bold\", size: 9pt, font: (\"Inter\", \"Source Serif 4\"))[" .. spec.label .. "]",
    "  #v(5pt)",
    inner,
    "]",
  }, "\n")
end

local function label_paragraph(text)
  return pandoc.Para({
    pandoc.Span(pandoc.Strong(text), pandoc.Attr("", { "box-label" }, {})),
  })
end

function Div(el)
  if el.classes:includes("gold-box-done") then
    return nil
  end
  local kind = kind_of(el)
  if not kind then
    return nil
  end
  local spec = SPECS[kind]
  if is_typst() then
    local ok, inner = pcall(function()
      return pandoc.write(pandoc.Pandoc(el.content), "typst")
    end)
    if not ok then
      return nil
    end
    return pandoc.RawBlock("typst", typst_box(spec, inner))
  end
  if FORMAT == "docx" then
    local blocks = { label_paragraph(spec.label) }
    for _, block in ipairs(el.content) do
      blocks[#blocks + 1] = block
    end
    return pandoc.Div(blocks, pandoc.Attr("", { "gold-box-done" }, { { "custom-style", spec.style } }))
  end
  local blocks = { label_paragraph(spec.label) }
  for _, block in ipairs(el.content) do
    blocks[#blocks + 1] = block
  end
  local classes = { kind, "gold-box-done" }
  return pandoc.Div(blocks, pandoc.Attr("", classes, {}))
end
