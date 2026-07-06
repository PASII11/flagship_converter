"""i18n: flat RU->EN translation lookup and runtime language switching."""
from flagship_converter import i18n


def test_default_language_is_russian():
    assert i18n.current_language() == "ru"


def test_russian_returns_source_text_unchanged():
    i18n.set_language("ru")
    assert i18n.t("Настройки") == "Настройки"


def test_english_returns_translation():
    i18n.set_language("en")
    assert i18n.t("Настройки") == "Settings"


def test_unknown_key_falls_back_to_source_text():
    i18n.set_language("en")
    assert i18n.t("Нет такого текста в словаре") == "Нет такого текста в словаре"


def test_invalid_language_code_falls_back_to_russian():
    i18n.set_language("fr")
    assert i18n.current_language() == "ru"


def test_format_placeholders_survive_translation():
    i18n.set_language("en")
    assert i18n.t("Готово {done}").format(done=3) == "Done 3"
