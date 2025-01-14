# Development

This project uses [`poetry`](https://python-poetry.org/). To setup a development environment, run:

```bash
poetry lock
poetry install
```

### Testing 

To run all standard unit tests, run:

```bash
poetry run pytest
```

To run all example snippets in `invariant/examples/` as unit tests, run:

```bash
poetry run python -m unittest discover -s invariant/analyzer/examples -p "*_example.py"
```

### Dependency Management and Extras

Due to the nature of the analyzer and the included checkers in the standard library, not all dependencies are specified as direct dependency in `pyproject.toml`'s main `[project]` section. Instead, for dependencies that are not required for the core functionality of the analyzer, we use runtime dependency resolution, as implemented by the class `Extra` in `invariant/extras.py`.

For instance, a module that relies on `presidio-analyzer`, can import it using the following code:

```python
# add an `Extra` declaration to extras.py describing the optional feature
presidio_extra = Extra("PII and Secrets Scanning (using Presidio)", "Enables the detection of personally identifiable information (PII) and secret scanning in text", {
    "presidio_analyzer": ExtrasImport("presidio_analyzer", "presidio-analyzer", ">=2.2.354"),
    "spacy": ExtrasImport("spacy", "spacy", ">=3.7.5")
})

# then import a component from the `presidio_analyzer` package, via the `presidio_extra` extra
AnalyzerEngine = presidio_extra.package("presidio_analyzer").import_names('AnalyzerEngine')
```


This way, the analyzer can operate without many of the extra dependencies, but as soon as a feature that requires an `Extra` dependency is used (e.g. the code above runs), it will prompt the user to install the required dependencies, with the option to automatically install them using `pip`.

To learn more about all available extras, you can run the `invariant-cli list` command after installing the analyzer. This gives you a list of all available extras and their descriptions. If you want to install an extra already before the first use, you can use `invariant-cli add <extra>` to install any `Extra` ahead of time.

**Testing** If you need to write tests that require extra dependencies to be installed, you can declare the relevant `test_*` methods using the following decorator:

```python
from invariant.analyzer.extras import extras_available, presidio_extra

class TestSomething:
    @unittest.skipUnless(extras_available(presidio_extra), "presidio-analyzer is not installed")
    def test_presidio_analyzer(self):
        ...
```

This way, all relevant tests will be skipped if the required dependencies are not installed, allowing us to test setups with and without the extra dependencies in place.

For convenience, all extra dependencies are also specified as a dev dependency in `pyproject.toml`'s `[tool.rye.dev-dependencies]` section, so that they are automatically installed when running `rye sync`. This way, during development, all extra dependencies will always be installed, even though testing without them is recommended. If you want to test a setup without any extra dependencies, you can simply run `rye sync --no-dev` to install only the core dependency set.
