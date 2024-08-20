"""Utility functions for the OntoDiff Curator."""

import logging
from pathlib import Path
import shlex
import subprocess
import time
import requests


RETRY_DELAY = 300  # 5 minutes
PROJECT_DIR = Path(__file__).parents[2]

def check_rate_limit(g):
    """
    Check the current rate limit status of the GitHub API.

    :param g: GitHub instance.
    :return: Tuple containing remaining requests, reset timestamp, and current timestamp.
    """
    rate_limit = g.get_rate_limit().core
    remaining = rate_limit.remaining
    reset_timestamp = rate_limit.reset.timestamp()
    current_timestamp = time.time()
    return remaining, reset_timestamp, current_timestamp


def remove_import_lines(owl_file: str):
    """
    Remove import lines from an OWL file.

    # ! This is a band-aid fix for OWL files for now. This function will be removed in the future.

    :param owl_file: Path to the OWL file.
    """
    try:
        # Read the content of the OWL file
        with open(owl_file, "r") as file:
            lines = file.readlines()

        # Write back the lines excluding the specified import lines
        with open(owl_file, "w") as file:
            for line in lines:
                if not line.startswith("Import"):
                    file.write(line)

        logging.info(f"Successfully removed specified import lines from {owl_file}")

    except Exception as e:
        logging.error(f"Error removing import lines from {owl_file}: {e}")


def owl2obo(owl_file: str):
    """
    Convert OWL file to OBO format.

    :param owl_file: Path to the OWL file.
    """
    remove_import_lines(owl_file)
    obo_file = str(owl_file).replace(".owl", ".obo")
    catalog_file = PROJECT_DIR / "catalog-v001.xml"
    command = (
        f"robot remove --catalog {catalog_file} -i {owl_file} "
        '--select "imports" --trim false convert --check false '
        f"-o {obo_file}"
    )

    try:
        command_list = shlex.split(command)
        result = subprocess.run(command_list, capture_output=True, text=True)
        # Check if the command was successful
        if result.returncode == 0:
            logging.info(f"ROBOT command succeeded: {result.stdout}")
        else:
            if "INVALID ONTOLOGY FILE ERROR" in result.stdout:
                return 0  # Skip this file and move to the next iteration
            else:
                raise RuntimeError(f"ROBOT command failed: {result.stdout}")

    except Exception as e:
        raise RuntimeError(f"Error converting OWL to OBO: {e}") from e

def download_file(url, file_path, g):
     while True:
        try:
            if g:
                # Check rate limit and sleep if necessary
                remaining, reset_timestamp, current_timestamp = check_rate_limit(g)
                if remaining < 10:
                    sleep_time = max(0, reset_timestamp - current_timestamp + 10)  # Add buffer time
                    logging.info(f"Rate limit low. Sleeping for {sleep_time} seconds.")
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.72)  # Sleep to avoid hitting rate limit

            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            with open(file_path, "wb") as file:
                file.write(response.content)
            break  # Exit the loop if download is successful
        except requests.exceptions.ReadTimeout:
            logging.warning(f"ReadTimeout occurred. Retrying in {RETRY_DELAY // 60} minutes...")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException: {e}")
            break  # Exit the loop on other request exceptions
