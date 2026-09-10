import logging
import tkinter as tk

from gui import GUI
from style import configure_ttk_style, style_root


def main() -> None:
    root = tk.Tk()
    style_root(root)
    configure_ttk_style()
    GUI(root)
    tk.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
