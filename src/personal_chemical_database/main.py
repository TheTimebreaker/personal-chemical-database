import socket
import sys

from PySide6.QtWidgets import QApplication

from .config import read_config
from .gui import GUI
from .style import configure_app_style


def signal_ready(port: int) -> None:
    with socket.create_connection(("127.0.0.1", port)) as sock:
        print("READY!")
        sock.sendall(b"READY")


def main(ready_port: int | None = None, use_default_config: bool = False) -> int:
    settings = read_config(use_default_config)

    app: QApplication = QApplication.instance() or QApplication([sys.argv[0]])  # type: ignore
    app.setApplicationName("Personal Chemical Database")
    configure_app_style(app, settings)
    window = GUI(app, settings=settings)
    window.show()
    app.processEvents()
    if ready_port is not None:
        signal_ready(ready_port)
    return app.exec()
