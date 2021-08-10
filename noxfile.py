from __future__ import annotations

import nox

ALL_PYTHONS = ["3.6", "3.7", "3.8", "3.9"]

nox.options.sessions = ["lint", "tests"]


@nox.session
def lint(session):
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(python=ALL_PYTHONS, reuse_venv=True)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install(".[test,boost,root]")
    session.run("pytest", "-s", *session.posargs)


@nox.session
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")
