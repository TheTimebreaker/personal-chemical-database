import logging
import tkinter as tk

from gui import GUI


def main() -> None:
    root = tk.Tk()
    _g = GUI(root)
    tk.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
