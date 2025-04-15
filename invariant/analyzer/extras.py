"""
Optional dependency management for Invariant.
"""

import sys

TERMINATE_ON_EXTRA_FAILURE = True


def set_extras_strategy(terminate_on_extra_failure: bool):
    """
    Set the strategy for handling missing extras.

    Args:
        terminate_on_extra_failure (bool): If True, the program will terminate if an extra is not available.
    """
    global TERMINATE_ON_EXTRA_FAILURE
    TERMINATE_ON_EXTRA_FAILURE = terminate_on_extra_failure


class ExtrasImport:
    """
    An extras import is a dynamic import that comes with information about the
    required package and corresponding version constraint.

    If the package is installed, the module is imported as usual. If the package
    is not installed, the wrapping 'Extra' feature group, can take the necessary
    steps to install the additional dependencies, if the user agrees.
    """

    def __init__(self, import_name, package_name, version_constraint):
        """Creates a new ExtrasImport object.

        Args:
            import_name (str): The name or specifier of the module to import (e.g. 'lib' or 'lib.submodule')
            package_name (str): The name of the pypi package that contains the module.
            version_constraint (str): The version constraint for the package (e.g. '>=1.0.0')
        """
        self.name = import_name
        self.package_name = package_name
        self.version_constraint = version_constraint

        # collection of sites where this dependency is used
        # (only available if find_all is used)
        self.sites = []

    def import_names(self, *specifiers):
        """
        Import specific names from the module, e.g.

        ```[<spec1>, <spec2>] = ExtrasImport(<package_name>, ...).import_names(<spec1>, <spec2>)```

        is equivalent to

        ```
        from <package_name> import <specifier1>, <specifier2>, ...
        ```
        """
        module = self.import_module()
        elements = [getattr(module, specifier) for specifier in specifiers]
        if len(elements) == 1:
            return elements[0]
        return elements

    def import_module(self):
        """
        Import the module and return it.

        ```<package_name> = ExtrasImport(<package_name>, ...).import_module()```

        is equivalent to

        ```
        import <package_name>
        ```
        """
        module = __import__(self.name, fromlist=[self.name])
        return module

    def __str__(self):
        if len(self.sites) > 0:
            sites_str = f", sites={self.sites}"
        else:
            sites_str = ""
        return f"ExtrasImport('{self.name}', '{self.package_name}', '{self.version_constraint}'{sites_str})"

    def __repr__(self):
        return str(self)


class Extra:
    """
    An Extra is a group of optional dependencies that can be installed on demand.

    The extra is defined by a name, a description, and a collection of packages.

    For a list of available extras, see `Extra.find_all()` and below.
    """

    def __init__(self, name, description, packages):
        self.name = name
        self.description = description
        self.packages = packages
        self._is_available = None

        Extra.extras[name] = self

    def is_available(self) -> bool:
        """Returns whether the extra is available (all assigned imports can be resolved)."""
        if self._is_available is not None:
            return self._is_available

        for package in self.packages.values():
            try:
                __import__(package.name)
            except ImportError:
                self._is_available = False
                return False

        self._is_available = True
        return True

    def package(self, name) -> ExtrasImport:
        """Returns the package with the given name."""
        if not self.is_available():
            self.install()

        return self.packages[name]

    def install(self):
        """Installs all required packages for this extra (using pip if available)."""
        # like for imports, but all in one go
        msg = "warning: you are trying to use a feature that relies on the extra dependency '{}', which requires the following packages to be installed:\n".format(
            self.name
        )
        for imp in self.packages.values():
            msg += "   - " + imp.package_name + imp.version_constraint + "\n"

        sys.stderr.write(msg + "\n")

        # check if terminal input is possible
        if sys.stdin.isatty():
            sys.stderr.write("Press (y/enter) to install the packages or Ctrl+C to exit: ")
            answer = input()
            if answer == "y" or len(answer) == 0:
                import subprocess

                # check if 'pip' is installed
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"], capture_output=True
                )
                if result.returncode != 0:
                    sys.stderr.write(
                        "error: 'pip' is not installed. Please install the above mentioned packages manually.\n"
                    )
                    if TERMINATE_ON_EXTRA_FAILURE:
                        sys.exit(1)
                    else:
                        raise RuntimeError(
                            "policy execution failed due to missing dependencies in the runtime environment"
                        )
                for imp in self.packages.values():
                    subprocess.call(
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            f"{imp.package_name}{imp.version_constraint}",
                        ]
                    )
            else:
                if TERMINATE_ON_EXTRA_FAILURE:
                    sys.exit(1)
                else:
                    raise RuntimeError(
                        "policy execution failed due to missing dependencies in the runtime environment"
                    )
        else:
            if TERMINATE_ON_EXTRA_FAILURE:
                sys.exit(1)
            else:
                raise RuntimeError(
                    "policy execution failed due to missing dependencies in the runtime environment"
                )

    @staticmethod
    def find_all() -> list["Extra"]:
        return list(Extra.extras.values())


Extra.extras = {}

"""Extra for features that rely on the `transformers` library."""
transformers_extra = Extra(
    "Transformers",
    "Enables the use of 🤗 `transformer`-based models and classifiers in the analyzer",
    {
        "transformers": ExtrasImport("transformers", "transformers", ">=4.41.1"),
        "torch": ExtrasImport("torch", "torch", ">=2.3.0"),
    },
)

"""Extra for features that rely on the `openai` library."""
openai_extra = Extra(
    "OpenAI",
    "Enables the use of OpenAI's GPT-3 API for text analysis",
    {"openai": ExtrasImport("openai", "openai", ">=1.33.0")},
)

"""Extra for features that rely on the `presidio_analyzer` library."""
presidio_extra = Extra(
    "PII and Secrets Scanning (using Presidio)",
    "Enables the detection of personally identifiable information (PII) and secret scanning in text",
    {
        "presidio_analyzer": ExtrasImport("presidio_analyzer", "presidio-analyzer", ">=2.2.354"),
        "spacy": ExtrasImport("spacy", "spacy", ">=3.7.5"),
    },
)

"""Extra for features that rely on the `semgrep` library."""
semgrep_extra = Extra(
    "Code Scanning with Semgrep",
    "Enables the use of Semgrep for code scanning",
    {"semgrep": ExtrasImport("semgrep", "semgrep", ">=1.78.0")},
)

"""Extra for features that rely on the `langchain` library."""
langchain_extra = Extra(
    "langchain Integration",
    "Enables the use of Invariant's langchain integration",
    {"langchain": ExtrasImport("langchain", "langchain", ">=0.2.1")},
)


def extras_available(*extras: list[Extra]) -> bool:
    """Returns true if and only if all given extras are available."""
    for extra in extras:
        if not extra.is_available():
            return False
    return True
