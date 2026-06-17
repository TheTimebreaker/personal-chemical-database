import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Literal

from database import Database


class AddMolecule(ttk.Frame):
    padx = 5
    pady = 5

    def __init__(
        self,
        master: ttk.Notebook | None = None,
        *,
        border: float | str | None = None,
        borderwidth: float | str | None = None,
        class_: Any = "",
        cursor: Any = "",
        height: int = 0,
        name: str | None = None,
        padding: (
            float
            | str
            | tuple[float | str]
            | tuple[float | str, float | str]
            | tuple[float | str, float | str, float | str]
            | tuple[float | str, float | str, float | str, float | str]
            | None
        ) = None,
        relief: Literal["raised", "sunken", "flat", "ridge", "solid", "groove"] | None = None,
        style: Any = "",
        takefocus: Any = "",
        width: int = 0,
        parent: GUI,
        root: tk.Tk,
    ) -> None:
        super().__init__(
            master,
            border=border,  # type: ignore
            borderwidth=borderwidth,  # type: ignore
            class_=class_,
            cursor=cursor,
            height=height,
            name=name,  # type: ignore
            padding=padding,  # type: ignore
            relief=relief,  # type: ignore
            style=style,
            takefocus=takefocus,
            width=width,
        )
        self.parent = parent
        self.root = root
        self._build_ui()

    def _build_ui(self) -> None:
        self.inchi_var = tk.StringVar()
        self.inchikey_var = tk.StringVar()
        self.smiles_var = tk.StringVar()
        self.cas_var = tk.StringVar()
        self.compound_names_var: list[str] = []

        self.inchi_label = ttk.Label(self, text="InChI")
        self.inchi_entry = ttk.Entry(self, textvariable=self.inchi_var)
        self.inchikey_label = ttk.Label(self, text="InChIKey")
        self.inchikey_entry = ttk.Entry(self, textvariable=self.inchikey_var)
        self.smiles_label = ttk.Label(self, text="SMILES")
        self.smiles_entry = ttk.Entry(self, textvariable=self.smiles_var)
        self.cas_label = ttk.Label(self, text="CAS")
        self.cas_entry = ttk.Entry(self, textvariable=self.cas_var)
        self.names_label = ttk.Label(self, text="Compound name(s)")

        self.inchi_label.grid(row=0, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.inchi_entry.grid(row=0, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.inchikey_label.grid(row=1, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.inchikey_entry.grid(row=1, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.smiles_label.grid(row=2, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.smiles_entry.grid(row=2, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.cas_label.grid(row=3, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.cas_entry.grid(row=3, column=1, sticky="ew", padx=self.padx, pady=self.pady)

        self.grid_columnconfigure(1, weight=1)


class Search(ttk.Frame):
    padx = 5
    pady = 5

    def __init__(
        self,
        master: ttk.Notebook | None = None,
        *,
        border: float | str | None = None,
        borderwidth: float | str | None = None,
        class_: Any = "",
        cursor: Any = "",
        height: int = 0,
        name: str | None = None,
        padding: (
            float
            | str
            | tuple[float | str]
            | tuple[float | str, float | str]
            | tuple[float | str, float | str, float | str]
            | tuple[float | str, float | str, float | str, float | str]
            | None
        ) = None,
        relief: Literal["raised", "sunken", "flat", "ridge", "solid", "groove"] | None = None,
        style: Any = "",
        takefocus: Any = "",
        width: int = 0,
        parent: GUI,
        root: tk.Tk,
    ) -> None:
        super().__init__(
            master,
            border=border,  # type: ignore
            borderwidth=borderwidth,  # type: ignore
            class_=class_,
            cursor=cursor,
            height=height,
            name=name,  # type: ignore
            padding=padding,  # type: ignore
            relief=relief,  # type: ignore
            style=style,
            takefocus=takefocus,
            width=width,
        )
        self.parent = parent
        self.root = root
        self._build_ui()

    def _build_ui(self) -> None: ...


class Browse(ttk.Frame):
    padx = 5
    pady = 5

    def __init__(
        self,
        master: ttk.Notebook | None = None,
        *,
        border: float | str | None = None,
        borderwidth: float | str | None = None,
        class_: Any = "",
        cursor: Any = "",
        height: int = 0,
        name: str | None = None,
        padding: (
            float
            | str
            | tuple[float | str]
            | tuple[float | str, float | str]
            | tuple[float | str, float | str, float | str]
            | tuple[float | str, float | str, float | str, float | str]
            | None
        ) = None,
        relief: Literal["raised", "sunken", "flat", "ridge", "solid", "groove"] | None = None,
        style: Any = "",
        takefocus: Any = "",
        width: int = 0,
        parent: GUI,
        root: tk.Tk,
    ) -> None:
        super().__init__(
            master,
            border=border,  # type: ignore
            borderwidth=borderwidth,  # type: ignore
            class_=class_,
            cursor=cursor,
            height=height,
            name=name,  # type: ignore
            padding=padding,  # type: ignore
            relief=relief,  # type: ignore
            style=style,
            takefocus=takefocus,
            width=width,
        )
        self.parent = parent
        self.root = root
        self._build_ui()

    def _build_ui(self) -> None:
        for molecule_uuid, molecule in self.parent.database.by_uuid.items():
            print(molecule_uuid, molecule)
        # TODO(TheTimebreaker): do this later when the database exists again lol


class GUI(tk.Tk):
    padx = 5
    pady = 5

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Personal Chemical Database")
        self.root.minsize(800, 0)

        self.database = Database()

        self._build_ui()

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.add_molecule = AddMolecule(self.notebook, parent=self, root=self.root)
        self.notebook.add(self.add_molecule, text="Add Molecule")
        self.browse_tab = Browse(self.notebook, parent=self, root=self.root)
        self.notebook.add(self.browse_tab, text="Browse")

        self.search_tab = Search(self.notebook, parent=self, root=self.root)
        self.notebook.add(self.search_tab, text="Search")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    g = GUI(root)
    tk.mainloop()
