import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Literal

from PIL import ImageTk
from rdkit import Chem
from rdkit.Chem import Draw

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
from database import Database, Molecule, MoleculeData, NMRData, generate_molecule_data, get_display_name
from style import configure_ttk_style


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
        self.previous_tab: Browse | AddMolecule | EditMolecule | View | None = None

        self.inchi_var = tk.StringVar()
        self.inchikey_var = tk.StringVar()
        self.smiles_var = tk.StringVar()
        self.cas_var = tk.StringVar()
        self.molecule_uuid_var: str | None = None
        self.compound_names_var: list[str] = []
        self._new_compound_names: list[str] = []
        self._deleted_compound_names: list[str] = []  # unused in here, but used in descendants
        self.data_var: dict[str, MoleculeData | NMRData] = {}
        self._new_data: list[str] = []
        self._updated_data: list[str] = []
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

        if self.viewer_mode is True:
            molecule = Chem.MolFromSmiles(self.smiles_var.get())
            draw = Draw.MolToImage(molecule, size=(150, 150), backgroundColor="red")
            drawtk = ImageTk.PhotoImage(draw)
            xlabel = tk.Label(self, image=drawtk, relief="solid", borderwidth=2)
            xlabel.bind("<Button-1>", lambda _: self._popup_lewis())
            xlabel.image = drawtk  # type: ignore
            xlabel.grid(row=0, column=2, rowspan=6, padx=self.padx, pady=self.pady, sticky="n")

        # --- OK buttons

        separator = ttk.Separator(self, orient="horizontal")
        separator.grid(row=6, column=0, columnspan=3, sticky="ew", padx=self.padx, pady=self.pady)

        action_frame = ttk.Frame(self)
        action_frame.grid(row=7, column=0, columnspan=3, sticky="e", padx=self.padx, pady=self.pady)

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
            self.cas_var.set(molecule.get("cas"))  # type: ignore
        if molecule.get("names", None):
            self.compound_names_var = molecule.get("names")  # type: ignore
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
                        command=lambda name=name: self._remove_this_name_undo(name),  # type: ignore
                    ).grid(row=i, column=1, padx=self.padx, pady=0)
                else:
                    ttk.Button(
                        frame,
                        text="Delete",
                        command=lambda name=name: self._remove_this_name(name),  # type: ignore
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
            marked_as_edited = data_uuid in self._updated_data
            if marked_for_deletion:
                styl = "Deleted.TLabel"
            elif marked_as_new:
                styl = "New.TLabel"
            elif marked_as_edited:
                styl = "Edited.TLabel"
            else:
                styl = ""

            lab = ttk.Label(frame, text=f"#{data_uuid}-{data["data_type"]}", style=styl)
            lab.bind("<Button-1>", lambda _event, data_uuid=data_uuid, data=data: self.open_data_dialog(data=data, data_uuid=data_uuid))  # type: ignore
            lab.grid(row=i, column=0, sticky="ew", padx=self.padx, pady=self.pady)
            if not self.viewer_mode:
                if marked_for_deletion:
                    ttk.Button(
                        frame,
                        text="Undo",
                        command=lambda data_uuid=data_uuid: self._remove_this_data_undo(data_uuid),  # type: ignore
                    ).grid(row=i, column=1, padx=self.padx, pady=0)
                else:
                    ttk.Button(
                        frame,
                        text="Delete",
                        command=lambda data_uuid=data_uuid: self._remove_this_data(data_uuid),  # type: ignore
                    ).grid(row=i, column=1, padx=self.padx, pady=0)

        if not self.viewer_mode:
            button_add_data = ttk.Button(self.data_entry, text="Add data", command=self.open_data_dialog)
            button_add_data.pack(fill="x", expand=True, padx=self.padx, pady=self.pady)

    def _popup_lewis(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.update_idletasks()
        dialog.title("LEWIS structure")
        dialog.transient(self.root)
        dialog.grab_set()

        smiles = self.smiles_var.get()
        if not smiles:
            return

        molecule = Chem.MolFromSmiles(smiles)
        draw = Draw.MolToImage(molecule)
        drawtk = ImageTk.PhotoImage(draw)
        xlabel = tk.Label(dialog, image=drawtk)
        xlabel.image = drawtk  # type: ignore
        xlabel.pack()

        dialog.bind("<Return>", lambda _event: dialog.destroy())

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

    def open_data_dialog(
        self,
        *,
        molecule_uuid: str | None = None,
        data_uuid: str | None = None,
        data: MoleculeData | NMRData | None = None,
    ) -> None:
        def _build_ui() -> None:
            for child in dialog.winfo_children():
                child.destroy()

            dialog.entries = []
            for row, label_text in enumerate(fields.keys()):
                if label_text in ("Solvent", "Frequency") and "NMR" not in fields["Type"].get():
                    continue
                ttk.Label(dialog, text=f"{label_text}:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
                if label_text in ("Type",):
                    el = ttk.Combobox(
                        dialog,
                        textvariable=fields[label_text],
                        values=["1H NMR", "13C NMR", "19F NMR", "31P NMR", "IR", "Mass", "boiling point", "melting point", "color"],
                        state="readonly",
                    )
                    el.bind("<<ComboboxSelected>>", lambda _: _build_ui())
                else:
                    el = ttk.Entry(dialog, textvariable=fields[label_text])
                el.configure(state=self.edit_state)
                el.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
                dialog.entries.append(el)

            if self.viewer_mode is False:
                button_frame = ttk.Frame(dialog)
                button_confirm = ttk.Button(button_frame, text="Confirm", command=lambda: self._confirm_add_data(dialog, fields, data_uuid))
                button_cancel = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
                button_frame.grid(row=row + 1, column=0, columnspan=2, sticky="e", padx=self.padx, pady=self.pady)
                button_cancel.pack(side="right", padx=self.padx, pady=self.pady)
                button_confirm.pack(side="right", padx=self.padx, pady=self.pady)

        if data is None:
            if molecule_uuid and data_uuid:
                data = self.parent.database.read_data(molecule_uuid, data_uuid)
            else:
                data = {}  # type: ignore
        logging.info(data)
        if data is None:
            raise ValueError

        dialog = tk.Toplevel(self.root)
        dialog.title("Data details")
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()
        dialog.resizable(True, False)

        fields: dict[Literal["Type", "Solvent", "Frequency", "Data", "Source"], tk.StringVar] = {
            "Type": tk.StringVar(value=str(data.get("data_type", ""))),
            "Solvent": tk.StringVar(value=str(data.get("solvent", ""))),
            "Frequency": tk.StringVar(value=str(data.get("frequency", ""))),
            "Data": tk.StringVar(value=str(data.get("data", ""))),
            "Source": tk.StringVar(value=str(data.get("source", ""))),
        }

        dialog.fields = fields  # type: ignore
        _build_ui()

        dialog.bind("<Return>", lambda _: self._confirm_add_data(dialog, fields, data_uuid))
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

    def _confirm_add_data(
        self, dialog: tk.Toplevel, fields: dict[Literal["Type", "Solvent", "Frequency", "Data", "Source"], tk.StringVar], data_uuid: str | None = None
    ) -> None:
        # get all the variables
        type_value = fields["Type"].get().strip()
        solvent_value = fields["Solvent"].get().strip()
        frequency_value = fields["Frequency"].get().strip()
        data_value = fields["Data"].get().strip()
        source_value = fields["Source"].get().strip()

        # Data UUID
        if data_uuid is None:
            data_uuid = self.parent.database._gen_uuid()

        if "NMR" in type_value:
            data_obj = NMRData(data_type=type_value, data=data_value, source=source_value, solvent=solvent_value, frequency=frequency_value)  # type: ignore
        else:
            data_obj = MoleculeData(data_type=type_value, data=data_value, source=source_value)  # type: ignore

        if type_value and data_value and source_value:
            if data_uuid not in self.data_var:
                self._new_data.append(data_uuid)
            else:
                self._updated_data.append(data_uuid)

            self.data_var[data_uuid] = data_obj
            self._update_data()
            dialog.destroy()
        else:
            messagebox.showerror(title="Invalid entry", message="Some values were detected as being empty, which is disallowed.")

    def _autofill(self) -> None:
        inchi: str | None = self.inchi_var.get()
        if not inchi:
            inchi = None
        inchikey: str | None = self.inchikey_var.get()
        if not inchikey:
            inchikey = None
        smiles: str | None = self.smiles_var.get()
        if not smiles:
            smiles = None
        cas: str | None = self.cas_var.get()
        if not cas:
            cas = None
        names: list[str] | None = self.compound_names_var
        name: str | None
        if not names:
            name = None
        else:
            name = names[0]

        try:
            molecule = generate_molecule_data(inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, compound_name=name)
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
        cas: str | None = self.cas_var.get()
        if not cas:
            cas = None
        names: list[str] | None = self.compound_names_var
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
            self.parent.database.__init__()  # type: ignore

            molecule_uuid = self.parent.database.by_inchi[inchi]
            existing_data_uuids = self.parent.database.get_data_uuids(molecule_uuid)
            for data_uuid, data in self.data_var.items():
                molecule_has_data = bool(existing_data_uuids)
                data_exists = data_uuid in existing_data_uuids
                data_updated = data_uuid in self._updated_data
                data_was_deleted = data_uuid in self._deleted_data
                if data_was_deleted:
                    self.parent.database.delete_data(molecule_uuid=molecule_uuid, data_uuid=data_uuid)
                elif not molecule_has_data or not data_exists:
                    self.parent.database.add_data(molecule_uuid, data=data, data_uuid=data_uuid)
                elif data_updated:
                    self.parent.database.modify_data(molecule_uuid, data=data, data_uuid=data_uuid)

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
        self._updated_data = []
        self._deleted_data = []

        self._build_ui()
        if self.previous_tab is not None:
            self.parent.notebook.select(self.previous_tab)


class EditMolecule(AddMolecule):
    edit_state = "normal"

    def _build_ui(self) -> None:
        super()._build_ui()
        self.autofill_button.pack_forget()
        self.clear_button.configure(text="Cancel")

    def _confirm(self) -> None:
        inchi = self.inchi_var.get()
        inchikey = self.inchikey_var.get()
        smiles = self.smiles_var.get()
        cas: str | None = self.cas_var.get()
        if not cas:
            cas = None
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
            self.parent.database.__init__()  # type: ignore

            existing_data_uuids = self.parent.database.get_data_uuids(molecule_uuid)
            for data_uuid, data in self.data_var.items():
                molecule_has_data = bool(existing_data_uuids)
                data_exists = data_uuid in existing_data_uuids
                data_updated = data_uuid in self._updated_data
                data_was_deleted = data_uuid in self._deleted_data
                print(data_uuid, self._deleted_data, data_was_deleted)
                if data_was_deleted:
                    self.parent.database.delete_data(molecule_uuid=molecule_uuid, data_uuid=data_uuid)
                elif not molecule_has_data or not data_exists:
                    logging.info("committing new data for molecule %s datauuid %s to database: %s", molecule_uuid, data_uuid, data)
                    self.parent.database.add_data(molecule_uuid, data=data, data_uuid=data_uuid)
                elif data_updated:
                    self.parent.database.modify_data(molecule_uuid, data=data, data_uuid=data_uuid)

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
        for child in self.winfo_children():
            child.destroy()

        self.search = ttk.Frame(self)
        self.search_label = ttk.Label(self.search, text="Search: ")
        self.search_label.grid(column=0, row=0, padx=self.padx, pady=self.pady)
        self.search_var = tk.StringVar(self)
        self.search_box = ttk.Entry(self.search, textvariable=self.search_var)
        self.search_box.grid(column=1, row=0, sticky="ew", padx=self.padx, pady=self.pady)
        self.search.columnconfigure(1, weight=1)
        self.search.pack(fill="both", expand=True)

        self.scroll_canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        self.scrollable_frame = tk.Frame(self.scroll_canvas)
        self.scrollable_frame.bind("<Configure>", lambda _event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))

        window_id = self.scroll_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scroll_canvas.bind("<Configure>", lambda e: self.scroll_canvas.itemconfigure(window_id, width=e.width))
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.bind_all("<MouseWheel>", lambda event: self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.scrollable_frame.columnconfigure(0, weight=1)

        self._populate_ui_moleculelist()  # TODO(TheTimebreaker): link this to the search; and then filter results based on input

    def _populate_ui_moleculelist(self) -> None:
        def sort_molecules_by_name(molecules: dict[str, Molecule]) -> dict[str, Molecule]:
            def _sorter(items: tuple[str, Molecule]) -> Any:
                trans = str.maketrans(
                    {
                        "0": "",
                        "1": "",
                        "2": "",
                        "3": "",
                        "4": "",
                        "5": "",
                        "6": "",
                        "7": "",
                        "8": "",
                        "9": "",
                        "-": "",
                        "'": "",
                        '"': "",
                    }
                )
                if items[1].get("names", []):
                    name = str(items[1].get("names", [])[0])  # type: ignore
                    name = name.lower()
                    name = name.translate(trans)
                    return name
                else:
                    return items[1].get("cas", "")

            return dict(sorted(molecules.items(), key=_sorter))

        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        molecules: dict[str, Molecule] = sort_molecules_by_name(self.parent.database.by_uuid)

        for i, (molecule_uuid, molecule) in enumerate(molecules.items()):
            print(molecule_uuid, molecule)
            ttk.Label(self.scrollable_frame, text=get_display_name(molecule)).grid(row=i, column=0, padx=self.padx, pady=self.pady, sticky="ew")
            ttk.Button(
                self.scrollable_frame,
                text="View",
                command=lambda molecule_uuid=molecule_uuid: self._view(molecule_uuid),  # type: ignore
            ).grid(row=i, column=1, padx=self.padx, pady=self.pady)
            ttk.Button(
                self.scrollable_frame,
                text="Edit",
                command=lambda molecule_uuid=molecule_uuid: self._edit(molecule_uuid),  # type: ignore
            ).grid(row=i, column=2, padx=self.padx, pady=self.pady)
            ttk.Button(
                self.scrollable_frame,
                text="Delete",
                command=lambda molecule_uuid=molecule_uuid: self._delete(molecule_uuid),  # type: ignore
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
        self.parent.database.__init__()  # type: ignore
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
    configure_ttk_style()
    g = GUI(root)
    tk.mainloop()
