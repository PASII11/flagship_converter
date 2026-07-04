"""Centralized frontend theme tokens and QSS helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
RADIUS = {"panel": 12, "control": 8}


@dataclass(frozen=True)
class Palette:
    name: str
    is_dark: bool
    app_bg: str
    surface: str
    surface_secondary: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    running: str
    running_soft: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    error: str
    error_soft: str
    cat_image: str
    cat_audio: str
    cat_video: str
    cat_doc: str
    focus: str
    scrollbar: str
    scrollbar_hover: str


LIGHT = Palette(
    name="Light", is_dark=False,
    app_bg="#F6F7F9", surface="#FFFFFF", surface_secondary="#F1F3F6",
    border="#E4E7EC", border_strong="#CBD2DC",
    text_primary="#14181F", text_secondary="#5C6470", text_muted="#98A1AE",
    accent="#E50914", accent_hover="#C40812", accent_pressed="#A50710",
    accent_soft="#FDEBEC",
    running="#2E7CF6", running_soft="#EAF2FE",
    success="#1DA55A", success_soft="#E7F6EE",
    warning="#D97706", warning_soft="#FBF1DF",
    error="#DC2626", error_soft="#FCEBEB",
    cat_image="#2E7CF6", cat_audio="#D97706", cat_video="#7C5CFC",
    cat_doc="#0D9488",
    focus="#2E7CF6", scrollbar="#CBD2DC", scrollbar_hover="#98A1AE",
)

DARK = Palette(
    name="Dark", is_dark=True,
    app_bg="#101216", surface="#171A20", surface_secondary="#1E232B",
    border="#2A303B", border_strong="#3D4553",
    text_primary="#F2F4F8", text_secondary="#9AA3B2", text_muted="#6B7482",
    accent="#E50914", accent_hover="#FF2B35", accent_pressed="#B80710",
    accent_soft="#33161A",
    running="#5B9BFF", running_soft="#16233B",
    success="#34C97B", success_soft="#12291C",
    warning="#F2A33C", warning_soft="#2E2312",
    error="#F26D6D", error_soft="#33181A",
    cat_image="#5B9BFF", cat_audio="#F2A33C", cat_video="#9D86FF",
    cat_doc="#2CC7B2",
    focus="#5B9BFF", scrollbar="#3D4553", scrollbar_hover="#6B7482",
)

_mode = ThemeMode.SYSTEM
_palette = LIGHT


def detect_system_mode() -> ThemeMode:
    app = QApplication.instance()
    if app is None:
        return ThemeMode.LIGHT

    try:
        color_scheme = app.styleHints().colorScheme()
    except AttributeError:
        return ThemeMode.LIGHT

    if color_scheme == Qt.ColorScheme.Dark:
        return ThemeMode.DARK
    return ThemeMode.LIGHT


def resolve_palette(mode: ThemeMode) -> Palette:
    if mode == ThemeMode.DARK:
        return DARK
    if mode == ThemeMode.LIGHT:
        return LIGHT
    return DARK if detect_system_mode() == ThemeMode.DARK else LIGHT


def set_theme_mode(mode: ThemeMode | str) -> Palette:
    global _mode, _palette
    _mode = ThemeMode(mode)
    _palette = resolve_palette(_mode)
    return _palette


def theme_mode() -> ThemeMode:
    return _mode


def palette() -> Palette:
    if _mode == ThemeMode.SYSTEM:
        return resolve_palette(_mode)
    return _palette


def app_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QMainWindow {{
    background-color: {p.app_bg};
}}

QWidget {{
    color: {p.text_primary};
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    letter-spacing: 0px;
}}

QLabel {{
    background: transparent;
}}

QPushButton {{
    min-height: 34px;
    border-radius: 8px;
    padding: 0 14px;
    font-weight: 600;
    letter-spacing: 0px;
}}

QPushButton:focus, QComboBox:focus, QSpinBox:focus {{
    outline: none;
    border: 2px solid {p.focus};
}}

QToolTip {{
    background-color: {p.surface};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
    border-radius: 6px;
    padding: 6px 8px;
}}
"""


def root_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QWidget#Root {{
    background-color: {p.app_bg};
}}
"""


def panel_qss(object_name: str = "Panel", p: Palette | None = None, radius: int | None = None) -> str:
    p = p or palette()
    if radius is None:
        radius = RADIUS["panel"]
    return f"""
QFrame#{object_name} {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {radius}px;
}}
"""


def primary_button_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QPushButton {{
    background-color: {p.accent};
    color: #FFFFFF;
    border: 1px solid {p.accent};
    min-height: 40px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {p.accent_hover};
    border-color: {p.accent_hover};
}}
QPushButton:pressed {{
    background-color: {p.accent_pressed};
    border-color: {p.accent_pressed};
}}
QPushButton:disabled {{
    background-color: {p.surface_secondary};
    color: {p.text_muted};
    border-color: {p.border};
}}
"""


def secondary_button_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QPushButton {{
    background-color: {p.surface};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
}}
QPushButton:hover {{
    background-color: {p.surface_secondary};
    border-color: {p.border_strong};
}}
QPushButton:pressed {{
    background-color: {p.surface_secondary};
}}
QPushButton:disabled {{
    background-color: {p.surface_secondary};
    color: {p.text_muted};
    border-color: {p.border};
}}
"""


def ghost_button_qss(p: Palette | None = None, danger: bool = False) -> str:
    p = p or palette()
    color = p.error if danger else p.text_secondary
    hover_bg = p.error_soft if danger else p.surface_secondary
    hover_border = p.error if danger else p.border
    return f"""
QPushButton {{
    background-color: transparent;
    color: {color};
    border: 1px solid transparent;
}}
QPushButton:hover {{
    background-color: {hover_bg};
    color: {color if danger else p.text_primary};
    border-color: {hover_border};
}}
QPushButton:pressed {{
    background-color: {p.accent_soft if danger else p.surface_secondary};
}}
QPushButton:disabled {{
    color: {p.text_muted};
}}
"""


def input_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QComboBox, QSpinBox, QLineEdit {{
    background-color: {p.surface};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 26px;
}}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{
    border-color: {p.border_strong};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {p.surface};
    color: {p.text_primary};
    border: 1px solid {p.border};
    selection-background-color: {p.running};
    selection-color: #FFFFFF;
    outline: none;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    border: none;
    background: transparent;
    width: 18px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {p.accent_soft};
}}
"""


def checkbox_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QCheckBox {{
    color: {p.text_primary};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {p.border_strong};
    background-color: {p.surface};
}}
QCheckBox::indicator:hover {{
    border-color: {p.focus};
}}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border-color: {p.accent};
}}
QCheckBox:disabled {{
    color: {p.text_muted};
}}
"""


def scroll_area_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget#qt_scrollarea_viewport {{
    background: transparent;
}}
QScrollBar:vertical {{
    width: 10px;
    background: transparent;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p.scrollbar};
    border-radius: 5px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p.scrollbar_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


def text_style(color: str, size: int = 13, weight: int = 400) -> str:
    return f"color: {color}; font-size: {size}px; font-weight: {weight};"


def progress_qss(color: str, p: Palette | None = None) -> str:
    p = p or palette()
    return (
        "QProgressBar {"
        f"border: none; background-color: {p.surface_secondary}; border-radius: 3px;"
        "}"
        f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
    )


def chip_qss(fg: str, bg: str) -> str:
    return (
        "QComboBox, QLabel {"
        f"color: {fg}; background-color: {bg}; border: none;"
        "border-radius: 12px; padding: 3px 12px;"
        "font-size: 12px; font-weight: 600; min-height: 24px;"
        "}"
        "QComboBox::drop-down { border: none; width: 18px; }"
    )


def nav_button_qss(selected: bool, p: Palette | None = None) -> str:
    p = p or palette()
    if selected:
        return (
            "QPushButton {"
            f"background-color: {p.surface_secondary}; color: {p.text_primary};"
            f"border: 1px solid {p.border}; border-radius: {RADIUS['control']}px;"
            "padding: 0 16px; font-weight: 600;"
            "}"
        )
    return (
        "QPushButton {"
        f"background-color: transparent; color: {p.text_secondary};"
        f"border: 1px solid transparent; border-radius: {RADIUS['control']}px;"
        "padding: 0 16px; font-weight: 400;"
        "}"
        "QPushButton:hover {"
        f"color: {p.text_primary}; background-color: {p.surface_secondary};"
        "}"
    )
