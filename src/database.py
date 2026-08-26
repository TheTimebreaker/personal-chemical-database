import json
import logging
import uuid as uuid_module
from typing import Literal, TypedDict

import pubchempy
from rdkit import Chem
from send2trash import send2trash

from config import db_path


class Molecule(TypedDict):
    inchi: str
    inchikey: str
    smiles: str
    cas: str | None
    names: list[str] | None


class MoleculeData(TypedDict):
    data_type: Literal["1H NMR", "13C NMR", "19F NMR", "31P NMR", "IR", "Mass", "boiling point", "melting point", "color"]
    data: str
    source: str


class NMRData(MoleculeData):
    data_type: Literal["1H NMR", "13C NMR", "19F NMR", "31P NMR"]
    solvent: str
    frequency: float
    data: str
    source: str


class Database:
    def __init__(self) -> None:
        self.db_path = db_path
        self.molecules_path = db_path / "molecules"
        self.molecules_path.mkdir(parents=True, exist_ok=True)

        self.by_uuid: dict[str, Molecule] = {}
        self.by_inchi: dict[str, str] = {}
        self.by_inchikey: dict[str, str] = {}
        self.by_smiles: dict[str, str] = {}
        self.by_cas: dict[str, str] = {}
        self.by_name: dict[str, str] = {}

        self.read_db_metadata()

    def _gen_uuid(self) -> None:
        return uuid_module.uuid4()

    def search_in_db(
        self,
        *,
        inchi: str | None = None,
        inchikey: str | None = None,
        smiles: str | None = None,
        cas: str | None = None,
        compound_name: str | None = None,
        molecule: Molecule | None = None,
    ) -> str | None:
        if molecule is not None:
            inchi = molecule["inchi"]
        if inchi is not None:
            if not inchi.startswith("InChI="):  # the "InChI=" part is actually part of the inchi, but thats not really intuitive so this adds it
                inchi = f"InChI={inchi}"
            return self.by_inchi.get(inchi, None)
        elif inchikey is not None:
            return self.by_inchikey(inchikey, None)
        elif smiles is not None:
            return self.by_smiles.get(smiles, None)
        elif cas is not None:
            return self.by_cas.get(cas, None)
        elif compound_name is not None:
            return self.by_name.get(compound_name, None)

    def is_this_in_db(self, *, uuid: str | None = None, molecule: Molecule | None = None) -> bool:
        if self.by_uuid.get(uuid, None):
            return True
        if self.by_inchikey.get(molecule["inchikey"], None):
            return True
        return False

    def create_entry(self, molecule: Molecule) -> bool:
        if self.is_this_in_db(molecule=molecule):
            logging.error("Molecule could not be added to database, because such a molecule is already in there.")
            return False

        molecule_uuid = str(self._gen_uuid())
        self.write_metadata_file(uuid=molecule_uuid, molecule=molecule)
        return True

    def overwrite_entry(self, molecule_uuid: str, molecule: Molecule) -> bool:
        if not self.is_this_in_db(uuid=molecule_uuid):
            logging.error("Molecule is not in database (and therefore can't be overwritten).")
            return False

        self.write_metadata_file(uuid=molecule_uuid, molecule=molecule)
        return True

    def delete_entry(
        self,
        uuid: str | None = None,
    ) -> bool:

        print("Deleting molecule from database...")
        deletion_path = self.molecules_path / uuid
        if not deletion_path.is_dir():
            raise FileNotFoundError("Could not delete molecule %s from db, because the path %s could not be found.", uuid, deletion_path)
        send2trash(deletion_path)
        print("Deleting molecule from database... Done!")
        return True

    def add_entry_names(
        self,
        uuid: str | None = None,
    ) -> bool:
        result = self.by_uuid[uuid]
        print(f"Current names: {result["names"]}")

        msg = "Please enter additional name (press ENTER without typing anything to save your changes):"
        add = input(msg)
        while add:
            while add.startswith(" "):
                add = add[1:]
            while add.endswith(" "):
                add = add[:-1]

            if result["names"] is None:
                result["names"] = [add]
            else:
                result["names"] = result["names"] + [add]

            add = input(msg)

        self.write_metadata_file(uuid=uuid, molecule=result)

        return True

    def modify_entry_cas(
        self,
        uuid: str | None = None,
    ) -> None:
        result = self.by_uuid[uuid]
        print(f"Selected molecule: {result}")

        add = input("Please enter CAS:")
        while add.startswith(" "):
            add = add[1:]
        while add.endswith(" "):
            add = add[:-1]
        result["cas"] = add

        self.write_metadata_file(uuid=uuid, molecule=result)

        return True

    def read_metadata_file(self, uuid: str) -> Molecule:
        file_path = self.molecules_path / uuid / "metadata.json"
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Path at %s does not point at file, cannot read.", str(file_path))

        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

        inchi = data.get("inchi", None)
        inchikey = data.get("inchikey", None)
        smiles = data.get("smiles", None)
        cas = data.get("cas", None)
        names = data.get("names", None)

        if any(val is None for val in (inchi, inchikey, smiles)):
            raise ValueError("Molecule metadata file at path %s is invalid, arguments missing.", file_path)

        return Molecule(inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, names=names)

    def write_metadata_file(self, *, uuid: str, molecule: Molecule) -> None:
        file_path = self.molecules_path / uuid / "metadata.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(molecule, indent=4, sort_keys=True))

    def read_db_metadata(self) -> None:
        for uuid_molecule_path in self.molecules_path.iterdir():
            uuid = uuid_molecule_path.stem
            molecule = self.read_metadata_file(uuid)
            self.by_uuid[uuid] = molecule
            self.by_inchi[molecule["inchi"]] = uuid
            self.by_inchikey[molecule["inchikey"]] = uuid
            self.by_smiles[molecule["smiles"]] = uuid
            if molecule["cas"]:
                self.by_cas[molecule["cas"]] = uuid
            if molecule["names"]:
                for name in molecule["names"]:
                    self.by_name[name] = uuid

    def get_data_uuids(self, molecule_uuid: str) -> list[str]:
        molecule_data_path = self.molecules_path / molecule_uuid / "data"
        molecule_data_path.mkdir(parents=True, exist_ok=True)
        out = []
        for data_uuid_path in molecule_data_path.iterdir():
            data_uuid = data_uuid_path.stem
            out.append(data_uuid)
        return out

    def add_data(self, molecule_uuid: str, data: MoleculeData | NMRData, *, data_uuid: str | None = None) -> None:
        if data_uuid is None:
            data_uuid = self._gen_uuid()
        self.write_more_data(molecule_uuid, data_uuid, data)

    def modify_data(self, molecule_uuid: str, data: MoleculeData | NMRData, *, data_uuid: str | None = None) -> None:
        if data_uuid is None:
            raise ValueError
        self.write_more_data(molecule_uuid, data_uuid, data)

    def delete_data(self, molecule_uuid: str, data_uuid: str) -> bool:
        try:
            file_path = self.molecules_path / molecule_uuid / "data" / f"{data_uuid}.json"
            send2trash(file_path)
            return True
        except Exception as error:
            logging.error("Deletion of data file %s failed: %s", file_path, repr(error))
            return False

    def read_data(self, molecule_uuid: str, data_uuid: str) -> MoleculeData | NMRData:
        file_path = self.molecules_path / molecule_uuid / "data" / f"{data_uuid}.json"
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Path at %s does not point at file, cannot read.", str(file_path))

        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

        datatype = data.get("data_type", None)
        data_content = data.get("data", None)
        source = data.get("source", None)
        required_values = [datatype, data_content, source]
        if "NMR" in datatype:
            solvent = data.get("solvent", None)
            frequency = data.get("frequency", None)

        if any(val is None for val in required_values):
            raise ValueError("Molecule metadata file at path %s is invalid, arguments missing.", file_path)

        if "NMR" in datatype:
            return NMRData(data_type=datatype, data=data_content, source=source, solvent=solvent, frequency=frequency)
        else:
            return MoleculeData(data_type=datatype, data=data_content, source=source)

    def write_more_data(self, molecule_uuid: str, data_uuid: str, data: MoleculeData | NMRData) -> None:
        file_path = self.molecules_path / molecule_uuid / "data" / f"{data_uuid}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, indent=4, sort_keys=True))


def generate_molecule_data(
    *,
    smiles: str | None = None,
    inchi: str | None = None,
    inchikey: str | None = None,
    cas: str | None = None,
    compound_name: str | None = None,
) -> Molecule:
    if smiles:
        molecule_rdkitmol = Chem.MolFromSmiles(smiles, sanitize=True)
    elif inchi:
        if not inchi.startswith("InChI="):  # the "InChI=" part is actually part of the inchi, but thats not really intuitive so this adds it
            inchi = f"InChI={inchi}"
        molecule_rdkitmol = Chem.MolFromInchi(inchi, sanitize=True)
    elif cas or compound_name:
        compounds = pubchempy.get_compounds(cas or compound_name, "name")
        molecule_rdkitmol = Chem.MolFromInchi(pubchemsearchselection(compounds).inchi, sanitize=True)
    elif inchikey:
        compounds = pubchempy.get_compounds(inchikey, "inchikey")
        molecule_rdkitmol = Chem.MolFromInchi(pubchemsearchselection(compounds).inchi, sanitize=True)
    else:
        raise ValueError("The arguments given are not enough to create an RDKit molecule.")

    if not molecule_rdkitmol:
        raise ValueError("The given args could not be resolved into a valid molecule.")

    canonical_smiles = Chem.MolToSmiles(molecule_rdkitmol, canonical=True)
    inchi_str = Chem.inchi.MolToInchi(molecule_rdkitmol)
    inchikey = Chem.inchi.InchiToInchiKey(inchi_str)

    names = None
    if compound_name is not None:
        names = [compound_name]
    return Molecule(inchi=inchi_str, inchikey=inchikey, smiles=canonical_smiles, cas=cas, names=names)


def pubchemsearchselection(compounds: list[pubchempy.Compound]) -> pubchempy.Compound:
    if compounds and len(compounds) > 1:
        print("=" * 20)
        for i, c in enumerate(compounds):
            print(f"[{i}] - {c}")
        print("=" * 20)
        choice = input("Please enter the number of the compound you want to select:")
        if not choice or int(choice) > len(compounds):
            raise ValueError("No valid choice made.")
        else:
            return compounds[int(choice)]

    elif compounds and len(compounds) == 1:
        return compounds[0]

    else:
        raise ValueError("The given InChI Key could not be found in PubChem.")


def get_display_name(molecule: Molecule) -> str:
    if molecule["names"]:
        return molecule["names"][0]
    if molecule["cas"]:
        return molecule["cas"]
    return molecule["inchi"]
