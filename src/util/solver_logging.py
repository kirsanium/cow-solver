import logging
import logging.handlers
import sys


def set_stdout_logging(log_level: int = logging.INFO):
    root = logging.getLogger()
    root.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    log_handler = logging.handlers.RotatingFileHandler(
        'log.txt', maxBytes=1024 * 1024 * 5, backupCount=25,
        encoding='utf-8'
    )
    log_handler.setLevel(log_level)
    log_handler.setFormatter(formatter)
    root.addHandler(log_handler)


def log_to_json(filename, s, id):
    ...
    # with open(filename, 'a') as file:
    #     file.write(f"{str(id)}: {str(s)}\n")
