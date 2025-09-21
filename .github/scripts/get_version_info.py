import os
import re
import subprocess
from collections import defaultdict

# Regex patterns for Conventional Commits
feat_pattern = re.compile(r"^feat(\([^)]+\))?:", re.IGNORECASE)
feat_breaking_pattern = re.compile(r"^feat!|^feat!\([^)]*\):", re.IGNORECASE)
fix_pattern = re.compile(r"^fix(\([^)]+\))?:", re.IGNORECASE)


def get_version_bump_from_commits(last_tag: str | None) -> str | None:
    """
    Determines the version bump type ('major', 'minor', 'patch') from commit messages.
    """
    try:
        if last_tag:
            commits = subprocess.check_output(
                ["git", "log", f"{last_tag}..HEAD", "--merges", "--pretty=format:%B"],
                text=True,
            ).strip()
        else:
            commits = subprocess.check_output(
                ["git", "log", "--merges", "--pretty=format:%B"], text=True
            ).strip()
    except Exception as exc:
        print(f"Error getting commits: {exc}")
        commits = ""

    if not commits:
        return None

    commit_lines = [c.strip() for c in commits.splitlines() if c.strip()]
    bump_commits = defaultdict(list)

    for c in commit_lines:
        if feat_breaking_pattern.match(c):
            bump_commits["major"].append(c)
        elif feat_pattern.match(c):
            bump_commits["minor"].append(c)
        elif fix_pattern.match(c):
            bump_commits["patch"].append(c)

    if bump_commits["major"]:
        bump_type = "major"
    elif bump_commits["minor"]:
        bump_type = "minor"
    elif bump_commits["patch"]:
        bump_type = "patch"
    else:
        bump_type = None

    print(f"\nVersion bump type from commits: {bump_type}")
    for bt in ["major", "minor", "patch"]:
        if bump_commits[bt]:
            print(f"\n{bt.upper()} commits ({len(bump_commits[bt])}):")
            for commit in bump_commits[bt]:
                print(f"  {commit}")

    return bump_type


def main():
    """
    Main function to determine version bump part and current version.
    """
    # Determine version part
    part = os.environ.get("VERSION_PART_INPUT")
    if not part:
        try:
            last_tag = (
                subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"])
                .decode()
                .strip()
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"Could not get last tag, probably because there are no tags yet. Error: {exc}"
            )
            last_tag = None
        print(f"Last tag: {last_tag}")
        part = get_version_bump_from_commits(last_tag)
    else:
        print(f"Got version bump part from input: {part}")

    # Set outputs
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        if part:
            f.write(f"part={part}\n")
            f.write("bump_needed=true\n")
        else:
            f.write("bump_needed=false\n")
            print("No version bump needed.")


if __name__ == "__main__":
    main()
