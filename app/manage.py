from data.helpers import *
from data.load_banner import *
from data.hard_coded_defaults import load_defaults
from models import *
from models.config import Base, engine
import argparse
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def simple_create_database():
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load data")
    parser.add_argument("command", help="Command to execute", choices=["load"])
    parser.add_argument("data", help="Data to load", choices=["default", "banner", "database"])
    args = parser.parse_args()
    if args.command == "load":
        if args.data == "banner":
            load_everything_from_banner()
        elif args.data == "default":
            load_defaults()
        elif args.data == "database":
            simple_create_database()
