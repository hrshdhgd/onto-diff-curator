"""Command line interface for onto-diff-curator."""

import logging
from pathlib import Path
from typing import Union

import click

from onto_diff_curator import __version__
from onto_diff_curator.main import analyze_repo, scrape_repo

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
    "-g",
    "--token",
    help="Github token for the repository.",
)
output_option = click.option("-o", "--output-file", help="Path to the output YAML file.")


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """
    CLI for onto-diff-curator.

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
def scrape(repo: str, token: str, output_file: Union[Path, str]):
    """Run the onto-diff-curator's scrape command."""
    scrape_repo(repo, token, output_file)


@main.command()
@repo_option
@output_option
def analyze(repo: str, output_file: Union[Path, str]):
    """Run the onto-diff-curator's analyze command."""
    analyze_repo(repo, output_file)


if __name__ == "__main__":
    main()
