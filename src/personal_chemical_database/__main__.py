import argparse
import logging
import sys
from importlib.metadata import version

from packaging.version import Version

from .main import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-port", type=int)
    parser.add_argument(
        "--use-default-config",
        action="store_true",
        help="Use a temporary empty database and skip the config prompt (for plain testing if the application starts).",
    )
    args = parser.parse_args()

    APP_VERSION = Version(version("personal-chemical-database"))
    print(f"{APP_VERSION=}")

    sys.exit(main(args.ready_port, args.use_default_config))
