"""Runtime UI language switching: a flat dictionary keyed by the Russian source text.

Mirrors ui/theme.py's module-global pattern (set_theme_mode/theme_mode) so the
rest of the app wires language the same way it already wires theme.
"""
from __future__ import annotations

_TRANSLATIONS: dict[str, str] = {
    # main_window.py
    "Конвертер": "Converter",
    "Пресеты": "Presets",
    "Настройки": "Settings",
    "Переключить тему": "Switch theme",
    "Тема: Системная": "Theme: System",
    "Тема: Светлая": "Theme: Light",
    "Тема: Тёмная": "Theme: Dark",
    "Тема": "Theme",
    "Дождитесь завершения текущей конвертации": "Wait for the current conversion to finish",
    "Отпустите, чтобы добавить файлы": "Drop to add files",
    # settings_page.py
    "Папка вывода": "Output folder",
    "converted/ рядом с исходником": "converted/ next to the source file",
    "Фиксированная папка": "Fixed folder",
    "Выбрать папку…": "Choose folder…",
    "Выберите папку для сохранения": "Choose a folder to save to",
    "Добавлять суффикс (1)": "Add suffix (1)",
    "Перезаписывать": "Overwrite",
    "Конфликты имён": "Name conflicts",
    "Система": "System",
    "Светлая": "Light",
    "Тёмная": "Dark",
    "Авто": "Auto",
    "Максимум параллельных задач": "Max parallel tasks",
    "Кодек видео по умолчанию": "Default video codec",
    "Язык": "Language",
    "Авто (CPU x264)": "Auto (CPU x264)",
    # converter_page.py
    "Добавьте файлы или перетащите их в окно": "Add files or drag them into the window",
    "Открыть папку вывода": "Open output folder",
    "Выберите файлы для конвертации": "Choose files to convert",
    "Выбранный формат недоступен для этого файла.": (
        "The selected format is not available for this file."
    ),
    "Нет поддерживаемых файлов для конвертации": "No supported files to convert",
    "Останавливаю текущие задачи…": "Stopping current tasks…",
    "Готово {done}": "Done {done}",
    "Ошибки {failed}": "Errors {failed}",
    "Отменено {cancelled}": "Cancelled {cancelled}",
    "Готово {done} · В работе {running}": "Done {done} · Running {running}",
    # command_bar.py
    "Добавить файлы": "Add files",
    "Конвертировать": "Convert",
    "Конвертировать {n}": "Convert {n}",
    "Отменить": "Cancel",
    # task_queue.py
    "Перетащите файлы сюда": "Drag files here",
    "или нажмите кнопку, чтобы выбрать вручную": "or click the button to choose manually",
    "Выбрать файлы": "Choose files",
    # file_row.py
    "Изображение": "Image",
    "Аудио": "Audio",
    "Видео": "Video",
    "Документ": "Document",
    "Неизвестный тип": "Unknown type",
    "Убрать файл из очереди": "Remove file from queue",
    "Пресет": "Preset",
    "Свои настройки": "Custom settings",
    "Качество": "Quality",
    "Битрейт аудио": "Audio bitrate",
    "Битрейт видео": "Video bitrate",
    "Кодек": "Codec",
    "Сбросить к пресету": "Reset to preset",
    "Копировать текст ошибки": "Copy error text",
    "Открыть": "Open",
    "Папка": "Folder",
    "Не удалось конвертировать: {error}": "Conversion failed: {error}",
    # presets_page.py
    "Изображения": "Images",
    "Документы": "Documents",
    "качество {q}": "quality {q}",
    "пустой пресет": "empty preset",
    "Новый пресет": "New preset",
    "Название пресета": "Preset name",
    "Тип файлов": "File type",
    "Формат": "Format",
    "Сохранить": "Save",
    "Отмена": "Cancel",
    "  · встроенный": "  · built-in",
    "Применить": "Apply",
    "Дублировать": "Duplicate",
    "Редактировать": "Edit",
    "Удалить": "Delete",
    "Без названия": "Untitled",
    # core error messages
    "Конвертер '{name}' не найден": "Converter '{name}' not found",
    "Не удалось открыть изображение: {name}": "Failed to open image: {name}",
    "Ошибка при сохранении {name}: {error}": "Error while saving {name}: {error}",
    "Не удалось открыть stderr процесса FFmpeg": "Failed to open FFmpeg process stderr",
}

_current_language = "ru"


def set_language(code: str) -> None:
    global _current_language
    _current_language = code if code in ("ru", "en") else "ru"


def current_language() -> str:
    return _current_language


def t(text: str) -> str:
    if _current_language == "en":
        return _TRANSLATIONS.get(text, text)
    return text
