import argparse
import logging
import socket
import sys

from PySide6.QtWidgets import QApplication

from gui import GUI
from style import configure_app_style


def signal_ready(port: int) -> None:
    with socket.create_connection(("127.0.0.1", port)) as sock:
        print("READY!")
        sock.sendall(b"READY")


def main(ready_port: int | None = None) -> int:
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Personal Chemical Database")
    configure_app_style(app)
    window = GUI()
    window.show()
    app.processEvents()
    if ready_port is not None:
        signal_ready(ready_port)
    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-port", type=int)
    args = parser.parse_args()
    sys.exit(main(args.ready_port))
