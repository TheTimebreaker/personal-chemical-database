import argparse
import logging
import socket
import tkinter as tk

from gui import GUI
from style import configure_ttk_style, style_root


def signal_ready(port: int) -> None:
    with socket.create_connection(("127.0.0.1", port)) as sock:
        print("READY!")
        sock.sendall(b"READY")


def main() -> None:
    root = tk.Tk()
    style_root(root)
    configure_ttk_style()
    GUI(root)
    tk.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-port", type=int)
    args = parser.parse_args()
    if args.ready_port is not None:
        signal_ready(args.ready_port)

    main()
