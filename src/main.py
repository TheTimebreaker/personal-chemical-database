import json
import logging
import uuid
from pathlib import Path
from typing import TypedDict

import pubchempy
from rdkit import Chem
from send2trash import send2trash

from config import db_path


class Molecule(TypedDict):
    uuid: str
    inchi: str
    inchikey: str
    smiles: str
    cas: str | None
    names: list[str] | None


class Database:
    def __init__(self) -> None:
        self.db_path = db_path
        self.molecules_path = db_path / "molecules"
        self.molecules_path.mkdir(parents=True, exist_ok=True)

        self.by_uuid: dict[str, Molecule] = {}
        self.by_inchi: dict[str, Molecule] = {}
        self.by_inchikey: dict[str, Molecule] = {}
        self.by_smiles: dict[str, Molecule] = {}
        self.by_cas: dict[str, Molecule] = {}
        self.by_name: dict[str, Molecule] = {}

        self.read_db_metadata()

    def search_in_db(
        self,
        *,
        uuid: str | None = None,
        inchi: str | None = None,
        inchikey: str | None = None,
        smiles: str | None = None,
        cas: str | None,
        compound_name: str | None,
    ) -> Molecule | None:
        result: Molecule | None = None
        if uuid is not None:
            result = self.by_uuid.get(uuid, None)
        elif inchi is not None:
            result = self.by_inchi.get(inchi, None)
        elif inchikey is not None:
            result = self.by_inchikey(inchikey, None)
        elif smiles is not None:
            result = self.by_smiles.get(smiles, None)
        elif cas is not None:
            result = self.by_cas.get(cas, None)
        elif compound_name is not None:
            result = self.by_name.get(compound_name, None)
        else:
            raise ValueError("No search query given, can't search.")

        return result

    def is_this_in_db(self, molecule: Molecule) -> bool:
        if self.by_uuid.get(molecule["uuid"], None):
            return True
        if self.by_inchikey.get(molecule["inchikey"], None):
            return True
        return False

    def create_entry(self, molecule: Molecule) -> bool:
        if self.is_this_in_db(molecule):
            logging.error("Molecule could not be added to database, because such a molecule is already in there.")
            return False

        self.write_metadata_file(molecule=molecule)

    def delete_entry(
        self,
        *,
        uuid: str | None = None,
        inchi: str | None = None,
        inchikey: str | None = None,
        smiles: str | None = None,
        cas: str | None = None,
        compound_name: str | None = None,
    ) -> bool:
        result = self.search_in_db(uuid=uuid, inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, compound_name=compound_name)
        if result is None:
            raise ValueError("The given molecule could not be found in the database, so it can't be deleted.")

        print(f"Found in database: {result}")
        confirmation = str(input("Are you sure to delete that? y(es) / n(o) :"))
        if any(confirmation == x for x in ("yes", " yes", "yes ", " yes ", "y", " y", "y ", " y ")):
            print("Deleting molecule from database...")
            deletion_path = self.molecules_path / result["uuid"]
            if not deletion_path.is_dir():
                raise FileNotFoundError("Could not delete molecule %s from db, because the path %s could not be found.", result, deletion_path)
            send2trash(deletion_path)
            print("Deleting molecule from database... Done!")
            return True
        else:
            print("Deletion aborted...")
            return False

    def add_entry_names(
        self,
        *,
        uuid: str | None = None,
        inchi: str | None = None,
        inchikey: str | None = None,
        smiles: str | None = None,
        cas: str | None = None,
        compound_name: str | None = None,
    ) -> bool:
        result = self.search_in_db(uuid=uuid, inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, compound_name=compound_name)
        if result is None:
            raise ValueError("The given molecule could not be found in the database, so it can't be deleted.")

        print(f"Current names: {result["names"]}")

        add = input("Please enter additional name:")
        while add:
            while add.startswith(" "):
                add = add[1:]
            while add.endswith(" "):
                add = add[:-1]

            if result["names"] is None:
                result["names"] = [add]
            else:
                result["names"] = result["names"] + [add]

            add = input("Please enter additional name:")

        self.write_metadata_file(molecule=result)

        return True

    def modify_entry_cas(
        self,
        *,
        uuid: str | None = None,
        inchi: str | None = None,
        inchikey: str | None = None,
        smiles: str | None = None,
        cas: str | None = None,
        compound_name: str | None = None,
    ) -> None:
        result = self.search_in_db(uuid=uuid, inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, compound_name=compound_name)
        if result is None:
            raise ValueError("The given molecule could not be found in the database, so it can't be deleted.")

        print(f"Selected molecule: {result}")

        add = input("Please enter CAS:")
        while add.startswith(" "):
            add = add[1:]
        while add.endswith(" "):
            add = add[:-1]
        result["cas"] = add

        self.write_metadata_file(molecule=result)

        return True

    def read_metadata_file(self, file_path: Path) -> Molecule:
        if not file_path.exists() and file_path.is_file():
            raise ValueError("Path at %s does not point at file, cannot read.", str(file_path))

        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

        uuid = data.get("uuid", None)
        inchi = data.get("inchi", None)
        inchikey = data.get("inchikey", None)
        smiles = data.get("smiles", None)
        cas = data.get("cas", None)
        names = data.get("names", None)

        if any(val is None for val in (uuid, inchi, inchikey, smiles)):
            raise ValueError("Molecule metadata file at path %s is invalid, arguments missing.", file_path)

        return Molecule(uuid=uuid, inchi=inchi, inchikey=inchikey, smiles=smiles, cas=cas, names=names)

    def write_metadata_file(self, *, file_path: Path | None = None, molecule: Molecule | None = None) -> None:
        if file_path is None:
            if molecule is None:
                raise ValueError
            file_path = self.molecules_path / molecule["uuid"] / "metadata.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(molecule, indent=4, sort_keys=True))

    def read_db_metadata(self) -> None:
        for uuid_molecule in self.molecules_path.iterdir():
            metadata_file = uuid_molecule / "metadata.json"
            molecule = self.read_metadata_file(metadata_file)
            self.by_uuid[molecule["uuid"]] = molecule
            self.by_inchi[molecule["inchi"]] = molecule
            self.by_inchikey[molecule["inchikey"]] = molecule
            self.by_smiles[molecule["smiles"]] = molecule
            if molecule["cas"]:
                self.by_cas[molecule["cas"]] = molecule
            if molecule["names"]:
                for name in molecule["names"]:
                    self.by_name[name] = molecule


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


def generate_molecule_data(
    *,
    smiles: str | None = None,
    inchi: str | None = None,
    inchikey: str | None = None,
    cas: str | None = None,
    compound_name: str | None = None,
) -> Molecule:
    molecule_uuid = str(uuid.uuid4())

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
    return Molecule(uuid=molecule_uuid, inchi=inchi_str, inchikey=inchikey, smiles=canonical_smiles, cas=cas, names=names)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    m = generate_molecule_data(compound_name="toluene")
    print(m)
    db = Database()
    db.modify_entry_cas(compound_name="toluene")
# TODO(TheTimebreaker) next step: add data layer
