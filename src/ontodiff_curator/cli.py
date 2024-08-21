"""Command line interface for ontodiff-curator."""

import logging
from pathlib import Path
from typing import Union

import click

from ontodiff_curator import __version__
from ontodiff_curator.main import analyze_repo, scrape_repo

__all__ = [
    "main",
]

logger = logging.getLogger(__name__)

repo_option = click.option(
    "-r",
    "--repo",
    required=True,
    help="Org/name of the github repo.",
)
token_option = click.option(
    "-t",
    "--token",
    required=False,
    help="Github token for the repository.",
)
output_option = click.option("-o", "--output-file", help="Path to the output YAML file.")
max_pr_option = click.option("--max-pr", type=int, default=None, help="Latest PR to scrape.")
min_pr_option = click.option("--min-pr", type=int, default=None, help="Earliest PR to scrape.")
overwrite_option = click.option("--overwrite/--no-overwrite", default=True, help="Enable or disable overwriting.")
from_pr_option = click.option("--from-pr", type=int, default=None, help="Earliest PR to analyze.")
pr_status_option = click.option(
    "--pr-status",
    type=click.Choice(["open", "closed"], case_sensitive=False),
    default="closed",
    help="Status of the PRs to scrape.",
)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """
    CLI for ontodiff-curator.

    :param verbose: Verbosity while running.
    :param quiet: Boolean to be quiet or verbose.
    """
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


@main.command()
@repo_option
@token_option
@output_option
@max_pr_option
@min_pr_option
@pr_status_option
@overwrite_option
def scrape(
    repo: str, token: str, output_file: Union[Path, str], max_pr: int, min_pr: int, pr_status: str, overwrite: bool
):
    """Run the ontodiff-curator's scrape command."""
    scrape_repo(repo, token, output_file, max_pr, min_pr, pr_status, overwrite)


@main.command()
@repo_option
@token_option
@output_option
@from_pr_option
@overwrite_option
def analyze(repo: str, token: str, output_file: Union[Path, str], from_pr: int, overwrite: bool):
    """Run the ontodiff-curator's analyze command."""
    analyze_repo(repo, token, output_file, from_pr, overwrite)


if __name__ == "__main__":
    main()
