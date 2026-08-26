from tkinter import ttk


def configure_ttk_style() -> None:
    style = ttk.Style()
    style.configure("Deleted.TLabel", foreground="red")
    style.configure("New.TLabel", foreground="green")
    style.configure("Edited.TLabel", foreground="blue")
