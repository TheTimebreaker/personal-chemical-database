import json
import logging
from pathlib import Path

import platformdirs

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

pl_dirs = platformdirs.PlatformDirs("personal-chemical-database", "TheTimebreaker")

try:
    (pl_dirs.user_config_path).mkdir(exist_ok=True)
    config_path = pl_dirs.user_config_path / "config.json"
    logging.info("Using %s as config directory", config_path)
    with open(config_path, encoding="utf-8") as file:
        data = json.load(file)
except FileNotFoundError:
    logging.error("Config file not found at %s , using defaults.", config_path)
    data = {}

db_path = Path(data.get("db_path", pl_dirs.site_data_path)).resolve()
logging.info("Using %s as db directory", db_path)
