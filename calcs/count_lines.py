import os
import subprocess
from pathlib import Path


def count_lines_with_git_ignore(root_dir):
    total_lines = 0
    # Use git ls-files to get a list of files that are tracked by Git
    # This automatically excludes files in .gitignore (that aren't already tracked)
    try:
        # Change to the root directory temporarily to run the git command correctly
        os.chdir(root_dir)
        result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
        files = result.stdout.splitlines()

        for file_path in files:
            try:
                # Open each file with UTF-8 encoding to avoid UnicodeDecodeError
                with open(file_path, "r", encoding="utf-8") as f:
                    total_lines += len(f.readlines())
            except UnicodeDecodeError:
                print(f"Skipping file due to encoding error: {file_path}")
            except IOError as e:
                print(f"Error reading file {file_path}: {e}")

    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e.stderr}")
    except FileNotFoundError:
        print("Git is not installed or not found in the system's PATH.")

    return total_lines


if __name__ == "__main__":
    repo_path = str(Path(__file__).resolve().parents[1])
    lines = count_lines_with_git_ignore(repo_path)
    print(f"Total lines of code (excluding gitignore files): {lines}")

