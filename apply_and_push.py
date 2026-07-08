#!/usr/bin/env python3
"""
Apply the FIARS dispatch-table patch and push it.

Run this FROM YOUR LOCAL CLONE of the repo (the folder that already has
.git in it), with the patch file downloaded next to it, e.g.:

    cd ~/path/to/FIARS
    python3 apply_and_push.py

Uses your machine's own git auth (SSH key or cached credential helper) —
nothing is embedded here. Set PUSH = False first if you just want to
apply and inspect before pushing.
"""
import subprocess
import sys
from pathlib import Path

PATCH_FILE = "0001-Add-dispatch-table-parsing-merge-into-ticket-jobs.patch"
BRANCH = "main"
PUSH = True  # flip to False to apply only, review, then push manually


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(f"Command failed: {' '.join(cmd)}")


def main() -> None:
    if not Path(".git").exists():
        sys.exit("Run this from the root of your local FIARS clone (no .git folder found here).")
    if not Path(PATCH_FILE).exists():
        sys.exit(f"Patch file '{PATCH_FILE}' not found next to this script.")

    status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True).stdout
    if status.strip():
        sys.exit("Working tree isn't clean — commit or stash your changes first:\n" + status)

    run(["git", "checkout", BRANCH])
    run(["git", "pull", "origin", BRANCH])
    run(["git", "am", PATCH_FILE])  # preserves the original commit message + author

    if PUSH:
        run(["git", "push", "origin", BRANCH])
        print("Pushed.")
    else:
        print("Applied locally. Review with 'git show', then run: git push origin", BRANCH)


if __name__ == "__main__":
    main()
