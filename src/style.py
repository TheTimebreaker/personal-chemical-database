from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def configure_app_style(app: QApplication) -> None:
    app.setFont(QFont("sans-serif"))
