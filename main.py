import sys

from leetcodebot.bot import run
from leetcodebot.db import create_tables

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Commands: run, create_tables")
    elif sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "create_tables":
        create_tables()
    else:
        print("Invalid command")
