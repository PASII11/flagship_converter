"""Токены темы: новые поля палитры и токены геометрии."""
from flagship_converter.ui import theme


def test_new_palette_fields_light_and_dark():
    for p in (theme.LIGHT, theme.DARK):
        for field in (
            "running", "running_soft", "success", "success_soft",
            "warning", "warning_soft", "error", "error_soft",
            "cat_image", "cat_audio", "cat_video", "cat_doc",
        ):
            value = getattr(p, field)
            assert isinstance(value, str) and value.startswith("#")


def test_light_palette_spec_values():
    p = theme.LIGHT
    assert p.app_bg == "#F6F7F9"
    assert p.accent == "#E50914"
    assert p.running == "#2E7CF6"
    assert p.cat_video == "#7C5CFC"


def test_dark_palette_spec_values():
    p = theme.DARK
    assert p.app_bg == "#101216"
    assert p.running == "#5B9BFF"
    assert p.cat_doc == "#2CC7B2"


def test_geometry_tokens():
    assert theme.SPACING == {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
    assert theme.RADIUS == {"panel": 12, "control": 8}


def test_new_qss_helpers_return_strings():
    p = theme.LIGHT
    assert "border-radius" in theme.chip_qss(p.running, p.running_soft)
    assert "QPushButton" in theme.nav_button_qss(True, p)
    assert "QPushButton" in theme.nav_button_qss(False, p)
