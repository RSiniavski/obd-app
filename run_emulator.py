import config
from emulator.server import start_emulator_server

if __name__ == "__main__":
    start_emulator_server(config.EMULATOR_HOST, config.EMULATOR_PORT)