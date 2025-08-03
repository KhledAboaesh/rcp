# main.py
from receiver import restart_server

from pynetdicom import debug_logger
debug_logger()


if __name__ == "__main__":
    restart_server()
