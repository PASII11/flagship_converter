# Flagship Converter

Privacy-first file converter for Windows. Everything runs locally on your
machine: no uploads, no accounts, no telemetry.

![Flagship Converter](docs/assets/screenshot.png)

## Features

- **Images:** convert PNG, JPEG, WebP, BMP, TIFF and AVIF (opens HEIC/HEIF and
  GIF too), with per-file quality control.
- **Video:** convert MP4, MKV, AVI, MOV, WebM, FLV and M4V, compress a video to
  an exact file size, extract audio (MP3, WAV, FLAC, AAC, OGG) or turn clips
  into GIFs.
- **Audio:** convert MP3, WAV, FLAC, AAC, M4A, OGG and WMA.
- **Documents:** convert between PDF, DOCX and Markdown with layout-aware
  parsing and built-in OCR, so scanned PDFs work too.
- **Batch queue:** drop in files or whole folders, convert in parallel, tweak
  settings per file and save presets you use often.
- **Interface:** light and dark themes, English and Russian.

## Download

Grab the latest version from the
[Releases page](https://github.com/PASII11/flagship_converter/releases/latest):

- `FlagshipConverter-Setup-<version>.exe` if you just want to install and go.
- `FlagshipConverter-<version>-portable-win64.zip` if you prefer to unzip it
  anywhere and run it without installing.

Works on Windows 10/11 x64 and takes about 3 GB of disk space. Everything the
app needs (FFmpeg, OCR models, document parsers) is already inside.

On startup the app checks GitHub for a new release and shows an "Update
available" button when there is one. Your files never leave your machine.

## Build from source

You need [uv](https://docs.astral.sh/uv/), plus `ffmpeg` and `wkhtmltopdf`
on `PATH`.

```bash
uv sync
uv run python -m pytest                    # run tests
uv run python -m flagship_converter.app    # run from source
uv run python build.py                     # build dist/FlagshipConverter
```

## License

[MIT](LICENSE)
