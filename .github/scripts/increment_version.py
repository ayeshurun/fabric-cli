import os
import re


def increment_version(version, part):
    if "rc" in version:
        if ".rc" in version:
            base_version, rc_part = version.split(".rc")
        else:
            base_version, rc_part = version.split("rc")
        major, minor, patch = map(int, base_version.split("."))
        rc_num = int(rc_part)
    else:
        major, minor, patch = map(int, version.split("."))
        rc_num = None

    if part == "major":
        major += 1
        minor = 0
        patch = 0
        rc_num = None
    elif part == "minor":
        minor += 1
        patch = 0
        rc_num = None
    elif part == "patch":
        patch += 1
        rc_num = None
    elif part == "rc":
        if rc_num is not None:
            rc_num += 1
        else:
            rc_num = 0
    elif part == "release":
        rc_num = None
    else:
        raise ValueError(
            "Part must be one of 'major', 'minor', 'patch', 'rc', or 'release'"
        )

    return (
        f"{major}.{minor}.{patch}"
        if rc_num is None
        else f"{major}.{minor}.{patch}.rc{rc_num}"
    )


def main():
    part = os.environ["PART"]
    # Get current version from pyproject.toml
    with open("pyproject.toml", "r") as file:
        content = file.read()
        current_version_match = re.search(
            r'version\s*=\s*"(\d+\.\d+\.\d+(?:\.?rc\d+)?)', content
        )
        if not current_version_match:
            raise RuntimeError("Could not find version in pyproject.toml")
        current_version = current_version_match.group(1)
    new_version = increment_version(current_version, part)

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"new_version={new_version}\n")


if __name__ == "__main__":
    main()
