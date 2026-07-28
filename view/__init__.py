import sys as _sys
from types import ModuleType as _ModuleType

_LAZY_SYMBOLS = {
    "ACCENT", "BG_COLOR", "CARD_COLOR", "DARK", "ERROR_COLOR",
    "FONT", "INPUT_BG", "INPUT_BORDER", "INPUT_BORDER_FOCUS",
    "PANEL_COLOR", "SUCCESS_COLOR", "TABLE_ROW_ALT", "TABLE_HOVER",
    "TEXT_MUTED", "TEXT_PRIMARY", "TEXT_SECONDARY", "WHITE",
    "draw_rounded_rect", "put_text", "text_size",
}


class _LazyModule(_ModuleType):
    def __getattr__(self, name):
        if name == "OpenCVRenderer":
            from view.renderer import OpenCVRenderer
            return OpenCVRenderer
        if name in _LAZY_SYMBOLS:
            import view.draw
            return getattr(view.draw, name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_sys.modules[__name__].__class__ = _LazyModule
