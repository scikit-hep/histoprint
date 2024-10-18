from __future__ import annotations

import nox

nox.needs_version = ">=2024.4.15"
nox.options.default_venv_backend = "uv|virtualenv"

ALL_PYTHONS = [
    c.split()[-1]
    for c in nox.project.load_toml("pyproject.toml")["project"]["classifiers"]
    if c.startswith("Programming Language :: Python :: 3.")
]


@nox.session
def lint(session):
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(python=ALL_PYTHONS)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install(".[test,boost,uproot,rich]")
    session.run("pytest", "-s", *session.posargs)


@nox.session(default=False)
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")
