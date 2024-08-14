# -----------------------------------------------------------------------------
# Makefile for Scraping Repositories
#
# This Makefile allows you to run scrapes on individual repositories as well as
# all repositories cumulatively. The list of repositories is defined in the 
# REPOS variable.
#
# Usage:
#   - To scrape all repositories: 
#       make scrape
#       or
#       make all
#
#   - To scrape an individual repository, use:
#       make <repo>
#     Example:
#       make monarch-initiative/mondo
#       make geneontology/go-ontology
#
# Variables:
#   GITHUB_ACCESS_TOKEN - Your GitHub access token for authentication.
#
# Targets:
#   - all: Default target to scrape all repositories.
#   - scrape: Phony target to scrape all repositories (alias for 'all').
#   - Individual repository targets: Each repository in REPOS has its own target.
#
# Notes:
#   - The .PHONY directive is used to declare non-file targets to avoid conflicts
#     with files of the same name.
# -----------------------------------------------------------------------------

# List of repositories
REPOS := monarch-initiative/mondo \
		 geneontology/go-ontology \
		 EnvironmentOntology/envo \
		 obophenotype/cell-ontology \
		 obophenotype/uberon \
		 pato-ontology/pato

# Default target to scrape all repositories
all: $(REPOS)

# Target to scrape individual repositories
$(REPOS):
	@echo "Starting scrape for repo $@..."
	@time curate scrape --repo $@ --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1
	@echo "Scrape completed for repo $@."

# Phony target to scrape all repositories cumulatively
scrape: all

.PHONY: all scrape $(REPOS)
