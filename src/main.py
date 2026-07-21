import logging
import tkinter as tk

from gui import GUI
from style import configure_ttk_style


def main() -> None:
    root = tk.Tk()
    configure_ttk_style()
    _g = GUI(root)
    tk.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
