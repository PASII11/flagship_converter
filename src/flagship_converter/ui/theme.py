"""Centralized frontend theme tokens and QSS helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class Palette:
    name: str
    is_dark: bool
    app_bg: str
    app_bg_to: str
    surface: str
    surface_secondary: str
    surface_elevated: str
    surface_glass: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    blue: str
    blue_soft: str
    green: str
    green_soft: str
    orange: str
    orange_soft: str
    error: str
    error_soft: str
    focus: str
    shadow: str
    scrollbar: str
    scrollbar_hover: str


LIGHT = Palette(
    name="Light",
    is_dark=False,
    app_bg="#F8FAFC",
    app_bg_to="#EEF1F6",
    surface="#FFFFFF",
    surface_secondary="#F8F9FC",
    surface_elevated="#FFFFFF",
    surface_glass="rgba(255, 255, 255, 0.92)",
    border="#E5E7EB",
    border_strong="#D1D5DB",
    text_primary="#111827",
    text_secondary="#6B7280",
    text_muted="#9CA3AF",
    accent="#E50914",
    accent_hover="#F0333D",
    accent_pressed="#B80710",
    accent_soft="#FDECEC",
    blue="#3B82F6",
    blue_soft="#EFF6FF",
    green="#22C55E",
    green_soft="#ECFDF3",
    orange="#F59E0B",
    orange_soft="#FFFBEB",
    error="#EF4444",
    error_soft="#FEF2F2",
    focus="#FDA4AF",
    shadow="#1F2937",
    scrollbar="#CBD5E1",
    scrollbar_hover="#94A3B8",
)

DARK = Palette(
    name="Dark",
    is_dark=True,
    app_bg="#0F1115",
    app_bg_to="#171A21",
    surface="#171A21",
    surface_secondary="#1F2430",
    surface_elevated="#232936",
    surface_glass="rgba(35, 41, 54, 0.90)",
    border="#343A46",
    border_strong="#475569",
    text_primary="#F9FAFB",
    text_secondary="#A1A1AA",
    text_muted="#71717A",
    accent="#E50914",
    accent_hover="#FF3341",
    accent_pressed="#B80710",
    accent_soft="#2A1216",
    blue="#60A5FA",
    blue_soft="#172033",
    green="#4ADE80",
    green_soft="#102418",
    orange="#FBBF24",
    orange_soft="#2B2110",
    error="#F87171",
    error_soft="#2A1216",
    focus="#FB7185",
    shadow="#000000",
    scrollbar="#475569",
    scrollbar_hover="#64748B",
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
    font-family: "Segoe UI Variable", "SF Pro Display", "Segoe UI";
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
    font-weight: 650;
    letter-spacing: 0px;
}}

QPushButton:focus, QComboBox:focus, QSpinBox:focus {{
    outline: none;
    border: 2px solid {p.focus};
}}

QStatusBar {{
    background-color: {p.app_bg};
    color: {p.text_secondary};
    border-top: 1px solid {p.border};
    padding-left: 8px;
}}

QToolTip {{
    background-color: {p.text_primary};
    color: {p.surface};
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
}}
"""


def root_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QWidget#Root {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {p.app_bg}, stop: 1 {p.app_bg_to}
    );
}}
"""


def panel_qss(object_name: str = "Panel", p: Palette | None = None, radius: int = 18) -> str:
    p = p or palette()
    return f"""
QFrame#{object_name} {{
    background-color: {p.surface_glass};
    border: 1px solid {p.border};
    border-radius: {radius}px;
}}
"""


def sidebar_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QFrame#Sidebar {{
    background-color: {p.surface_glass};
    border: 1px solid {p.border};
    border-radius: 20px;
}}
"""


def nav_item_qss(selected: bool, p: Palette | None = None) -> str:
    p = p or palette()
    if selected:
        return f"""
QPushButton {{
    background-color: {p.accent_soft};
    color: {p.accent};
    border: 1px solid {p.accent_soft};
    text-align: left;
    padding-left: 14px;
}}
QPushButton:hover {{
    background-color: {p.accent_soft};
    border-color: {p.accent};
}}
"""
    return f"""
QPushButton {{
    background-color: transparent;
    color: {p.text_secondary};
    border: 1px solid transparent;
    text-align: left;
    padding-left: 14px;
}}
QPushButton:hover {{
    background-color: {p.surface_secondary};
    color: {p.text_primary};
    border-color: {p.border};
}}
"""


def primary_button_qss(p: Palette | None = None) -> str:
    p = p or palette()
    return f"""
QPushButton {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {p.accent_hover}, stop: 1 {p.accent}
    );
    color: #FFFFFF;
    border: 1px solid {p.accent};
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
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
}}
QPushButton:hover {{
    background-color: {p.surface_secondary};
    border-color: {p.accent};
}}
QPushButton:pressed {{
    background-color: {p.accent_soft};
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
QComboBox, QSpinBox {{
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 26px;
}}

QComboBox:hover, QSpinBox:hover {{
    border-color: {p.accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
    selection-background-color: {p.accent};
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
    background-color: {p.surface_elevated};
}}
QCheckBox::indicator:hover {{
    border-color: {p.accent};
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


def status_pill_style(fg: str, bg: str, border: str | None = None) -> str:
    border_color = border or bg
    return (
        "QLabel {"
        f"color: {fg}; background-color: {bg}; border: 1px solid {border_color};"
        "border-radius: 12px; padding: 4px 10px; font-size: 12px; font-weight: 700;"
        "}"
    )


def category_badge_style(fg: str, bg: str, border: str) -> str:
    return (
        "QLabel {"
        f"color: {fg}; background-color: {bg}; border: 1px solid {border};"
        "border-radius: 11px; font-size: 12px; font-weight: 800;"
        "}"
    )


def progress_qss(color: str, p: Palette | None = None) -> str:
    p = p or palette()
    track = "#E8EEF6" if not p.is_dark else "#2C3442"
    return (
        "QProgressBar {"
        f"border: none; background-color: {track}; border-radius: 3px;"
        "}"
        f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
    )


def make_shadow(p: Palette | None = None, blur: int = 28, y: int = 10) -> QGraphicsDropShadowEffect:
    p = p or palette()
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y)
    color = QColor(p.shadow)
    color.setAlpha(34 if not p.is_dark else 70)
    shadow.setColor(color)
    return shadow
