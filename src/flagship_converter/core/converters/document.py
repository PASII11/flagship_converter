"""Конвертер документов (PDF, DOCX, MD) на базе Docling и pdfkit."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import markdown
import pdfkit
from docx import Document
from docling.document_converter import DocumentConverter

# Жизненно важные настройки для HuggingFace на Windows без админа
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HUGGINGFACE_HUB_VERBOSITY"] = "error"

# Патчим симлинки до любых других импортов
import shutil
import huggingface_hub.file_download as _hf_fd

def _safe_symlink(src: str, dst: str, **kwargs: object) -> None:
    try:
        os.symlink(src, dst)
    except (OSError, NotImplementedError):
        src_abs = os.path.join(os.path.dirname(dst), src) if not os.path.isabs(src) else src
        if not os.path.exists(dst):
            shutil.copy2(src_abs, dst)

_hf_fd._create_symlink = _safe_symlink  # type: ignore[attr-defined]


from docling.datamodel.base_models import DocumentStream
from docling.datamodel.pipeline_options import PipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from flagship_converter.core.converters.base import safe_output_path
from flagship_converter.core.converters.media import get_wkhtmltopdf_path

SUPPORTED_INPUT = {".pdf", ".docx", ".md"}
SUPPORTED_OUTPUT = {"pdf", "docx", "md"}


class DocConverter:
    """Конвертирует документы с сохранением структуры (PyInstaller-safe)."""

    def __init__(self) -> None:
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import PdfFormatOption

        # Ограничиваем потоки — критично для PyInstaller и стабильности в GUI
        accelerator_options = AcceleratorOptions(num_threads=1)

        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_options

        self._doc_converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_INPUT

    def build_output_path(
        self,
        input_path: Path,
        output_dir: Path,
        target_ext: str,
        overwrite: bool,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        base = output_dir / f"{input_path.stem}.{target_ext.lstrip('.')}"
        return safe_output_path(base, overwrite)

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        params: dict[str, object],
        cancel_cb: Callable[[], bool],
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        if cancel_cb():
            return

        target_ext = output_path.suffix.lower().lstrip(".")

        if progress_cb:
            progress_cb(10)

        # 1. Читаем исходник в Markdown (прямой вызов, без multiprocessing)
        if input_path.suffix.lower() == ".md":
            md_text = input_path.read_text(encoding="utf-8")
        else:
            conv_res = self._doc_converter.convert(str(input_path))
            md_text = conv_res.document.export_to_markdown()

        if cancel_cb():
            return

        if progress_cb:
            progress_cb(60)

        # 2. Пишем в целевой формат
        if target_ext == "md":
            output_path.write_text(md_text, encoding="utf-8")

        elif target_ext == "pdf":
            html_content = markdown.markdown(md_text, extensions=["tables"])
            full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
    body {{ font-family: sans-serif; line-height: 1.5; padding: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    img {{ max-width: 100%; }}
</style></head><body>{html_content}</body></html>"""

            wk_path = get_wkhtmltopdf_path()
            config = pdfkit.configuration(wkhtmltopdf=wk_path)
            options = {"quiet": "", "encoding": "UTF-8", "enable-local-file-access": ""}
            pdfkit.from_string(full_html, str(output_path), configuration=config, options=options)

        elif target_ext == "docx":
            doc = Document()
            for line in md_text.split("\n"):
                if line.startswith("# "):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith("## "):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith("### "):
                    doc.add_heading(line[4:], level=3)
                elif line.strip():
                    doc.add_paragraph(line)
            doc.save(str(output_path))

        if progress_cb:
            progress_cb(100)
