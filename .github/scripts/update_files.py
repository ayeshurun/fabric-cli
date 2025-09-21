import os
import re


def update_file(file_path, old_version, new_version):
    with open(file_path, "r") as file:
        content = file.read()

    # Use word boundaries to avoid replacing parts of other strings
    old_version_pattern = r"\b" + re.escape(old_version) + r"\b"
    content = re.sub(old_version_pattern, new_version, content)

    with open(file_path, "w") as file:
        file.write(content)


def main():
    files_to_update = [
        "pyproject.toml",
        "src/fabric_cli/__init__.py",
        "src/fabric_cli/core/fab_constant.py",
    ]

    old_version = os.environ["OLD_VERSION"]
    new_version = os.environ["NEW_VERSION"]

    for file_path in files_to_update:
        update_file(file_path, old_version, new_version)
        print(f"Updated {file_path} from {old_version} to {new_version}")


if __name__ == "__main__":
    main()
