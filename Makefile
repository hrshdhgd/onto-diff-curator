# This Makefile provides commands to scrape and analyze multiple repositories.
#
# Available Commands:
# 
# 1. make scrape
#    - Scrapes all listed repositories.
#
# 2. make analyze
#    - Analyzes all listed repositories.
#
# 3. make <repository-name>-scrape
#    - Scrapes a specific repository. Replace <repository-name> with the actual name, e.g., monarch-initiative/mondo-scrape.
#
# 4. make <repository-name>-analyze
#    - Analyzes a specific repository. Replace <repository-name> with the actual name, e.g., monarch-initiative/mondo-analyze.
#
# 5. make scrapalyze REPO=<repository-name>
#    - Scrapes and then analyzes a specific repository. Replace <repository-name> with the actual name, e.g., REPO=monarch-initiative/mondo.
#
# List of Repositories:
# - monarch-initiative/mondo
# - geneontology/go-ontology
# - EnvironmentOntology/envo
# - obophenotype/cell-ontology
# - obophenotype/uberon
# - pato-ontology/pato

# List of repositories
REPOS := \
	monarch-initiative/mondo \
	geneontology/go-ontology \
	EnvironmentOntology/envo \
	obophenotype/cell-ontology \
	obophenotype/uberon \
	pato-ontology/pato

# Target to scrape individual repositories
.PHONY: $(addsuffix -scrape, $(REPOS))
$(addsuffix -scrape, $(REPOS)):
	@repo=$(subst -scrape,,$@); \
	echo "Starting scrape for repo $$repo..."; \
	time ontodiff scrape --repo $$repo --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1; \
	echo "Scrape completed for repo $$repo."

# Phony target to scrape all repositories cumulatively
.PHONY: scrape-all
scrape-all: $(addsuffix -scrape, $(REPOS))

# Phony target to scrape all repositories using 'scrape-all'
.PHONY: scrape
scrape: scrape-all

# Target to analyze individual repositories
.PHONY: $(addsuffix -analyze, $(REPOS))
$(addsuffix -analyze, $(REPOS)):
	@repo=$(subst -analyze,,$@); \
	echo "Starting analysis for repo $$repo..."; \
	time ontodiff analyze --repo $$repo --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1; \
	echo "Analysis completed for repo $$repo."

# Phony target to analyze all repositories cumulatively
.PHONY: analyze-all
analyze-all: $(addsuffix -analyze, $(REPOS))

# Phony target to analyze all repositories using 'analyze-all'
.PHONY: analyze
analyze: analyze-all

# Phony target to scrape and then analyze a specific repository
.PHONY: scrapalyze
scrapalyze:
	@echo "Starting scrape and analyze for repo $(REPO)..."
	@time ontodiff scrape --repo $(REPO) --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1
	@echo "Scrape completed for repo $(REPO)."
	@time ontodiff analyze --repo $(REPO) --token $(GITHUB_ACCESS_TOKEN) > /dev/null 2>&1
	@echo "Analyze completed for repo $(REPO)."
