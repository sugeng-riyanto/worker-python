"""Build a B5 Word reference document and the Gold Standard paragraph styles."""

from __future__ import annotations

import io
import re
import subprocess
import zipfile
from pathlib import Path

from physics_studio.palettes import DEFAULT_PALETTE, docx_palette
from physics_studio.render_error import RenderError

# 176 mm × 250 mm in twips, and the spec margins (inner 20 mm, outer 14 mm, 18 mm vertical).
_PAGE_SIZE = '<w:pgSz w:w="9978" w:h="14173"/>'
_PAGE_MARGINS = (
    '<w:pgMar w:top="1020" w:right="794" w:bottom="1020" w:left="1134" '
    'w:header="450" w:footer="450" w:gutter="0"/>'
)

# Box paragraph styles: style id -> (fill role, left-border role). Roles are
# palette keys (physics_studio.palettes); colours follow typst-show.typ.
_STYLES = {
    "WorkspaceBox": ("green-soft", "green"),
    "GivensBox": ("surface", "accent"),
    "ExamTrap": ("red-soft", "red"),
    "BoxObjectives": ("primary-soft", "primary"),
    "BoxWorkedExample": ("surface", "accent"),
    "BoxPractice": ("surface", "navy"),
    "BoxReview": ("surface", "primary"),
    "BoxSummary": ("blue-softer", "blue"),
    "BoxDefinition": ("blue-soft", "blue-soft"),
    "BoxHook": ("blue-softer", "primary"),
    "BoxPractical": ("purple-soft", "purple"),
    "BoxThink": ("green-soft", "green"),
    "BoxFigureBrief": ("surface", "grey"),
    "BoxNote": ("grey-soft", "grey"),
    "BoxAside": ("blue-softer", "navy"),
}

# Word has no font fallback, so DOCX uses fonts that ship with Office:
# Calibri for body text (humanist sans like the PDF) and Arial Narrow for headings.
_BODY_FONT = "Calibri"
_HEAD_FONT = "Arial Narrow"
_PRIMARY = "@primary@"
_PRIMARY_TEXT = "@primary-text@"
_NAVY = "@navy@"
_BLUE = "@table-head@"

_BASE_STYLES = {
    "Normal": f"""<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
  <w:name w:val="Normal"/><w:qFormat/>
  <w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_BODY_FONT}" w:hAnsi="{_BODY_FONT}" w:cs="{_BODY_FONT}"/><w:color w:val="@ink@"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>
</w:style>
""",
    "Heading1": f"""<w:style w:type="paragraph" w:styleId="Heading1">
  <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:link w:val="Heading1Char"/><w:uiPriority w:val="9"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:pageBreakBefore/><w:shd w:val="clear" w:color="auto" w:fill="{_PRIMARY}"/>
    <w:spacing w:before="0" w:after="360"/><w:ind w:left="0" w:right="0"/>
    <w:pBdr><w:top w:val="single" w:sz="48" w:space="12" w:color="{_PRIMARY}"/><w:left w:val="single" w:sz="48" w:space="8" w:color="{_PRIMARY}"/><w:bottom w:val="single" w:sz="48" w:space="12" w:color="{_PRIMARY}"/><w:right w:val="single" w:sz="48" w:space="8" w:color="{_PRIMARY}"/></w:pBdr>
    <w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:bCs/><w:color w:val="@on-primary@"/><w:sz w:val="52"/><w:szCs w:val="52"/></w:rPr>
</w:style>
""",
    "Heading2": f"""<w:style w:type="paragraph" w:styleId="Heading2">
  <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:link w:val="Heading2Char"/><w:uiPriority w:val="9"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:shd w:val="clear" w:color="auto" w:fill="{_PRIMARY}"/><w:spacing w:before="360" w:after="160"/>
    <w:pBdr><w:top w:val="single" w:sz="24" w:space="3" w:color="{_PRIMARY}"/><w:left w:val="single" w:sz="24" w:space="6" w:color="{_PRIMARY}"/><w:bottom w:val="single" w:sz="24" w:space="3" w:color="{_PRIMARY}"/><w:right w:val="single" w:sz="24" w:space="6" w:color="{_PRIMARY}"/></w:pBdr>
    <w:outlineLvl w:val="1"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:bCs/><w:color w:val="@on-primary@"/><w:sz w:val="34"/><w:szCs w:val="34"/></w:rPr>
</w:style>
""",
    "Heading3": f"""<w:style w:type="paragraph" w:styleId="Heading3">
  <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:link w:val="Heading3Char"/><w:uiPriority w:val="9"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="100"/><w:outlineLvl w:val="2"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:bCs/><w:color w:val="@ink@"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr>
</w:style>
""",
    "Heading4": f"""<w:style w:type="paragraph" w:styleId="Heading4">
  <w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:link w:val="Heading4Char"/><w:uiPriority w:val="9"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="3"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:bCs/><w:color w:val="{_PRIMARY_TEXT}"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
</w:style>
""",
    "TOCHeading": f"""<w:style w:type="paragraph" w:styleId="TOCHeading">
  <w:name w:val="TOC Heading"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:qFormat/>
  <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="240"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:bCs/><w:color w:val="{_PRIMARY_TEXT}"/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr>
</w:style>
""",
    "Title": f"""<w:style w:type="paragraph" w:styleId="Title">
  <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:link w:val="TitleChar"/><w:uiPriority w:val="10"/><w:qFormat/>
  <w:pPr><w:spacing w:before="1200" w:after="200"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="{_HEAD_FONT}" w:hAnsi="{_HEAD_FONT}" w:cs="{_HEAD_FONT}"/><w:b/><w:color w:val="{_PRIMARY}"/><w:sz w:val="64"/><w:szCs w:val="64"/></w:rPr>
</w:style>
""",
    "Caption": f"""<w:style w:type="paragraph" w:styleId="Caption">
  <w:name w:val="caption"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:before="60" w:after="160"/></w:pPr>
  <w:rPr><w:i/><w:color w:val="{_NAVY}"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
</w:style>
""",
    "Table": f"""<w:style w:type="table" w:default="1" w:styleId="Table">
  <w:name w:val="Table"/><w:basedOn w:val="TableNormal"/><w:uiPriority w:val="59"/><w:qFormat/>
  <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
  <w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr>
  <w:tblPr><w:tblStyleRowBandSize w:val="1"/><w:tblInd w:w="0" w:type="dxa"/>
    <w:tblBorders><w:insideV w:val="single" w:sz="4" w:space="0" w:color="@paper@"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="@paper@"/></w:tblBorders>
    <w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr>
  <w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="@blue-softer@"/></w:tcPr>
  <w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:color w:val="@on-primary@"/></w:rPr><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{_BLUE}"/><w:vAlign w:val="bottom"/></w:tcPr></w:tblStylePr>
  <w:tblStylePr w:type="band1Horz"><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="@blue-soft@"/></w:tcPr></w:tblStylePr>
</w:style>
""",
}


def _style_xml(style_id: str, fill: str, border: str) -> str:
    return f"""<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">
  <w:name w:val="{style_id}"/>
  <w:basedOn w:val="Normal"/>
  <w:uiPriority w:val="99"/>
  <w:qFormat/>
  <w:pPr>
    <w:spacing w:before="120" w:after="120" w:line="288" w:lineRule="auto"/>
    <w:ind w:left="180" w:right="120"/>
    <w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>
    <w:pBdr>
      <w:top w:val="single" w:sz="4" w:space="6" w:color="{border}"/>
      <w:left w:val="single" w:sz="24" w:space="10" w:color="{border}"/>
      <w:bottom w:val="single" w:sz="4" w:space="6" w:color="{border}"/>
      <w:right w:val="single" w:sz="4" w:space="8" w:color="{border}"/>
    </w:pBdr>
  </w:pPr>
</w:style>
"""


def _replace_tag(xml: str, tag: str, replacement: str) -> str:
    updated, count = re.subn(rf"<{tag}\b[^>]*/>", replacement, xml, count=1)
    if count:
        return updated
    updated, count = re.subn(rf"<{tag}\b[^>]*>.*?</{tag}>", replacement, xml, count=1, flags=re.DOTALL)
    if count:
        return updated
    updated, count = re.subn(r"</w:sectPr>", replacement + "</w:sectPr>", xml, count=1)
    if not count:
        raise RenderError("Could not apply B5 page geometry to reference.docx")
    return updated


def _patch_document(xml: str) -> str:
    xml = _replace_tag(xml, "w:pgSz", _PAGE_SIZE)
    return _replace_tag(xml, "w:pgMar", _PAGE_MARGINS)


def _patch_settings(xml: str) -> str:
    if "<w:mirrorMargins" in xml:
        return xml
    if "</w:settings>" not in xml:
        raise RenderError("reference.docx is missing word settings")
    return xml.replace("</w:settings>", "<w:mirrorMargins/></w:settings>", 1)


def _colour(template: str, palette: dict[str, str]) -> str:
    return re.sub(r"@([a-z-]+)@", lambda m: palette[m.group(1)], template)


def _patch_styles(xml: str, palette_name: str = DEFAULT_PALETTE) -> str:
    if "</w:styles>" not in xml:
        raise RenderError("reference.docx is missing word styles")
    for style_id in _BASE_STYLES:
        xml = re.sub(
            rf'<w:style\b[^>]*w:styleId="{style_id}"[^>]*>.*?</w:style>\s*',
            "",
            xml,
            count=1,
            flags=re.DOTALL,
        )
    palette = docx_palette(palette_name)
    addition = _colour("".join(_BASE_STYLES.values()), palette)
    addition += "".join(_style_xml(name, palette[fill], palette[border]) for name, (fill, border) in _STYLES.items())
    return xml.replace("</w:styles>", addition + "</w:styles>", 1)


def apply_b5(docx_path: Path, palette: str = DEFAULT_PALETTE) -> None:
    """Patch page geometry and Gold Standard styles into an existing docx."""
    original = docx_path.read_bytes()
    buffer_path = docx_path.with_suffix(".patched.docx")
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(
        buffer_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as result:
        for member in source.infolist():
            data = source.read(member)
            if member.filename == "word/document.xml":
                data = _patch_document(data.decode("utf-8")).encode("utf-8")
            elif member.filename == "word/settings.xml":
                data = _patch_settings(data.decode("utf-8")).encode("utf-8")
            elif member.filename == "word/styles.xml":
                data = _patch_styles(data.decode("utf-8"), palette).encode("utf-8")
            result.writestr(member, data)
    buffer_path.replace(docx_path)


def write_reference(target: Path, quarto: str, env: dict[str, str], palette: str = DEFAULT_PALETTE) -> None:
    """Ask Quarto's Pandoc for its default reference doc and apply B5 styles."""
    proc = subprocess.run(
        [quarto, "pandoc", "--print-default-data-file=reference.docx"],
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.startswith(b"PK"):
        detail = (proc.stderr or b"").decode("utf-8", errors="replace")[-1500:]
        raise RenderError(f"Could not build the Word reference document.\n{detail}")
    target.write_bytes(proc.stdout)
    apply_b5(target, palette)
