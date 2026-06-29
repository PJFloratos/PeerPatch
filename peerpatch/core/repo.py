import os
import subprocess
import sys


class GitEngine:
    def __init__(self, repo_dir="/app/storage"):
        self.repo_dir = repo_dir
        self.git_env = os.environ.copy()
        self.git_env["GIT_SSH_COMMAND"] = (
            "sshpass -p peerpatch123 ssh -o StrictHostKeyChecking=no"
        )

    def _execute(self, args, capture=True, exit_on_fail=False):
        """Master method to handle all subprocess Git executions."""
        full_command = ["git", "-C", self.repo_dir] + args

        try:
            result = subprocess.run(
                full_command,
                capture_output=capture,
                text=True if capture else False,
                env=self.git_env,
                check=exit_on_fail,
            )

            # If we are capturing, handle the output and graceful errors
            if capture:
                if not exit_on_fail and result.returncode != 0:
                    print(f"[-] Git Error: {result.stderr.strip()}")
                return result.stdout.strip() if result.stdout else ""

        except subprocess.CalledProcessError:
            # If we are streaming to terminal (passthrough), Git already printed the error
            if not capture:
                sys.exit(1)
            raise  # Re-raise if it was a background task that faile

    def run_quiet(self, args):
        """Helper to run git commands quietly in the background. Used Inernally"""
        self._execute(args, capture=True, exit_on_fail=True)

    def run_with_output(self, args):
        """Helper to run git commands and capture output as a string. Used by Network"""
        return self._execute(args, capture=True, exit_on_fail=False)

    def passthrough(self, git_command, args):
        """Passes commands directly to the native Git engine. Only using in CLI"""
        self._execute([git_command] + args, capture=False, exit_on_fail=True)

    def initialize_workspace(self, node_name):
        """Initializes standard Git directory, configures user, and secures tracking."""
        if not os.path.exists(os.path.join(self.repo_dir, ".git")):
            subprocess.run(
                ["git", "init", "--initial-branch=main", self.repo_dir], check=True
            )
            print("[+] Native Git repository initialized.")
        else:
            print("[*] Git repository already exists.")

        self.configure_profile(node_name)
        self._secure_gitignore()

    def configure_profile(self, node_name):
        """Configures local Git identity."""
        try:
            self.run_quiet(["config", "user.name", node_name])
            self.run_quiet(["config", "user.email", f"{node_name}@peerpatch.local"])
        except subprocess.CalledProcessError:
            pass

    def _secure_gitignore(self):
        """Ensures .peerpatch is ignored to protect private keys."""
        gitignore_path = os.path.join(self.repo_dir, ".gitignore")
        ignore_entry = ".peerpatch/\n"
        needs_commit = False

        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                content = f.read()
            if ".peerpatch" not in content:
                with open(gitignore_path, "a") as f:
                    f.write(f"\n# PeerPatch Tracking\n{ignore_entry}")
                print("[+] Appended .peerpatch/ to existing .gitignore.")
                needs_commit = True
        else:
            with open(gitignore_path, "w") as f:
                f.write(f"# PeerPatch Tracking\n{ignore_entry}")
            print("[+] Created .gitignore to secure .peerpatch/ config.")
            needs_commit = True

        if needs_commit:
            try:
                self.run_quiet(["add", ".gitignore"])
                self.run_quiet(
                    ["commit", "-m", "chore: secure PeerPatch identity tracking"]
                )
                print("[+] Automatically committed .gitignore security rules.")
            except subprocess.CalledProcessError:
                print("[-] Failed to auto-commit .gitignore. Please commit manually.")
