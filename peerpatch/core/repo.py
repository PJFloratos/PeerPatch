import os
import subprocess
import sys


REPO_DIR = "/app/storage"

def run_git_quiet(args):
    """Helper to run git commands quietly in the background."""
    subprocess.run(["git", "-C", REPO_DIR] + args, capture_output=True, check=True)

def init_git_repo(node_name):
    """Initializes standard Git directory."""
    # Initialize Git
    if not os.path.exists(os.path.join(REPO_DIR, ".git")):
        subprocess.run(["git", "init", "--initial-branch=main", REPO_DIR], check=True)
        print("[+] Native Git repository initialized.")
    else:
        print("[*] Git repository already exists.")

    # Configure local Git identity automatically using the node name
    try:
        run_git_quiet(["config", "user.name", node_name])
        run_git_quiet(["config", "user.email", f"{node_name}@peerpatch.local"])
    except subprocess.CalledProcessError:
        pass # Gracefully ignore if config fails

    # Secure the PeerPatch config via .gitignore
    gitignore_path = os.path.join(REPO_DIR, ".gitignore")
    ignore_entry = ".peerpatch/\n"
    needs_commit = False

    # Check if .gitignore exists to either create or append
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()

        # Only append if it's not already in the file
        if ".peerpatch" not in content:
            with open(gitignore_path, "a") as f:
                f.write(f"\n# PeerPatch Tracking\n{ignore_entry}")
            print("[+] Appended .peerpatch/ to existing .gitignore.")
            needs_commit = True
    else:
        # Create a fresh .gitignore
        with open(gitignore_path, "w") as f:
            f.write(f"# PeerPatch Tracking\n{ignore_entry}")
        print("[+] Created .gitignore to secure .peerpatch/ config.")
        needs_commit = True

    # Automatically commit the .gitignore
    if needs_commit:
        try:
            run_git_quiet(["add", ".gitignore"])
            run_git_quiet(["commit", "-m", "chore: secure PeerPatch identity tracking"])
            print("[+] Automatically committed .gitignore security rules.")
        except subprocess.CalledProcessError:
            print("[-] Failed to auto-commit .gitignore. Please commit manually.")


def passthrough_git(git_command, args):
    """Passes commands directly to the native Git engine."""
    # We combine 'git', the repo directory flag, the command (e.g., 'add'), and any user arguments
    full_command = ["git", "-C", REPO_DIR, git_command] + args

    # We don't capture output here; we let Git print directly to the user's terminal
    # so they get all the native colored formatting and error messages.
    try:
        subprocess.run(full_command, check=True)
    except subprocess.CalledProcessError:
        # Git already printed the error to the screen, so we just gracefully exit
        sys.exit(1)
