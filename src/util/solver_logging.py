import logging
import sys
import json


def set_stdout_logging(log_level: int = logging.INFO):
    root = logging.getLogger()
    root.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    file_handler = logging.FileHandler('log.txt')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def log_to_json(filename, s, id):
    with open(filename, 'a') as file:
        file.write(f"{str(id)}: {str(json.loads(bytes(s)))}")
        file.write('\n')
