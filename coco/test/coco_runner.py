"""Run coco script for unit tests."""

import json
import logging
import subprocess
import os
import pathlib
import tempfile
import shutil
import time

STATE_DIR = tempfile.TemporaryDirectory()
BLOCKLIST_DIR = tempfile.TemporaryDirectory()
BLOCKLIST_PATH = pathlib.Path(BLOCKLIST_DIR.name, "blocklist.json")

COCO_DAEMON = (
    shutil.which("cocod")
    or os.path.dirname(os.path.abspath(__file__)) + "/../../scripts/cocod"
)

COCO = (
    shutil.which("coco")
    or os.path.dirname(os.path.abspath(__file__)) + "/../../scripts/coco"
)

CONFIG = {
    "comet_broker": {"enabled": False},
    "metrics_port": 12056,
    "host": "localhost",
    "port": 12055,
    "log_level": "DEBUG",
    "blocklist_path": str(BLOCKLIST_PATH),
    "storage_path": STATE_DIR.name,
}
CLIENT_ARGS = [
    COCO,
    "-s",
    "json",
    "-r",
    "FULL",
    "--silent",
]

logger = logging.getLogger(__name__)


class Runner:
    """Coco Runner for unit tests."""

    def __init__(self, config, endpoints, reset_on_start=False, reset_on_shutdown=True):
        self.reset_on_shutdown = reset_on_shutdown
        self.start_coco(config, endpoints, reset_on_start)
        time.sleep(1)

    def __del__(self):
        """Destructor."""
        if self.reset_on_shutdown:
            self.client("reset-state", silent=True)
        self.stop_coco()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__del__()

    def client(self, command, data=[], silent=False):
        """Make coco-client script call a coco endpoint."""
        cmd = CLIENT_ARGS + ["-c", self.configfile.name, command] + data
        logger.debug(f"calling coco client: {cmd}")
        try:
            result = subprocess.check_output(cmd, encoding="utf-8")
        except subprocess.CalledProcessError as e:
            print(f"coco client errored: {e}")
            return None

        if not silent:
            print(result)
        if result == "":
            return None
        try:
            result = json.loads(result)
        except json.JSONDecodeError as err:
            print(f"Failure parsing json returned by client: {err}.\n{result}")
            return None
        return result

    def start_coco(self, config, endpoint_configs, reset):
        """Start coco with a given config."""
        CONFIG.update(config)

        # Write endpoint configs to file
        with tempfile.TemporaryDirectory() as endpointdir:
            CONFIG["endpoint_dir"] = endpointdir.name
            for name, endpoint_conf in endpoint_configs.items():
                with open(
                    os.path.join(endpointdir.name, name + ".conf"), "w"
                ) as outfile:
                    json.dump(endpoint_conf, outfile)

        # Write config to file
        self.configfile = tempfile.NamedTemporaryFile("w")
        json.dump(CONFIG, self.configfile)
        self.configfile.flush()

        args = []
        if reset:
            args.append("--reset")

        self.coco = subprocess.Popen([COCO_DAEMON, "-c", self.configfile.name, *args])

    def stop_coco(self):
        """Stop coco script."""
        self.coco.terminate()
        self.coco.communicate()
