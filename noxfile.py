from __future__ import annotations

import nox

nox.needs_version = ">=2025.02.09"
nox.options.default_venv_backend = "uv|virtualenv"

PYPROJECT = nox.project.load_toml("pyproject.toml")
PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)


@nox.session
def lint(session):
    """
    Run the linter.
    """
    session.install("prek")
    session.run("prek", "run", "--all-files", *session.posargs)


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install("-e.[boost,uproot,rich]", "--group=test")
    session.run("pytest", "-s", *session.posargs)


@nox.session(default=False)
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")
