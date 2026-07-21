from tkinter import ttk


def configure_ttk_style() -> None:
    style = ttk.Style()
    style.configure("Red.TLabel", foreground="red")
    style.configure("Green.TLabel", foreground="green")
