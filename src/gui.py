from __future__ import annotations

import logging
from io import BytesIO
from typing import Literal, cast, override

import pubchempy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from rdkit import Chem
from rdkit.Chem import Draw

from database import Database, Molecule, MoleculeData, NMRData, generate_molecule_data, get_display_name

DataType = Literal["1H NMR", "13C NMR", "19F NMR", "31P NMR", "IR", "Mass", "boiling point", "melting point", "color"]
NMRType = Literal["1H NMR", "13C NMR", "19F NMR", "31P NMR"]
DATA_TYPES: tuple[DataType, ...] = ("1H NMR", "13C NMR", "19F NMR", "31P NMR", "IR", "Mass", "boiling point", "melting point", "color")
NMR_TYPES: tuple[NMRType, ...] = ("1H NMR", "13C NMR", "19F NMR", "31P NMR")


def _molecule_sort_key(molecule: Molecule) -> str:
    name = get_display_name(molecule).lower()
    return name.translate(str.maketrans("", "", "0123456789-'\","))


class ClickableLabel(QLabel):
    clicked = Signal()

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class MoleculeDataDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        data: MoleculeData | NMRData | None,
        *,
        read_only: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Data details")
        self.setMinimumWidth(640)
        form = QFormLayout()
        self.form = form
        self.type_box = QComboBox()
        self.type_box.addItem("")
        self.type_box.addItems(DATA_TYPES)
        self.solvent_edit = QLineEdit()
        self.frequency_edit = QLineEdit()
        self.data_edit = QTextEdit()
        self.source_edit = QLineEdit()

        if data:
            self.type_box.setCurrentText(str(data.get("data_type", "")))
            self.solvent_edit.setText(str(data.get("solvent", "")))
            self.frequency_edit.setText(str(data.get("frequency", "")))
            self.data_edit.setPlainText(str(data.get("data", "")))
            self.source_edit.setText(str(data.get("source", "")))

        form.addRow("Type:", self.type_box)
        self.solvent_row = form.rowCount()
        form.addRow("Solvent:", self.solvent_edit)
        self.frequency_row = form.rowCount()
        form.addRow("Frequency:", self.frequency_edit)
        form.addRow("Data:", self.data_edit)
        form.addRow("Source:", self.source_edit)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        self.buttons = QDialogButtonBox()
        if read_only:
            self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        else:
            self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
            self.buttons.addButton(QDialogButtonBox.StandardButton.Save)
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        self.type_box.currentTextChanged.connect(self._update_nmr_fields)
        self._update_nmr_fields(self.type_box.currentText())

        for widget in (self.type_box, self.solvent_edit, self.frequency_edit, self.data_edit, self.source_edit):
            widget.setEnabled(not read_only)
        if read_only:
            self.data_edit.setReadOnly(True)

    def _update_nmr_fields(self, data_type: str) -> None:
        is_nmr = "NMR" in data_type
        self.form.setRowVisible(self.solvent_row, is_nmr)
        self.form.setRowVisible(self.frequency_row, is_nmr)

    def _validate_and_accept(self) -> None:
        values = self.values()
        if not values["Type"] or not values["Data"] or not values["Source"]:
            QMessageBox.warning(self, "Invalid entry", "Type, data, and source are required.")
        elif values["Type"] not in DATA_TYPES:
            QMessageBox.warning(self, "Invalid entry", "Select a supported data type.")
        else:
            self.accept()

    def values(self) -> dict[str, str]:
        return {
            "Type": self.type_box.currentText().strip(),
            "Solvent": self.solvent_edit.text().strip(),
            "Frequency": self.frequency_edit.text().strip(),
            "Data": self.data_edit.toPlainText().strip(),
            "Source": self.source_edit.text().strip(),
        }


class AddMolecule(QWidget):
    def __init__(self, parent: GUI, *, mode: Literal["add", "edit", "view"] = "add") -> None:
        super().__init__(parent)
        self.app_window = parent
        self.mode = mode
        self.previous_tab: QWidget | None = None
        self.molecule_uuid: str | None = None
        self.compound_names: list[str] = []
        self._new_compound_names: set[str] = set()
        self._deleted_compound_names: set[str] = set()
        self.data: dict[str, MoleculeData | NMRData] = {}
        self._new_data: set[str] = set()
        self._updated_data: set[str] = set()
        self._deleted_data: set[str] = set()

        self.inchi_edit = QLineEdit()
        self.inchikey_edit = QLineEdit()
        self.smiles_edit = QLineEdit()
        self.cas_edit = QLineEdit()
        self.names_layout = QVBoxLayout()
        self.data_layout = QVBoxLayout()
        self.structure_label = ClickableLabel()
        self.structure_label.clicked.connect(self._show_structure)
        self.structure_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.structure_label.setFixedSize(180, 180)
        self.structure_label.setStyleSheet("border: 1px solid palette(mid);")

        self._build_ui()

    @property
    def viewer_mode(self) -> bool:
        return self.mode == "view"

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        top = QHBoxLayout()
        form = QFormLayout()
        form.addRow("InChI:", self.inchi_edit)
        form.addRow("InChIKey:", self.inchikey_edit)
        form.addRow("SMILES:", self.smiles_edit)
        form.addRow("CAS:", self.cas_edit)
        top.addLayout(form, 1)
        if self.viewer_mode:
            top.addWidget(self.structure_label)
        content_layout.addLayout(top)

        names_heading = QLabel("Compound name(s)")
        names_heading.setStyleSheet("font-weight: bold;")
        content_layout.addWidget(names_heading)
        content_layout.addLayout(self.names_layout)

        data_heading = QLabel("Additional data")
        data_heading.setStyleSheet("font-weight: bold;")
        content_layout.addWidget(data_heading)
        content_layout.addLayout(self.data_layout)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        for widget in (self.inchi_edit, self.inchikey_edit, self.smiles_edit, self.cas_edit):
            widget.setReadOnly(self.viewer_mode)

        if not self.viewer_mode:
            self._append_add_name_button()
            self._append_add_data_button()

        actions = QHBoxLayout()
        actions.addStretch(1)
        if self.mode == "add":
            autofill_button = QPushButton("Autofill")
            autofill_button.clicked.connect(self._autofill)
            actions.addWidget(autofill_button)
        if self.mode == "view":
            confirm_text = "Exit Viewer"
        elif self.mode == "edit":
            confirm_text = "Save"
        else:
            confirm_text = "Confirm"
        self.confirm_button = QPushButton(confirm_text)
        self.confirm_button.clicked.connect(self._confirm)
        actions.addWidget(self.confirm_button)
        self.clear_button = QPushButton("Cancel" if self.mode == "edit" else ("Exit Viewer" if self.viewer_mode else "Clear"))
        self.clear_button.clicked.connect(self._clear)
        if self.viewer_mode:
            self.confirm_button.hide()
        actions.addWidget(self.clear_button)
        outer.addLayout(actions)

        self._update_compound_names()
        self._update_data()

    def _update_compound_names(self) -> None:
        self._clear_layout(self.names_layout)
        for name in self.compound_names:
            row = QHBoxLayout()
            label = QLabel(name)
            label.setStyleSheet(self._status_style(name in self._deleted_compound_names, name in self._new_compound_names))
            row.addWidget(label, 1)
            if not self.viewer_mode:
                if name in self._deleted_compound_names:
                    button = QPushButton("Undo")
                    button.clicked.connect(lambda _checked=False, current=name: self._undo_remove_name(current))
                else:
                    button = QPushButton("Delete")
                    button.clicked.connect(lambda _checked=False, current=name: self._remove_name(current))
                row.addWidget(button)
            self.names_layout.addLayout(row)
        if not self.viewer_mode:
            self._append_add_name_button()

    def _update_data(self) -> None:
        self._clear_layout(self.data_layout)
        for index, (data_uuid, data) in enumerate(self.data.items()):
            row = QHBoxLayout()
            if data.get("frequency") and data.get("solvent"):
                text = f"#{index}-{data['data_type']} ({data.get('frequency')} / {data.get('solvent')})"
            else:
                text = f"#{index}-{data['data_type']}"
            label = QPushButton(text)
            label.setStyleSheet(self._status_style(data_uuid in self._deleted_data, data_uuid in self._new_data, data_uuid in self._updated_data))
            label.setFlat(True)
            label.setEnabled(True)
            label.clicked.connect(lambda _checked=False, key=data_uuid: self.open_data_dialog(data_uuid=key))
            row.addWidget(label, 1)
            if not self.viewer_mode:
                if data_uuid in self._deleted_data:
                    button = QPushButton("Undo")
                    button.clicked.connect(lambda _checked=False, key=data_uuid: self._undo_remove_data(key))
                else:
                    button = QPushButton("Delete")
                    button.clicked.connect(lambda _checked=False, key=data_uuid: self._remove_data(key))
                row.addWidget(button)
            self.data_layout.addLayout(row)
        if not self.viewer_mode:
            self._append_add_data_button()

    def _append_add_name_button(self) -> None:
        button = QPushButton("Add name")
        button.clicked.connect(self._open_add_name_dialog)
        self.names_layout.addWidget(button)

    def _append_add_data_button(self) -> None:
        button = QPushButton("Add data")
        button.clicked.connect(self.open_data_dialog)
        self.data_layout.addWidget(button)

    @staticmethod
    def _status_style(deleted: bool, added: bool = False, edited: bool = False) -> str:
        if deleted:
            return "color: red;"
        if added:
            return "color: green;"
        if edited:
            return "color: blue;"
        return ""

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            if child := item.layout():
                while child.count():
                    child_item = child.takeAt(0)
                    if child_item is not None and (widget := child_item.widget()):
                        widget.deleteLater()
            elif widget := item.widget():
                widget.deleteLater()

    def _open_add_name_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add compound name")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Compound name:"))
        entry = QLineEdit()
        layout.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = entry.text().strip()
            if not name:
                QMessageBox.warning(self, "Invalid entry", "A compound name cannot be empty.")
                return
            if name not in self.compound_names:
                self.compound_names.append(name)
                self._new_compound_names.add(name)
            self._deleted_compound_names.discard(name)
            self._update_compound_names()

    def open_data_dialog(self, *, data_uuid: str | None = None) -> None:
        existing = self.data.get(data_uuid) if data_uuid else None
        dialog = MoleculeDataDialog(self, existing, read_only=self.viewer_mode)
        if dialog.exec() != QDialog.DialogCode.Accepted or self.viewer_mode:
            return
        values = dialog.values()
        data_type = cast(DataType, values["Type"])
        if data_type in NMR_TYPES:
            data_record: MoleculeData | NMRData = NMRData(
                data_type=cast(NMRType, data_type),
                data=values["Data"],
                source=values["Source"],
                solvent=values["Solvent"],
                frequency=values["Frequency"],
            )
        else:
            data_record = MoleculeData(data_type=data_type, data=values["Data"], source=values["Source"])

        if data_uuid is None:
            data_uuid = self.app_window.database._gen_uuid()
            self._new_data.add(data_uuid)
        else:
            self._updated_data.add(data_uuid)
            self._deleted_data.discard(data_uuid)
        self.data[data_uuid] = data_record
        self._update_data()

    def _remove_name(self, name: str) -> None:
        self._deleted_compound_names.add(name)
        self._new_compound_names.discard(name)
        self._update_compound_names()

    def _undo_remove_name(self, name: str) -> None:
        self._deleted_compound_names.discard(name)
        self._update_compound_names()

    def _remove_data(self, data_uuid: str) -> None:
        if data_uuid in self._new_data:
            self.data.pop(data_uuid, None)
            self._new_data.discard(data_uuid)
            self._updated_data.discard(data_uuid)
            self._deleted_data.discard(data_uuid)
            self._update_data()
            return
        self._deleted_data.add(data_uuid)
        self._update_data()

    def _undo_remove_data(self, data_uuid: str) -> None:
        self._deleted_data.discard(data_uuid)
        self._update_data()

    def _show_structure(self) -> None:
        smiles = self.smiles_edit.text()
        if not smiles:
            return
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            QMessageBox.warning(self, "Invalid structure", "The SMILES value could not be rendered.")
            return
        image = Draw.MolToImage(molecule, size=(600, 600))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        dialog = QDialog(self)
        dialog.setWindowTitle("LEWIS structure")
        layout = QVBoxLayout(dialog)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        layout.addWidget(image_label)
        dialog.exec()

    def _autofill(self) -> None:
        values = {
            "inchi": self.inchi_edit.text().strip() or None,
            "inchikey": self.inchikey_edit.text().strip() or None,
            "smiles": self.smiles_edit.text().strip() or None,
            "cas": self.cas_edit.text().strip() or None,
            "compound_name": self.compound_names[0] if self.compound_names else None,
        }
        try:
            molecule = generate_molecule_data(
                inchi=values["inchi"],
                inchikey=values["inchikey"],
                smiles=values["smiles"],
                cas=values["cas"],
                compound_name=values["compound_name"],
                choose_compound=self._choose_pubchem_compound,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Autofill unsuccessful", str(error))
            return
        self.inchi_edit.setText(molecule["inchi"])
        self.inchikey_edit.setText(molecule["inchikey"])
        self.smiles_edit.setText(molecule["smiles"])
        self.cas_edit.setText(molecule["cas"] or "")
        if molecule["names"]:
            self.compound_names = molecule["names"]
            self._update_compound_names()

    def _choose_pubchem_compound(self, compounds: list[pubchempy.Compound]) -> pubchempy.Compound | None:
        names = [f"{getattr(compound, 'iupac_name', None) or 'Compound'} (CID {compound.cid})" for compound in compounds]
        choice, accepted = QInputDialog.getItem(self, "Select compound", "Multiple matches were found:", names, 0, False)
        if not accepted:
            return None
        return compounds[names.index(choice)]

    def _confirm(self) -> None:
        if self.viewer_mode:
            self._clear()
            return
        inchi = self.inchi_edit.text().strip()
        inchikey = self.inchikey_edit.text().strip()
        smiles = self.smiles_edit.text().strip()
        if not inchi or not inchikey or not smiles:
            QMessageBox.warning(self, "Invalid molecule", "InChI, InChIKey, and SMILES are required.")
            return

        molecule = Molecule(
            inchi=inchi,
            inchikey=inchikey,
            smiles=smiles,
            cas=self.cas_edit.text().strip() or None,
            names=[name for name in self.compound_names if name not in self._deleted_compound_names] or None,
        )
        if self.mode == "add":
            if self.app_window.database.is_this_in_db(molecule=molecule):
                QMessageBox.warning(self, "Duplicate molecule", "This molecule is already in the database.")
                return
            if not self.app_window.database.create_entry(molecule):
                QMessageBox.critical(self, "Save failed", "The molecule could not be added to the database.")
                return
            self.app_window.database = Database()
            saved_molecule_uuid = self.app_window.database.by_inchi[inchi]
        else:
            if self.molecule_uuid is None:
                logging.error("Cannot save molecule edits: molecule UUID was not assigned.")
                QMessageBox.critical(self, "Save failed", "The molecule could not be saved.")
                return
            saved_molecule_uuid = self.molecule_uuid
            if not self.app_window.database.overwrite_entry(molecule_uuid=saved_molecule_uuid, molecule=molecule):
                QMessageBox.critical(self, "Save failed", "The molecule could not be saved.")
                return

        self._save_data(saved_molecule_uuid)
        self.app_window.database = Database()
        self.app_window.browse_tab.populate()
        if self.mode == "add":
            self._clear()
        else:
            self.app_window._close_temporary_tab(self)

    def _save_data(self, molecule_uuid: str) -> None:
        existing_data_uuids = set(self.app_window.database.get_data_uuids(molecule_uuid))
        for data_uuid, data in self.data.items():
            if data_uuid in self._deleted_data:
                self.app_window.database.delete_data(molecule_uuid=molecule_uuid, data_uuid=data_uuid)
            elif data_uuid in self._new_data or data_uuid not in existing_data_uuids:
                self.app_window.database.add_data(molecule_uuid, data=data, data_uuid=data_uuid)
            elif data_uuid in self._updated_data:
                self.app_window.database.modify_data(molecule_uuid, data=data, data_uuid=data_uuid)

    def _load_molecule(self, molecule_uuid: str) -> None:
        molecule = self.app_window.database.by_uuid[molecule_uuid]
        self._reset_fields()
        self.inchi_edit.setText(molecule["inchi"])
        self.inchikey_edit.setText(molecule["inchikey"])
        self.smiles_edit.setText(molecule["smiles"])
        self.cas_edit.setText(molecule.get("cas") or "")
        self.compound_names = list(molecule.get("names") or [])
        for data_uuid in self.app_window.database.get_data_uuids(molecule_uuid):
            self.data[data_uuid] = self.app_window.database.read_data(molecule_uuid, data_uuid)
        self.molecule_uuid = molecule_uuid
        self._update_compound_names()
        self._update_data()
        if self.viewer_mode:
            molecule_image = Draw.MolToImage(Chem.MolFromSmiles(molecule["smiles"]), size=(180, 180))
            buffer = BytesIO()
            molecule_image.save(buffer, format="PNG")
            self.structure_label.setPixmap(QPixmap())
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.structure_label.setPixmap(pixmap)

    def _reset_fields(self) -> None:
        self.inchi_edit.clear()
        self.inchikey_edit.clear()
        self.smiles_edit.clear()
        self.cas_edit.clear()
        self.compound_names = []
        self._new_compound_names.clear()
        self._deleted_compound_names.clear()
        self.data.clear()
        self._new_data.clear()
        self._updated_data.clear()
        self._deleted_data.clear()
        self.molecule_uuid = None

    def _clear(self) -> None:
        self._reset_fields()
        self._update_compound_names()
        self._update_data()
        if self.previous_tab is not None and self.mode in ("edit", "view"):
            self.app_window._close_temporary_tab(self)
        elif self.previous_tab is not None:
            self.app_window.tabs.setCurrentWidget(self.previous_tab)


class Browse(QWidget):
    def __init__(self, parent: GUI) -> None:
        super().__init__(parent)
        self.app_window = parent
        layout = QVBoxLayout(self)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by compound name or CAS")
        self.search_edit.textChanged.connect(self.populate)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.list_content = QWidget()
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.list_content)
        layout.addWidget(self.scroll_area, 1)
        self.populate()

    def populate(self, _text: str = "") -> None:
        AddMolecule._clear_layout(self.list_layout)
        term = self.search_edit.text().strip().lower()
        molecules = sorted(self.app_window.database.by_uuid.items(), key=lambda item: _molecule_sort_key(item[1]))
        visible = [
            (molecule_uuid, molecule)
            for molecule_uuid, molecule in molecules
            if not term or any(term in value.lower() for value in [molecule.get("cas") or "", *(molecule.get("names") or [])])
        ]
        for molecule_uuid, molecule in visible:
            row = QHBoxLayout()
            row.addWidget(QLabel(get_display_name(molecule)), 1)
            for title, action in (
                ("View", self._view),
                ("Edit", self._edit),
                ("Delete", self._delete),
            ):
                button = QPushButton(title)
                button.clicked.connect(lambda _checked=False, key=molecule_uuid, callback=action: callback(key))
                row.addWidget(button)
            self.list_layout.addLayout(row)
        if not visible:
            self.list_layout.addWidget(QLabel("No molecules found."))

    def _view(self, molecule_uuid: str) -> None:
        self.app_window._open_temporary_tab("view", molecule_uuid)

    def _edit(self, molecule_uuid: str) -> None:
        self.app_window._open_temporary_tab("edit", molecule_uuid)

    def _delete(self, molecule_uuid: str) -> None:
        if not self.app_window.database.is_this_in_db(uuid=molecule_uuid):
            QMessageBox.warning(self, "Molecule not found", "The selected molecule is no longer in the database.")
            return
        molecule = self.app_window.database.by_uuid[molecule_uuid]
        confirmation = QMessageBox.question(
            self,
            "Delete molecule?",
            f"Are you sure you want to delete this molecule?\n\n{molecule_uuid}\n{get_display_name(molecule)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return
        if not self.app_window.database.delete_entry(uuid=molecule_uuid):
            QMessageBox.critical(self, "Deletion failed", f"Could not delete molecule {molecule_uuid}.")
            return
        self.app_window.database = Database()
        self.populate()


class GUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Personal Chemical Database")
        self.setMinimumSize(800, 520)
        self.resize(1000, 720)
        self.database = Database()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.add_molecule = AddMolecule(self, mode="add")
        self.browse_tab = Browse(self)
        self.tabs.addTab(self.add_molecule, "Add Molecule")
        self.tabs.addTab(self.browse_tab, "Browse")
        self._temporary_tabs: dict[str, AddMolecule] = {}

    def _open_temporary_tab(self, mode: Literal["edit", "view"], molecule_uuid: str) -> None:
        tab = self._temporary_tabs.get(mode)
        if tab is None:
            tab = AddMolecule(self, mode=mode)
            self._temporary_tabs[mode] = tab
        tab.previous_tab = self.browse_tab
        tab._load_molecule(molecule_uuid)
        title = "Edit Molecule" if mode == "edit" else "View Molecule"
        index = self.tabs.indexOf(tab)
        if index < 0:
            self.tabs.addTab(tab, title)
        self.tabs.setCurrentWidget(tab)

    def _close_temporary_tab(self, tab: AddMolecule) -> None:
        index = self.tabs.indexOf(tab)
        if index >= 0:
            self.tabs.removeTab(index)
        if tab.previous_tab is not None:
            self.tabs.setCurrentWidget(tab.previous_tab)
