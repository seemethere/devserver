#!/usr/bin/env python3
import subprocess
from pathlib import Path

def get_git_root():
    """Returns the root directory of the git repository."""
    return subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], encoding='utf-8').strip()

def find_readme_files(root_dir):
    """Finds all README.md files in the given directory."""
    return Path(root_dir).glob('**/README.md')

def get_last_commit_date(file_path):
    """Gets the last commit date for a given file."""
    return subprocess.check_output(
        ['git', 'log', '-1', '--format=%cI', str(file_path)],
        encoding='utf-8'
    ).strip()

def get_commits_since(date, directory):
    """Gets commit messages for a directory since a given date."""
    return subprocess.check_output(
        ['git', 'log', f'--since={date}', '--pretty=format:%h by %an: %s%n%b%n', '--name-status', str(directory)],
        encoding='utf-8'
    ).strip()

def main():
    """
    Analyzes all README.md files in the repository and prints the commit
    history since each file was last updated.
    """
    root = get_git_root()
    for readme in find_readme_files(root):
        relative_path = readme.relative_to(root)
        print(f"--- Analyzing: {relative_path} ---")

        try:
            last_date = get_last_commit_date(readme)
            if not last_date:
                print(f"Could not find commit history for {relative_path}")
                continue

            print(f"Last updated: {last_date}")

            containing_dir = readme.parent
            commits = get_commits_since(last_date, containing_dir)

            if commits:
                print("Recent changes in this directory:")
                print(commits)
            else:
                print("No changes since last update.")

        except subprocess.CalledProcessError:
            print(f"Could not process {relative_path}. Is it committed in git?")

        print("-" * (len(str(relative_path)) + 18))
        print()

if __name__ == "__main__":
    main()
