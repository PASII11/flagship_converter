"""Конвертер изображений на базе Pillow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from flagship_converter.core.converters.base import safe_output_path

SUPPORTED_INPUT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
SUPPORTED_OUTPUT = {"png", "jpg", "jpeg", "webp", "bmp", "tiff"}


class ImageConverter:
    """Конвертирует изображения между форматами через Pillow."""

    supported_outputs = SUPPORTED_OUTPUT

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

        q_obj = params.get("quality")
        if isinstance(q_obj, int):
            quality = q_obj
        elif isinstance(q_obj, str):
            quality = int(q_obj)
        else:
            quality = 85

        lossless_webp = bool(params.get("lossless_webp", False))

        try:
            img: Image.Image = Image.open(input_path)
            with img:
                save_kwargs: dict[str, int | bool] = {}

                if target_ext in ("jpg", "jpeg"):
                    quality = max(1, min(quality, 95))
                    if img.mode in ("RGBA", "P", "LA"):
                        img = img.convert("RGB")
                    save_kwargs = {"quality": quality, "optimize": True}

                elif target_ext == "png":
                    save_kwargs = {"optimize": True}

                elif target_ext == "webp":
                    if lossless_webp:
                        save_kwargs = {"lossless": True}
                    else:
                        quality = max(1, min(quality, 95))
                        save_kwargs = {"quality": quality}

                output_path.parent.mkdir(parents=True, exist_ok=True)

                fmt_map = {
                    "jpg": "JPEG",
                    "jpeg": "JPEG",
                    "png": "PNG",
                    "webp": "WEBP",
                    "bmp": "BMP",
                    "tiff": "TIFF",
                }
                pil_format = fmt_map.get(target_ext, target_ext.upper())
                img.save(str(output_path), format=pil_format, **save_kwargs)

                if progress_cb:
                    progress_cb(100)

        except UnidentifiedImageError as e:
            raise RuntimeError(f"Не удалось открыть изображение: {input_path.name}") from e
        except OSError as e:
            raise RuntimeError(f"Ошибка при сохранении {output_path.name}: {e}") from e
