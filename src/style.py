from typing import TYPE_CHECKING

from PySide6.QtGui import QFont, Qt
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from config import SettingsModel


def configure_app_style(app: QApplication, settings: SettingsModel) -> None:
    app.setFont(QFont("sans-serif"))

    theme = settings.theme
    if theme == "light":
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    elif theme == "dark":
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
