from PySide6.QtGui import QFont, Qt
from PySide6.QtWidgets import QApplication

from config import SettingsModel, Theme


def configure_app_style(app: QApplication, settings: SettingsModel) -> None:
    app.setFont(QFont("sans-serif"))

    theme = settings.theme
    hints = app.styleHints()
    if theme == Theme.LIGHT:
        hints.setColorScheme(Qt.ColorScheme.Light)
    elif theme == Theme.DARK:
        hints.setColorScheme(Qt.ColorScheme.Dark)
    elif theme == Theme.SYSTEM:
        hints.unsetColorScheme()
