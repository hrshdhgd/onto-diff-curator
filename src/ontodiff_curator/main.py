"""Main module for the OntoDiffCurator package."""

import datetime
import io
import logging
import os
import shutil
import time
from os import makedirs
from pathlib import Path
from typing import Union

import requests_cache
import yaml
from github import Github, RateLimitExceededException
from oaklib import get_adapter
from oaklib.io.streaming_kgcl_writer import StreamingKGCLWriter

from ontodiff_curator.utils import PROJECT_DIR, check_rate_limit, download_file, owl2obo

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize requests_cache
requests_cache.install_cache("github_cache")

REPO_RESOURCE_MAP = {
    "monarch-initiative/mondo": "mondo-edit.obo",
    "pato-ontology/pato": "pato-edit.obo",
    "EnvironmentOntology/envo": "envo-edit.owl",
    "obophenotype/uberon": "uberon-edit.obo",
    "obophenotype/cell-ontology": "cl-edit.owl",
    "geneontology/go-ontology": "go-edit.obo",
}
RAW_DATA_FILENAME = "raw_data.yaml"
DATA_WITH_CHANGES_FILENAME = "data_with_changes.yaml"
TMP_DIR_NAME = "tmp"


def scrape_repo(repo: str, token: str, output_file: Union[Path, str], max_pr_number = None, min_pr_number = None, overwrite:bool = True) -> None:
    """
    Get pull requests and corresponding issues they close along with the ontology resource files.

    We collect the URLs of the resource files in the PR and also the main branch just before the PR was merged.

    :param repo: Org/name of the GitHub repo.
    :param token: GitHub token for the repository.
    :param output_file: Path to the output YAML file.
    """
    logging.info(f"Starting scrape for repo: {repo}")
    if token:
        g = Github(token)
    else:
        g = None
    file_of_interest = REPO_RESOURCE_MAP.get(repo)
    repository = g.get_repo(repo)

    # Set default output file path if not provided
    if not output_file:
        output_file = Path.cwd() / f"{repo.replace('/', '_')}/{RAW_DATA_FILENAME}"
        if output_file.exists() and overwrite:
            output_file.unlink()

    # Create directories if they do not exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Get closed pull requests
    pull_requests = repository.get_pulls(state="closed")

    # Filter pull requests based on the PR number
    if max_pr_number:
        pull_requests = [pr for pr in pull_requests if pr.number <= max_pr_number]
    if min_pr_number:
        pull_requests = [pr for pr in pull_requests if pr.number >= min_pr_number]

    for pr in pull_requests:
        try:
            # Initialize data structure for the pull request
            pr_data = {
                f"pull_request_{pr.number}": {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "labels": [label.name for label in pr.labels],
                    "comments": [comment.body for comment in pr.get_comments()],
                    "issue_closed": [],
                    "changed_files": [],
                }
            }

            # Get issues linked to the pull request
            if pr.body:
                issue_numbers = [
                    int(word[1:]) for word in pr.body.split() if word.startswith("#") and word[1:].isdigit()
                ]
                for issue_number in issue_numbers:
                    issue = repository.get_issue(issue_number)
                    if not issue.pull_request:
                        # Collect issue data
                        issue_data = {
                            "number": issue.number,
                            "title": issue.title,
                            "body": issue.body,
                            "labels": [label.name for label in issue.labels],
                            "comments": [comment.body for comment in issue.get_comments()],
                        }
                        pr_data[f"pull_request_{pr.number}"]["issue_closed"].append(issue_data)

                # Get changed files in the PR
                files = pr.get_files()
                for file in files:
                    if file.filename.endswith(f"/{file_of_interest}"):
                        # Get the commit SHA of the main branch just before the PR was merged
                        base_commit_sha = pr.base.sha
                        head_commit_sha = pr.head.sha

                        # Construct URLs
                        url_on_main = f"https://github.com/{repo}/raw/{base_commit_sha}/{file.filename}"
                        url_in_pr = f"https://github.com/{repo}/raw/{head_commit_sha}/{file.filename}"

                        # Collect file data
                        file_data = {
                            "filename": file.filename,
                            "url_on_main": url_on_main,
                            "url_in_pr": url_in_pr,
                        }
                        pr_data[f"pull_request_{pr.number}"]["changed_files"].append(file_data)

                # Write data to YAML file if conditions are met
                if (
                    pr_data[f"pull_request_{pr.number}"]["changed_files"]
                    and pr_data[f"pull_request_{pr.number}"]["issue_closed"]
                ):
                    with open(output_file, "a") as file:
                        yaml.dump(pr_data, file)
                    logging.info(f"Data for PR #{pr.number} written to {output_file}")
            else:
                logging.warning(f"No issues linked to PR #{pr.number}")

            if g:
                # Check rate limit and sleep if necessary
                remaining, reset_timestamp, current_timestamp = check_rate_limit(g)
                if remaining < 10:
                    sleep_time = max(0, reset_timestamp - current_timestamp + 10)  # Add buffer time
                    logging.info(f"Rate limit low. Sleeping for {sleep_time} seconds.")
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.72)  # Sleep to avoid hitting rate limit

        except RateLimitExceededException:
            logging.error("Rate limit exceeded. Sleeping for 60 seconds.")
            time.sleep(60)
            continue  # Retry after sleeping
        except Exception as e:
            logging.error(f"Failed to fetch issue or files for PR #{pr.number}: {e}")

    logging.info(f"Scrape completed for repo: {repo}")


def analyze_repo(repo: str, token:str, output_file: str, overwrite: bool = True) -> None:
    """
    Structure the pull request data and analyze the changes in the ontology files.

    :param repo: Org/name of the GitHub repo.
    :param output_file: Path to the output YAML file.
    """
    if token:
        g = Github(token)
    else:
        g = None
    DATA_PATH = PROJECT_DIR / f"{repo.replace('/', '_')}/{RAW_DATA_FILENAME}"
    TMP_DIR = PROJECT_DIR / f"{repo.replace('/', '_')}" / TMP_DIR_NAME
    makedirs(TMP_DIR, exist_ok=True)
    with open(DATA_PATH, "r") as file:
        data = yaml.safe_load(file)
    logging.info(f"Analyzing data for repo: {repo}")

    if not output_file:
        output_file = PROJECT_DIR / f"{repo.replace('/', '_')}/{DATA_WITH_CHANGES_FILENAME}"

    # Write metadata to the output file
    metadata = {
        "date_executed": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "code_version": "0.0.1",  # Replace with actual version if available
        "github_url": f"https://github.com/{repo}",
    }
    if output_file.exists() and overwrite:
        Path(output_file).unlink()
        mode = "w"
    else:
        mode = "a"

    # Analyze data
    with open(output_file, mode) as of:
        if overwrite:
            yaml.dump(metadata, of)
        for pr_number, content in data.items():
            url_in_pr = content["changed_files"][0]["url_in_pr"]
            url_on_main = content["changed_files"][0]["url_on_main"]
            extension = url_in_pr.split(".")[-1]
            new_file_path = TMP_DIR / f"new.{extension}"
            old_file_path = TMP_DIR / f"old.{extension}"

            # Download the files
            # 1. Download the file from the PR and name it new.obo/new.owl
            download_file(url_in_pr, new_file_path, g)

            # 2. Download the file from the main branch and name it old.obo/old.owl
            download_file(url_on_main, old_file_path, g)

            # 3. Run the diff command
            if extension == "owl":
                n = owl2obo(new_file_path)
                o = owl2obo(old_file_path)
                if n == 0 or o == 0:
                    continue
                old_file_path = old_file_path.with_suffix(".obo")
                new_file_path = new_file_path.with_suffix(".obo")
            try:
                adapter_new = get_adapter(f"simpleobo:{new_file_path}")
                adapter_old = get_adapter(f"simpleobo:{old_file_path}")
            except (ValueError, FileNotFoundError) as e:
                logging.error(f"ValueError: {e}")
                continue  # Skip this file and move to the next iteration
            except Exception as e:
                raise e
                # logging.error(f"Error: {e}")
                # continue  # Skip this file and move to the next iteration

            all_changes = []
            # Create an in-memory file-like object and use it within a 'with' statement
            with io.StringIO() as output:
                # Instantiate StreamingKGCLWriter with the in-memory file-like object
                writer = StreamingKGCLWriter(ontology_interface=adapter_old, file=output)

                # Emit all changes
                for change in adapter_old.diff(adapter_new):
                    writer.emit(change)

                # Capture the content written to the in-memory file-like object
                all_changes = output.getvalue().splitlines()
            # Create a new YAML file with the changes
            output_dict = {
                pr_number: {
                    "title": content["title"],
                    "body": content["body"],
                    "labels": content["labels"],
                    "comments": content["comments"],
                    "issue_closed": content["issue_closed"],
                    "changes": all_changes,
                }
            }
            yaml.dump(output_dict, of)
            # delete new and old files
            shutil.rmtree(TMP_DIR)
            makedirs(TMP_DIR, exist_ok=True)

    logging.info(f"Analysis completed for repo: {repo}")
