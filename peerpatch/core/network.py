import os
import subprocess
import paramiko
import hashlib
from .identity import setup_identity


REPO_DIR = "/app/storage"

def run_git(args):
    """Helper to run standard git commands inside the repository folder."""
    # Create an environment copy and inject our automated SSH command
    custom_env = os.environ.copy()
    custom_env["GIT_SSH_COMMAND"] = "sshpass -p peerpatch123 ssh -o StrictHostKeyChecking=no"

    result = subprocess.run(
        ["git", "-C", REPO_DIR] + args,
        capture_output=True,
        text=True,
        env=custom_env
    )
    if result.returncode != 0:
        print(f"[-] Git Error: {result.stderr.strip()}")
    return result.stdout.strip()


def clone_from_peer(target_peer):
    """Connects to a remote peer and clones their repository state."""
    print(f"[*] Attempting P2P clone from target node: {target_peer}...")

    # 1. Initialize our local git repository workspace if it doesn't exist
    if not os.path.exists(os.path.join(REPO_DIR, ".git")):
        subprocess.run(["git", "init", "--initial-branch=main", REPO_DIR], check=True)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect over our Docker Bridge Network
        ssh.connect(hostname=target_peer, port=22, username='root', password='peerpatch123')

        # 2. Fetch the remote node's public key string
        stdin, stdout, stderr = ssh.exec_command("cat /app/storage/.peerpatch/id_ed25519.pub")
        remote_pubkey = stdout.read().decode().strip()

        if not remote_pubkey:
            print(f"[-] Target peer {target_peer} has not initialized PeerPatch yet.")
            return

        # Create a Git-safe, 20-character Peer ID hash from the public key
        safe_namespace = hashlib.sha256(remote_pubkey.encode()).hexdigest()[:20]
        print(f"[+] Target Peer ID resolved: {safe_namespace}")

        # 3. Stream Git objects into an isolated peer namespace via SSH
        print("[*] Streaming Git objects from peer...")
        run_git([
            "fetch",
            f"ssh://root@{target_peer}/app/storage",
            f"refs/heads/*:refs/namespaces/{safe_namespace}/heads/*"
        ])

        # 4. Fast-forward local canonical main to mirror the cloned target state
        target_head = run_git(["rev-parse", f"refs/namespaces/{safe_namespace}/heads/main"])

        if target_head:
            run_git(["update-ref", "refs/heads/main", target_head])
            run_git(["checkout", "main", "--force"])

            # 5. Initialize Bob's own local identity so he can push later
            node_name = os.getenv("NODE_NAME", "unknown_node")
            print("[*] Setting up local Web of Trust identity...")
            setup_identity(node_name)

            print("[*] Configuring local Git user profile...")
            run_git(["config", "user.name", node_name])
            run_git(["config", "user.email", f"{node_name}@peerpatch.local"])

            print(f"[+] Repository successfully cloned and aligned to {target_peer}.")
        else:
            print(f"[*] {target_peer} has an initialized, but empty repository. Nothing to checkout.")

    except Exception as e:
        print(f"[-] P2P Clone transaction failed. Error: {e}")
    finally:
        ssh.close()
