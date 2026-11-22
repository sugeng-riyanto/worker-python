"""Build a B5 Word reference document and the Gold Standard paragraph styles."""

from __future__ import annotations

import io
import re
import subprocess
import zipfile
from pathlib import Path

from physics_studio.render_error import RenderError

# 176 mm × 250 mm in twips, and the spec margins (inner 20 mm, outer 14 mm, 18 mm vertical).
_PAGE_SIZE = '<w:pgSz w:w="9978" w:h="14173"/>'
_PAGE_MARGINS = (
    '<w:pgMar w:top="1020" w:right="794" w:bottom="1020" w:left="1134" '
    'w:header="450" w:footer="450" w:gutter="0"/>'
)

_STYLES = {
    "WorkspaceBox": ("E0F2FE", "0284C7"),
    "GivensBox": ("F1F5F9", "0F2942"),
    "ExamTrap": ("FEE2E2", "DC2626"),
}


def _style_xml(style_id: str, fill: str, border: str) -> str:
    return f"""<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">
  <w:name w:val="{style_id}"/>
  <w:basedOn w:val="Normal"/>
  <w:uiPriority w:val="99"/>
  <w:qFormat/>
  <w:pPr>
    <w:spacing w:before="160" w:after="160" w:line="312" w:lineRule="auto"/>
    <w:ind w:left="180" w:right="120"/>
    <w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>
    <w:pBdr>
      <w:top w:val="single" w:sz="4" w:space="8" w:color="{fill}"/>
      <w:left w:val="single" w:sz="24" w:space="10" w:color="{border}"/>
      <w:bottom w:val="single" w:sz="4" w:space="8" w:color="{fill}"/>
      <w:right w:val="single" w:sz="4" w:space="8" w:color="{fill}"/>
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


def _patch_styles(xml: str) -> str:
    if "</w:styles>" not in xml:
        raise RenderError("reference.docx is missing word styles")
    addition = "".join(_style_xml(name, fill, border) for name, (fill, border) in _STYLES.items())
    return xml.replace("</w:styles>", addition + "</w:styles>", 1)


def apply_b5(docx_path: Path) -> None:
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
                data = _patch_styles(data.decode("utf-8")).encode("utf-8")
            result.writestr(member, data)
    buffer_path.replace(docx_path)


def write_reference(target: Path, quarto: str, env: dict[str, str]) -> None:
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
    apply_b5(target)
