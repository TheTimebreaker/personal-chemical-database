import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


def style_root(root: tk.Tk) -> None:
    sans_fonts = (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    )

    for font_name in sans_fonts:
        try:
            tkfont.nametofont(font_name).configure(family="sans-serif")
        except tk.TclError:
            pass

    try:
        tkfont.nametofont("TkFixedFont").configure(family="monospace")
    except tk.TclError:
        pass


def configure_ttk_style() -> None:
    style = ttk.Style()
    style.configure("Deleted.TLabel", foreground="red")
    style.configure("New.TLabel", foreground="green")
    style.configure("Edited.TLabel", foreground="blue")
