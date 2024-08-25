"""Main module for the OntoDiffCurator package."""

import datetime
import io
import logging
import shutil
import time
from os import makedirs
from pathlib import Path
from typing import Union

import requests
import requests_cache
import yaml
from github import Github, RateLimitExceededException
from oaklib import get_adapter
from oaklib.io.streaming_kgcl_writer import StreamingKGCLWriter

from ontodiff_curator.constants import (
    CHANGED_FILES_KEY,
    CHANGES_KEY,
    FILENAME_KEY,
    ISSUE_BODY_KEY,
    ISSUE_COMMENTS_KEY,
    ISSUE_LABELS_KEY,
    ISSUE_NUMBER_KEY,
    ISSUE_TITLE_KEY,
    PR_BODY_KEY,
    PR_CHANGED_FILES_KEY,
    PR_CLOSED_ISSUES_KEY,
    PR_COMMENTS_KEY,
    PR_LABELS_KEY,
    PR_NUMBER_KEY,
    PR_TITLE_KEY,
    PULL_REQUESTS_KEY,
    URL_IN_MAIN_KEY,
    URL_IN_PR_KEY,
)
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


def scrape_repo(
    repo: str,
    token: str,
    output_file: Union[Path, str],
    max_pr_number=None,
    min_pr_number=None,
    pr_status="merged",
    overwrite: bool = True,
) -> None:
    """
    Get pull requests and corresponding issues they close along with the ontology resource files.

    We collect the URLs of the resource files in the PR and also the main branch just before the PR was merged.

    :param repo: Org/name of the GitHub repo.
    :param token: GitHub token for the repository.
    :param output_file: Path to the output YAML file.
    """
    logging.info(f"Starting scrape for repo: {repo}")
    g = Github(token)
    file_of_interest = REPO_RESOURCE_MAP.get(repo)
    repository = g.get_repo(repo)
    first_line_written = False

    # Set default output file path if not provided
    if not output_file:
        output_file = Path.cwd() / f"{repo.replace('/', '_')}/{RAW_DATA_FILENAME}"
        if output_file.exists() and overwrite:
            output_file.unlink()

    # Create directories if they do not exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Get closed pull requests
    pull_requests = repository.get_pulls(state=pr_status)

    # Filter pull requests based on the PR number
    if max_pr_number:
        pull_requests = [pr for pr in pull_requests if pr.number <= max_pr_number]
    if min_pr_number:
        pull_requests = [pr for pr in pull_requests if pr.number >= min_pr_number]

    for pr in pull_requests:
        merge_url = f"https://api.github.com/repos/{repo}/pulls/{pr.number}/merge"
        merge_response = requests.get(merge_url, timeout=10, headers={"Authorization": f"token {token}"})
        if merge_response.status_code == 204:
            try:
                # Initialize data structure for the pull request
                pr_entry = {
                    PR_NUMBER_KEY: f"pr{pr.number}",
                    PR_TITLE_KEY: pr.title,
                    PR_BODY_KEY: pr.body,
                    PR_LABELS_KEY: [label.name for label in pr.labels],
                    PR_COMMENTS_KEY: [comment.body for comment in pr.get_comments()],
                    PR_CLOSED_ISSUES_KEY: [],
                    PR_CHANGED_FILES_KEY: [],
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
                                ISSUE_NUMBER_KEY: issue.number,
                                ISSUE_TITLE_KEY: issue.title,
                                ISSUE_BODY_KEY: issue.body,
                                ISSUE_LABELS_KEY: [label.name for label in issue.labels],
                                ISSUE_COMMENTS_KEY: [comment.body for comment in issue.get_comments()],
                            }

                            pr_entry[PR_CLOSED_ISSUES_KEY].append(issue_data)

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
                                FILENAME_KEY: file.filename,
                                URL_IN_MAIN_KEY: url_on_main,
                                URL_IN_PR_KEY: url_in_pr,
                            }
                            pr_entry[PR_CHANGED_FILES_KEY].append(file_data)

                        # Write data to YAML file if conditions are met
                        if len(pr_entry[PR_CHANGED_FILES_KEY]) > 0 and len(pr_entry[PR_CLOSED_ISSUES_KEY]) > 0:
                            if not first_line_written:
                                with open(output_file, "a") as file:
                                    yaml.dump({PULL_REQUESTS_KEY: [pr_entry]}, file)
                                first_line_written = True
                            else:
                                with open(output_file, "a") as file:
                                    yaml.dump([pr_entry], file, default_flow_style=False, indent=2)
                            logging.info(f"Data for PR #{pr.number} written to {output_file}")
                else:
                    logging.info(f"No issues linked to PR #{pr.number}")

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


def analyze_repo(repo: str, token: str, output_file: str, overwrite: bool = True) -> None:
    """
    Structure the pull request data and analyze the changes in the ontology files.

    :param repo: Org/name of the GitHub repo.
    :param output_file: Path to the output YAML file.
    """
    g = Github(token)
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

    if output_file.exists():
        if overwrite:
            Path(output_file).unlink()
            mode = "w"
            first_change_found = False
        else:
            pr_numbers_scraped = {int(pr[PR_NUMBER_KEY].strip("pr")) for pr in data[PULL_REQUESTS_KEY]}
            with open(output_file, "r") as of:
                analyzed_data = yaml.safe_load(of)
            pr_numbers_analyzed = {int(pr[PR_NUMBER_KEY].strip("pr")) for pr in analyzed_data[PULL_REQUESTS_KEY]}
            if pr_numbers_scraped == pr_numbers_analyzed:
                logging.info(f"All data already analyzed for repo: {repo}")
                return
            pr_remaining = pr_numbers_scraped - pr_numbers_analyzed
            mode = "a"
            first_change_found = True
    else:
        mode = "a"
        first_change_found = True
        
    # Analyze data
    with open(output_file, mode) as of:
        if overwrite:
            yaml.dump(metadata, of)
            list_of_dicts = data[PULL_REQUESTS_KEY]
        else:
            list_of_dicts = [d for d in data[PULL_REQUESTS_KEY] if int(d[PR_NUMBER_KEY].strip("pr")) in pr_remaining]

        for dictionary in list_of_dicts:
            url_in_pr = dictionary[PR_CHANGED_FILES_KEY][0][URL_IN_PR_KEY]
            url_on_main = dictionary[PR_CHANGED_FILES_KEY][0][URL_IN_MAIN_KEY]
            extension = url_in_pr.split(".")[-1]

            new_file_path = TMP_DIR / f"new.{extension}"
            old_file_path = TMP_DIR / f"old.{extension}"

            # Download the files
            # 1. Download the file from the PR and name it new.obo/new.owl
            download_file(url_in_pr, new_file_path, g, token)

            # 2. Download the file from the main branch and name it old.obo/old.owl
            download_file(url_on_main, old_file_path, g, token)

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
            output_dict = {key: value for key, value in dictionary.items() if key != PR_CHANGED_FILES_KEY}
            output_dict[CHANGES_KEY] = all_changes
            if len(output_dict[CHANGES_KEY]) > 0:
                if not first_change_found:
                    yaml.dump({PULL_REQUESTS_KEY: [output_dict]}, of)
                    first_change_found = True
                else:
                    yaml.dump([output_dict], of, default_flow_style=False, indent=2)

            # delete new and old files
            shutil.rmtree(TMP_DIR)
            makedirs(TMP_DIR, exist_ok=True)

    logging.info(f"Analysis completed for repo: {repo}")
