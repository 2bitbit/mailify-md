import sys
import tomlkit
import subprocess
from typing import Annotated
from typer import Argument, Typer
from pathlib import Path

PYPROJECT_TOML_PATH = Path(__file__).parent.parent / "pyproject.toml"
with PYPROJECT_TOML_PATH.open("r") as f:
    TOML_DATA = tomlkit.load(f)
CUR_VERSION: str = TOML_DATA["project"]["version"]  # type: ignore

app = Typer()


@app.command()
def update_version(
    part_to_bump: Annotated[str, Argument(help="The part of the version to bump: patch, minor, or major")],
):
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding="utf-8")
    if result.stdout.strip():
        print("存在未提交的更改，请先提交后再运行此脚本。", file=sys.stderr)
        sys.exit(1)

    lst = CUR_VERSION.split(".")
    match part_to_bump:
        case "patch":
            new_version = f"{lst[0]}.{lst[1]}.{int(lst[2]) + 1}"
        case "minor":
            new_version = f"{lst[0]}.{int(lst[1]) + 1}.0"
        case "major":
            new_version = f"{int(lst[0]) + 1}.0.0"
            
    def git_commit():
        subprocess.run(["git", "commit", "-m", f"bump version to v{new_version}"], check=True)

    def git_tag():
        subprocess.run(["git", "tag", f"v{new_version}"], check=True)

    def update_pyproject_version():
        TOML_DATA["project"]["version"] = new_version  # type: ignore
        with PYPROJECT_TOML_PATH.open("w", encoding="utf-8") as f:
            tomlkit.dump(TOML_DATA, f)

    def push_tag_to_remote():
        subprocess.run(["git", "push", "origin", f"v{new_version}"], check=True)

    try:
        update_pyproject_version()
        git_commit()
        git_tag()
        push_tag_to_remote()
        print(f"Version bumped from {CUR_VERSION} to {new_version}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    app()
