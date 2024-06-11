"""
Invariant CLI tool.
"""

from .extras import Extra
import os
import termcolor
import sys
import subprocess
import re

from . import __version__

def shortname(name):
    name = name.lower()
    # replace " " with "-" and all non-alphanumeric characters with ""
    name = re.sub(r"[^a-z0-9-]", "", name.replace(" ", "-"))
    return name

def list_extras(*args):
    print("Invariant Version:", __version__)
    print("\nThe following extra features can be enabled by installing additional dependencies:")
    extras = Extra.find_all()
    print("\r", end="")

    for extra in extras:
        print("\r" + " " * 80, end="")
        short = shortname(extra.name)
        termcolor.cprint("\n- " + extra.name + " [" + short + "]", "green")
        print("  Required Packages: ")
        for imp in extra.packages.values():
            print("   - " + imp.package_name + imp.version_constraint)
        print("\n  " + extra.description)
    print()

def prompt(question):
    response = input(question + " [y/N] ").strip()
    return response.lower() == "y" or len(response) == 0

def cmd():
    return os.path.basename(sys.argv[0])

def add_extra(*extras):
    if len(extras) == 0:
        print("USAGE:", cmd(), "add [extra1] [extra2] ... [-y] [-r]")
        print("""
[extra1] [extra2] ...: The extras to install, use 'all' to install all extras.
-y: Do not ask for confirmation.
-r: Print the list of packages to install.
              
Examples:
    <cli> add all
    <cli> add extra1 extra2
    <cli> add extra1 extra2 -y
        """)
        sys.exit(1)
    
    to_install = set()
    extras = set(extras)
    
    noask = "-y" in extras
    install_all = 'all' in extras
    print_r_file = "-r" in extras
    extras = extras - {"-y", "all", "-r"}

    all_extras = Extra.find_all()
    print("\r", end="")

    for extra in all_extras:
        name = shortname(extra.name)
        if name in extras or install_all:
            for pd in extra.packages.values():
                to_install.add(pd.package_name + pd.version_constraint)
                extras = extras - {name}

    if len(extras) > 0:
        print("Unknown extras:", ", ".join(extras))
        sys.exit(1)

    if print_r_file:
        print("\n".join([pd for pd in to_install]))
        sys.exit(0)

    print("Installing the following packages:")
    print("\n".join(["- " + pd for pd in to_install]))
    
    if prompt("Do you want to continue?") or noask:
        # make sure 'pip' is installed
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True)
        if result.returncode != 0:
            print("Error: pip is not installed. If you are not using 'pip', please be sure to install the packages listed above manually.")
            sys.exit(1)

        subprocess.run([sys.executable, "-m", "pip", "install"] + [pd for pd in to_install])

def main():
    args = sys.argv[1:]
    
    commands = {
        "list": list_extras,
        "add": add_extra
    }

    if len(args) == 0:
        print("Usage: invariant-extra " + "|".join(commands.keys()) + " [args]")
        sys.exit(1)

    if args[0] in commands:
        commands[args[0]](*args[1:])
    else:
        print("Unknown command:", args[0])
        sys.exit(1)

if __name__ == "__main__":
    main()