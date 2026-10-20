import json
import logging
from pathlib import Path

import platformdirs
from pydantic import BaseModel
from PySide6.QtWidgets import QApplication, QFileDialog

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)


class SettingsModel(BaseModel):
    db_path: Path


def get_config_path() -> Path:
    pl_dirs = platformdirs.PlatformDirs("personal-chemical-database", "TheTimebreaker")
    (pl_dirs.user_config_path).mkdir(exist_ok=True, parents=True)
    config_path = pl_dirs.user_config_path / "config.json"
    return config_path


def save_config(settings: SettingsModel) -> None:
    data = settings.model_dump_json(indent=4)
    dst = get_config_path()
    with open(dst, "w", encoding="utf-8") as file:
        file.write(data)


def read_config() -> SettingsModel:
    config_path = get_config_path()
    try:
        logging.info("Using %s as config directory", config_path)
        with open(config_path, encoding="utf-8") as file:
            data: dict[str, str] = json.load(file)
            settings = SettingsModel(**data)

    except FileNotFoundError as error:
        logging.error("Config file not found at %s , asking user.", config_path)
        _app = QApplication.instance() or QApplication([])
        directory = QFileDialog.getExistingDirectory(None, "No config found. Select target folder for the database:")
        if not directory:
            raise ValueError("No directory selected") from error
        settings = SettingsModel(db_path=Path(directory))
        save_config(settings)

    return settings
