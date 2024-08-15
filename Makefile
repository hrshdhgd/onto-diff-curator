# -----------------------------------------------------------------------------
# Makefile for Scraping and Analyzing Repositories
#
# This Makefile allows you to run scrapes and analyses on individual repositories 
# as well as all repositories cumulatively. The list of repositories is defined 
# in the REPOS, OBO_REPOS, and OWL_REPOS variables.
#
# Usage:
#   - To scrape all repositories: 
#       make scrape
#       or
#       make scrape-all
#
#   - To scrape an individual repository, use:
#       make <repo>
#     Example:
#       make monarch-initiative/mondo
#       make geneontology/go-ontology
#
#   - To analyze OBO repositories:
#       make analyze-obo
#
#   - To analyze OWL repositories:
#       make analyze-owl
#
#   - To analyze all repositories:
#       make analyze-all
#
# Variables:
#   GITHUB_ACCESS_TOKEN - Your GitHub access token for authentication.
#
# Targets:
#   - scrape-all: Default target to scrape all repositories.
#   - scrape: Phony target to scrape all repositories (alias for 'scrape-all').
#   - Individual repository targets: Each repository in REPOS has its own target.
#   - analyze-obo: Target to analyze all OBO repositories.
#   - analyze-owl: Target to analyze all OWL repositories.
#   - analyze-all: Target to analyze all repositories.
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

OBO_REPOS := pato-ontology/pato \
			 obophenotype/uberon \
			 geneontology/go-ontology \
			 monarch-initiative/mondo

OWL_REPOS := obophenotype/cell-ontology \
			 EnvironmentOntology/envo

# Default target to scrape all repositories
scrape-all: $(REPOS)

# Target to scrape individual repositories
$(REPOS):
	@echo "Starting scrape for repo $@..."
	@time ontodiff scrape --repo $@ --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1
	@echo "Scrape completed for repo $@."

# Phony target to scrape all repositories cumulatively
scrape: scrape-all

# Target to analyze OBO repositories
analyze-obo: $(OBO_REPOS)

# Target to analyze individual OBO repositories
$(OBO_REPOS):
	@echo "Starting analysis for repo $@..."
	@time ontodiff analyze --repo $@
	@echo "Analysis completed for repo $@."

# Target to analyze OWL repositories
analyze-owl: $(OWL_REPOS)

# Target to analyze individual OWL repositories
$(OWL_REPOS):
	@echo "Starting analysis for repo $@..."
	@time ontodiff analyze --repo $@
	@echo "Analysis completed for repo $@."

# Target to analyze all repositories
analyze-all: analyze-obo analyze-owl

.PHONY: scrape-all scrape $(REPOS) analyze-obo analyze-owl analyze-all $(OBO_REPOS) $(OWL_REPOS)
