from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent


def load_template(template_name: str) -> str:
    template_path = TEMPLATES_DIR / template_name
    with open(template_path, "r", encoding="utf-8") as file:
        return file.read()


def load_styles() -> str:
    styles_path = TEMPLATES_DIR / "styles.css"
    with open(styles_path, "r", encoding="utf-8") as file:
        return file.read()


STYLES_CSS = load_styles()

__all__ = [
    "load_template",
]
