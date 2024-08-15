# onto-diff-curator

Curates differences in ontology resources during pull requests in KGCL format using [oaklib](https://github.com/INCATools/ontology-access-kit).

Currently curates diff for the following:
 - monarch-initiative/mondo
 - geneontology/go-ontology
 - EnvironmentOntology/envo
 - obophenotype/cell-ontology
 - obophenotype/uberon
 - pato-ontology/pato

## Setup

Currently just clone the git repo and proceed.
```shell
pip install poetry
git clone https://github.com/hrshdhgd/onto-diff-curator
cd onto-diff-curator
poetry install
```

## Scrape the repository

> **:warning:** You'll need a GitHub token stored as any environment variable name (`GITHUB_ACCESS_TOKEN` in this case).

```shell
ontodiff scrape --repository monarch-initiative/mondo --token $(GITHUB_ACCESS_TOKEN)
```

This grabs the information of all pull requests in the MONDO repository that change the `mondo-edit.obo` file & have an associated issue(s) that they close. The output is stored as `data.yaml`

```shell
ontodiff analyze --repository monarch-initiative/mondo
```

This grabs the resource (mondo-edit.obo) in the branch associated with the pull request and the `main` branch at the time and compares the two using `oaklib` and generates the difference between them in KGCL format. The output si another YAML file (`rag_input.yaml`) 



---
### Acknowledgements

This [cookiecutter](https://cookiecutter.readthedocs.io/en/stable/README.html) project was developed from the [monarch-project-template](https://github.com/monarch-initiative/monarch-project-template) template and will be kept up-to-date using [cruft](https://cruft.github.io/cruft/).
