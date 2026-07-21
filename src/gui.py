import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Literal

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
from database import Database, Molecule, MoleculeData, generate_molecule_data, get_display_name


class AddMolecule(ttk.Frame):
    padx = 5
    pady = 5

    edit_state: Literal["normal", "readonly"] = "normal"
    viewer_mode: bool = False

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
        self.previous_tab = None

        self.inchi_var = tk.StringVar()
        self.inchikey_var = tk.StringVar()
        self.smiles_var = tk.StringVar()
        self.cas_var = tk.StringVar()
        self.molecule_uuid_var: str | None = None
        self.compound_names_var: list[str] = []
        self._new_compound_names: list[str] = []
        self._deleted_compound_names: list[str] = []  # unused in here, but used in descendants
        self.data_var: dict[str, MoleculeData] = {}
        self._new_data: list[str] = []
        self._deleted_data: list[str] = []  # unused in here, but used in descendants

        self._build_ui()

    def _build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        self.inchi_label = ttk.Label(self, text="InChI")
        self.inchi_entry = ttk.Entry(self, textvariable=self.inchi_var, state=self.edit_state)
        self.inchikey_label = ttk.Label(self, text="InChIKey")
        self.inchikey_entry = ttk.Entry(self, textvariable=self.inchikey_var, state=self.edit_state)
        self.smiles_label = ttk.Label(self, text="SMILES")
        self.smiles_entry = ttk.Entry(self, textvariable=self.smiles_var, state=self.edit_state)
        self.cas_label = ttk.Label(self, text="CAS")
        self.cas_entry = ttk.Entry(self, textvariable=self.cas_var, state=self.edit_state)
        self.names_label = ttk.Label(self, text="Compound name(s)")
        self.names_entry = ttk.Frame(self)
        self.data_label = ttk.Label(self, text="Additional data")
        self.data_entry = ttk.Frame(self)

        self.inchi_label.grid(row=0, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.inchi_entry.grid(row=0, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.inchikey_label.grid(row=1, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.inchikey_entry.grid(row=1, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.smiles_label.grid(row=2, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.smiles_entry.grid(row=2, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.cas_label.grid(row=3, column=0, sticky="w", padx=self.padx, pady=self.pady)
        self.cas_entry.grid(row=3, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        self.names_label.grid(row=4, column=0, sticky="nw", padx=self.padx, pady=self.pady)
        self.names_entry.grid(row=4, column=1, sticky="ew")
        self.data_label.grid(row=5, column=0, sticky="nw", padx=self.padx, pady=self.pady)
        self.data_entry.grid(row=5, column=1, sticky="ew")

        self.grid_columnconfigure(1, weight=1)

        self._update_compound_names()
        self._update_data()

        # --- OK buttons

        separator = ttk.Separator(self, orient="horizontal")
        separator.grid(row=6, column=0, columnspan=2, sticky="ew", padx=self.padx, pady=self.pady)

        action_frame = ttk.Frame(self)
        action_frame.grid(row=7, column=0, columnspan=2, sticky="e", padx=self.padx, pady=self.pady)

        self.autofill_button = ttk.Button(action_frame, text="Autofill", command=self._autofill)
        self.confirm_button = ttk.Button(action_frame, text="Confirm", command=self._confirm)
        self.clear_button = ttk.Button(action_frame, text="Clear", command=self._clear)

        self.autofill_button.pack(side="left", padx=self.padx, pady=self.pady)
        self.clear_button.pack(side="right", padx=self.padx, pady=self.pady)
        self.confirm_button.pack(side="right", padx=self.padx, pady=self.pady)

    def _update_ui_from_database(self, molecule_uuid: str) -> None:
        logging.info("EDITING molecule_uuid=%s", molecule_uuid)
        molecule = self.parent.database.by_uuid[molecule_uuid]
        self._clear()  # Clear potential leftovers, so we dont get crossovers

        self.inchi_var.set(molecule["inchi"])
        self.inchikey_var.set(molecule["inchikey"])
        self.smiles_var.set(molecule["smiles"])
        if molecule.get("cas", None):
            self.cas_var.set(molecule.get("cas", None))
        if molecule.get("names", None):
            self.compound_names_var = molecule["names"]
        mol_data_uuids = self.parent.database.get_data_uuids(molecule_uuid)
        logging.info("data uuids found: mol_data_uuids=%s", mol_data_uuids)
        if mol_data_uuids:
            for data_uuid in mol_data_uuids:
                self.data_var[data_uuid] = self.parent.database.read_data(molecule_uuid, data_uuid)
        self.molecule_uuid_var = molecule_uuid
        self._build_ui()

    def _update_compound_names(self) -> None:
        for child in self.names_entry.winfo_children():
            child.destroy()

        frame = ttk.Frame(self.names_entry)
        frame.pack(fill="x", expand=True)
        frame.columnconfigure(0, weight=1)
        for i, name in enumerate(self.compound_names_var):
            marked_for_deletion = name in self._deleted_compound_names
            marked_as_new = name in self._new_compound_names
            if marked_for_deletion:
                styl = "Red.TLabel"
            elif marked_as_new:
                styl = "Green.TLabel"
            else:
                styl = ""

            ttk.Label(frame, text=name, style=styl).grid(row=i, column=0, sticky="ew", padx=self.padx, pady=self.pady)

            if not self.viewer_mode:
                if marked_for_deletion:
                    ttk.Button(
                        frame,
                        text="Undo",
                        command=lambda name=name: self._remove_this_name_undo(name),
                    ).grid(row=i, column=1, padx=self.padx, pady=0)
                else:
                    ttk.Button(
                        frame,
                        text="Delete",
                        command=lambda name=name: self._remove_this_name(name),
                    ).grid(row=i, column=1, padx=self.padx, pady=0)

        if not self.viewer_mode:
            button_add_names = ttk.Button(self.names_entry, text="Add name", command=self._open_add_name_dialog)
            button_add_names.pack(fill="x", expand=True, padx=self.padx, pady=self.pady)

    def _update_data(self) -> None:
        for child in self.data_entry.winfo_children():
            child.destroy()

        frame = ttk.Frame(self.data_entry)
        frame.pack(fill="x", expand=True)
        frame.columnconfigure(0, weight=1)
        for i, (data_uuid, data) in enumerate(self.data_var.items()):
            marked_for_deletion = data_uuid in self._deleted_data
            marked_as_new = data_uuid in self._new_data
            if marked_for_deletion:
                styl = "Red.TLabel"
            elif marked_as_new:
                styl = "Green.TLabel"
            else:
                styl = ""

            lab = ttk.Label(frame, text=f"#{data_uuid}-{data["data_type"]}", style=styl)
            lab.bind("<Button-1>", lambda _event, data=data: self._open_view_data_dialog(data=data))
            lab.grid(row=i, column=0, sticky="ew", padx=self.padx, pady=self.pady)
            if not self.viewer_mode:
                if marked_for_deletion:
                    ttk.Button(
                        frame,
                        text="Undo",
                        command=lambda data_uuid=data_uuid: self._remove_this_data_undo(data_uuid),
                    ).grid(row=i, column=1, padx=self.padx, pady=0)
                else:
                    ttk.Button(
                        frame,
                        text="Delete",
                        command=lambda data_uuid=data_uuid: self._remove_this_data(data_uuid),
                    ).grid(row=i, column=1, padx=self.padx, pady=0)

        if not self.viewer_mode:
            button_add_data = ttk.Button(self.data_entry, text="Add data", command=self._open_add_data_dialog)
            button_add_data.pack(fill="x", expand=True, padx=self.padx, pady=self.pady)

    def _open_add_name_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Add compound name")
        dialog.transient(self.root)
        dialog.grab_set()

        entry_var = tk.StringVar()
        label = ttk.Label(dialog, text="Compound name:")
        entry = ttk.Entry(dialog, textvariable=entry_var)
        button_frame = ttk.Frame(dialog)
        button_confirm = ttk.Button(button_frame, text="Confirm", command=lambda: self._confirm_add_name(dialog, entry_var))
        button_cancel = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)

        label.grid(row=0, column=0, sticky="w", padx=self.padx, pady=self.pady)
        entry.grid(row=0, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="e", padx=self.padx, pady=self.pady)
        button_cancel.pack(side="right", padx=self.padx, pady=self.pady)
        button_confirm.pack(side="right", padx=self.padx, pady=self.pady)

        dialog.grid_columnconfigure(1, weight=1)
        entry.focus_set()
        dialog.bind("<Return>", lambda _: self._confirm_add_name(dialog, entry_var))

    def _open_add_data_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Add a data entry")
        dialog.transient(self.root)
        dialog.grab_set()

        type_var = tk.StringVar()
        data_var = tk.StringVar()
        source_var = tk.StringVar()

        label1 = ttk.Label(dialog, text="Data type:")
        entry1 = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=["1H NMR", "13C NMR", "19F NMR", "31P NMR", "IR", "Mass", "boiling point", "melting point", "color"],
            state="readonly",
        )

        label2 = ttk.Label(dialog, text="Data:")
        entry2 = ttk.Entry(dialog, textvariable=data_var)

        label3 = ttk.Label(dialog, text="Source:")
        entry3 = ttk.Entry(dialog, textvariable=source_var)

        button_frame = ttk.Frame(dialog)
        button_confirm = ttk.Button(button_frame, text="Confirm", command=lambda: self._confirm_add_data(dialog, type_var, data_var, source_var))
        button_cancel = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)

        label1.grid(row=0, column=0, sticky="w", padx=self.padx, pady=self.pady)
        entry1.grid(row=0, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        label2.grid(row=1, column=0, sticky="w", padx=self.padx, pady=self.pady)
        entry2.grid(row=1, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        label3.grid(row=2, column=0, sticky="w", padx=self.padx, pady=self.pady)
        entry3.grid(row=2, column=1, sticky="ew", padx=self.padx, pady=self.pady)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=self.padx, pady=self.pady)
        button_cancel.pack(side="right", padx=self.padx, pady=self.pady)
        button_confirm.pack(side="right", padx=self.padx, pady=self.pady)

        dialog.grid_columnconfigure(1, weight=1)
        dialog.bind("<Return>", lambda _: self._confirm_add_data(dialog, type_var, data_var, source_var))

    def _open_view_data_dialog(
        self,
        *,
        molecule_uuid: str | None = None,
        data_uuid: str | None = None,
        data: MoleculeData | None = None,
    ) -> None:
        if data is None:
            if not molecule_uuid or not data_uuid:
                raise ValueError("Either data or both molecule_uuid and data_uuid must be provided.")
            data = self.parent.database.read_data(molecule_uuid, data_uuid)
        logging.info(data)

        dialog = tk.Toplevel(self.root)
        dialog.title("Data details")
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()
        dialog.resizable(False, False)

        fields = [
            ("Type", data.get("data_type", "")),
            ("Data", data.get("data", "")),
            ("Source", data.get("source", "")),
        ]
        self.anti_garbagecollector = []  # this is necessary to prevent the ENTRYs from being brutally murdered by python
        for row, (label_text, val) in enumerate(fields):
            ttk.Label(dialog, text=f"{label_text}:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
            el = ttk.Entry(dialog)
            el.insert(0, str(val))
            el.configure(state="readonly")
            el.grid(row=row, column=2, sticky="ew", padx=5, pady=5)
            self.anti_garbagecollector.append(el)

        dialog.columnconfigure(1, weight=1)
        dialog.minsize(320, 0)

    def _remove_this_name(self, name: str) -> None:
        self._deleted_compound_names.append(name)
        self._update_compound_names()

    def _remove_this_name_undo(self, name: str) -> None:
        try:
            self._deleted_compound_names.remove(name)
        except ValueError:
            messagebox.showerror(
                title="How did we get here?",
                message="I do not understand how this is possible, but the compound name you are trying to UNDO isn't marked for deletion anymore.",
            )
        self._update_compound_names()

    def _remove_this_data(self, data_uuid: str) -> None:
        self._deleted_data.append(data_uuid)
        self._update_data()

    def _remove_this_data_undo(self, data_uuid: str) -> None:
        try:
            self._deleted_data.remove(data_uuid)

        except ValueError:
            messagebox.showerror(
                title="How did we get here?",
                message="I do not understand how this is possible, but the data UUID you are trying to UNDO isn't marked for deletion anymore.",
            )
        self._update_data()

    def _confirm_add_name(self, dialog: tk.Toplevel, entry_var: tk.StringVar) -> None:
        value = entry_var.get().strip()
        if value:
            self.compound_names_var.append(value)
            self._new_compound_names.append(value)
            self._update_compound_names()
            dialog.destroy()
        else:
            messagebox.showerror(
                title="Invalid entry", message="The field was detected as being empty, which is disallowed (and would not make any sense)."
            )

    def _confirm_add_data(self, dialog: tk.Toplevel, type_var: tk.StringVar, data_var: tk.StringVar, source_var: tk.StringVar) -> None:
        type_value = type_var.get().strip()
        data_value = data_var.get().strip()
        source_value = source_var.get().strip()
        if type_value and data_value and source_value:
            new_data_uuid = self.parent.database._gen_uuid()
            self.data_var[new_data_uuid] = MoleculeData(data_type=type_value, data=data_value, source=source_value)
            self._new_data.append(new_data_uuid)
            self._update_data()
            dialog.destroy()
        else:
            messagebox.showerror(title="Invalid entry", message="Some values were detected as being empty, which is disallowed.")

    def _autofill(self) -> None:
        inchi = self.inchi_var.get()
        if not inchi:
            inchi = None
        inchikey = self.inchikey_var.get()
        if not inchikey:
            inchikey = None
        smiles = self.smiles_var.get()
        if not smiles:
            smiles = None
        cas = self.cas_var.get()
        if not cas:
            cas = None
        names = self.compound_names_var
        if not names:
            names = None
        else:
            names = names[0]

        try:
            molecule = generate_molecule_data(inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, compound_name=names)
        except ValueError:
            messagebox.showerror(
                title="Autofill not successfull",
                message="Autofilling was not successfull from the entered values. Make sure to give atleast one of the above values and if you did "
                "and it still failed, enter a value for another field.",
            )
            return

        if molecule:
            if molecule["inchi"]:
                self.inchi_var.set(molecule["inchi"])
            if molecule["inchikey"]:
                self.inchikey_var.set(molecule["inchikey"])
            if molecule["smiles"]:
                self.smiles_var.set(molecule["smiles"])
            if molecule["cas"]:
                self.cas_var.set(molecule["cas"])
            if molecule["names"]:
                self.compound_names_var = molecule["names"]

    def _confirm(self) -> None:
        inchi = self.inchi_var.get()
        inchikey = self.inchikey_var.get()
        smiles = self.smiles_var.get()
        cas = self.cas_var.get()
        if not cas:
            cas = None
        names = self.compound_names_var
        if not names:
            names = None
        names = [x for x in self.compound_names_var if x not in self._deleted_compound_names]
        if any(not x for x in (inchi, inchikey, smiles)):
            return
        molecule = Molecule(inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, names=names)

        if self.parent.database.is_this_in_db(molecule=molecule):
            messagebox.showerror(title="Adding molecule not successfull", message="This molecule is a duplicate and already exists in the database.")
            return

        if self.parent.database.create_entry(molecule):
            self.parent.database.__init__()

            molecule_uuid = self.parent.database.by_inchi[inchi]
            existing_data_uuids = self.parent.database.get_data_uuids(molecule_uuid)
            for data_uuid, data in self.data_var.items():
                molecule_has_no_data = existing_data_uuids is None
                data_exists = data_uuid in existing_data_uuids
                data_was_deleted = data_uuid in self._deleted_data
                if data_was_deleted:
                    self.parent.database.delete_data(molecule_uuid=molecule_uuid, data_uuid=data_uuid)
                elif molecule_has_no_data or not data_exists:
                    self.parent.database.add_data(molecule_uuid, data=data, data_uuid=data_uuid)

            self._clear()

            self.parent.browse_tab._build_ui()
            self._build_ui()
        else:
            messagebox.showerror(
                title="Adding molecule not successfull", message="The molecule could not be added successfully for an unknown reason."
            )

    def _clear(self) -> None:
        self.inchi_var = tk.StringVar()
        self.inchikey_var = tk.StringVar()
        self.smiles_var = tk.StringVar()
        self.cas_var = tk.StringVar()
        self.compound_names_var = []
        self._new_compound_names = []
        self._deleted_compound_names = []
        self.data_var = {}
        self._new_data = []
        self._deleted_data = []

        self._build_ui()
        if self.previous_tab is not None:
            self.parent.notebook.select(self.previous_tab)


class EditMolecule(AddMolecule):
    def _build_ui(self) -> None:
        super()._build_ui()
        self.autofill_button.pack_forget()
        self.clear_button.configure(text="Cancel")

    def _confirm(self) -> None:
        inchi = self.inchi_var.get()
        inchikey = self.inchikey_var.get()
        smiles = self.smiles_var.get()
        cas = self.cas_var.get()
        if not cas:
            cas = None
        names = self.compound_names_var
        if not names:
            names = None
        names = [x for x in self.compound_names_var if x not in self._deleted_compound_names]

        molecule_uuid = self.molecule_uuid_var
        if not molecule_uuid:
            logging.error("Could not commit EDITs, molecule UUID was not assigned.")
            return  # ERROR

        if any(not x for x in (inchi, inchikey, smiles)):
            logging.error("Could not commit EDITs, atleast one required value was empty.")
            return
        molecule = Molecule(inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, names=names)

        if self.parent.database.overwrite_entry(molecule_uuid=molecule_uuid, molecule=molecule):
            self.parent.database.__init__()

            existing_data_uuids = self.parent.database.get_data_uuids(molecule_uuid)
            for data_uuid, data in self.data_var.items():
                molecule_has_no_data = existing_data_uuids is None
                data_exists = data_uuid in existing_data_uuids
                data_was_deleted = data_uuid in self._deleted_data
                print(data_uuid, self._deleted_data, data_was_deleted)
                if data_was_deleted:
                    self.parent.database.delete_data(molecule_uuid=molecule_uuid, data_uuid=data_uuid)
                elif molecule_has_no_data or not data_exists:
                    logging.info("committing new data for molecule %s datauuid %s to database: %s", molecule_uuid, data_uuid, data)
                    self.parent.database.add_data(molecule_uuid, data=data, data_uuid=data_uuid)

            self._clear()
            self.parent.browse_tab._build_ui()
        else:
            messagebox.showerror(
                title="Adding molecule not successfull", message="The molecule could not be added successfully for an unknown reason."
            )

    def _clear(self) -> None:
        super()._clear()
        self.parent._toggle_edit_off()


class View(AddMolecule):
    edit_state = "readonly"
    viewer_mode = True

    def _build_ui(self) -> None:
        super()._build_ui()
        self.autofill_button.pack_forget()
        self.confirm_button.pack_forget()
        self.clear_button.configure(text="Exit Viewer")

    def _clear(self) -> None:
        super()._clear()
        self.parent._toggle_view_off()


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
        self.columnconfigure(0, weight=1)
        for child in self.winfo_children():
            child.destroy()

        for i, (molecule_uuid, molecule) in enumerate(self.parent.database.by_uuid.items()):
            print(molecule_uuid, molecule)
            ttk.Label(self, text=get_display_name(molecule)).grid(row=i, column=0, padx=self.padx, pady=self.pady, sticky="ew")
            ttk.Button(
                self,
                text="View",
                command=lambda molecule_uuid=molecule_uuid: self._view(molecule_uuid),
            ).grid(row=i, column=1, padx=self.padx, pady=self.pady)
            ttk.Button(
                self,
                text="Edit",
                command=lambda molecule_uuid=molecule_uuid: self._edit(molecule_uuid),
            ).grid(row=i, column=2, padx=self.padx, pady=self.pady)
            ttk.Button(
                self,
                text="Delete",
                command=lambda molecule_uuid=molecule_uuid: self._delete(molecule_uuid),
            ).grid(row=i, column=3, padx=self.padx, pady=self.pady)

    def _view(self, molecule_uuid: str) -> None:
        self.parent.view_tab.previous_tab = self.parent.browse_tab
        self.parent.view_tab._update_ui_from_database(molecule_uuid)
        self.parent._toggle_view_on()
        self.parent.notebook.select(self.parent.view_tab)

    def _edit(self, molecule_uuid: str) -> None:
        self.parent.edit_molecule.previous_tab = self.parent.browse_tab
        self.parent.edit_molecule._update_ui_from_database(molecule_uuid)
        self.parent._toggle_edit_on()
        self.parent.notebook.select(self.parent.edit_molecule)

    def _delete(self, molecule_uuid: str) -> None:
        print(molecule_uuid)
        if not self.parent.database.is_this_in_db(uuid=molecule_uuid):
            messagebox.showerror(
                title="Can't delete what doesn't exist",
                message=f"Cannot delete selected molecule {molecule_uuid} because it isn't in the database.",
            )
            return

        if not messagebox.askyesno(
            title="Are you sure?",
            message=f"Are you sure you want to delete this molecule:\n - {molecule_uuid}\n - {self.parent.database.by_uuid[molecule_uuid]}",
        ):
            return

        if not self.parent.database.delete_entry(uuid=molecule_uuid):
            messagebox.showerror(
                title="Deletion unsuccessful",
                message=f"Could not delete molecule {molecule_uuid} due to an unknown error.",
            )
        self.parent.database.__init__()
        self._build_ui()


class GUI(tk.Tk):
    padx = 5
    pady = 5

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Personal Chemical Database")
        self.root.minsize(800, 0)

        self.database = Database()

        self.notebook = ttk.Notebook(self.root)
        self.add_molecule = AddMolecule(self.notebook, parent=self, root=self.root)
        self.edit_molecule = EditMolecule(self.notebook, parent=self, root=self.root)
        self.browse_tab = Browse(self.notebook, parent=self, root=self.root)
        self.search_tab = Search(self.notebook, parent=self, root=self.root)
        self.view_tab = View(self.notebook, parent=self, root=self.root)

        self._build_ui()

    def _build_ui(self) -> None:
        self.notebook.pack(fill="both", expand=True)
        self.notebook.add(self.add_molecule, text="Add Molecule")
        self.notebook.add(self.browse_tab, text="Browse")
        self.notebook.add(self.search_tab, text="Search")

    def _toggle_edit_on(self) -> None:
        self.notebook.add(self.edit_molecule, text="Edit Molecule")

    def _toggle_edit_off(self) -> None:
        try:
            self.notebook.hide(self.edit_molecule)
        except tk.TclError:
            pass

    def _toggle_view_on(self) -> None:
        self.notebook.add(self.view_tab, text="View Molecule")

    def _toggle_view_off(self) -> None:
        try:
            self.notebook.hide(self.view_tab)
        except tk.TclError:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    style = ttk.Style()
    style.configure("Red.TLabel", foreground="red")
    style.configure("Green.TLabel", foreground="green")
    g = GUI(root)
    tk.mainloop()
