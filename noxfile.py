import nox


@nox.session
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session):
    session.install("pyright")
    session.install("-e", ".[dev]")
    session.run("pyright")
