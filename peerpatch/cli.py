import sys
import os
from .core.repo import init_git_repo, passthrough_git
from .core.identity import setup_identity
from .core.network import clone_from_peer


def cmd_init():
    print("[*] Initializing PeerPatch Repository...")
    node_name = os.getenv("NODE_NAME", "unknown_node")
    init_git_repo(node_name)
    setup_identity(node_name)


def cmd_clone(target_peer):
    clone_from_peer(target_peer)


def main():
    if len(sys.argv) < 2:
        print("Usage: python peerp.py [init | clone | add | rm | commit | status | log]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        cmd_init()
    elif command == "clone" and len(sys.argv) == 3:
        target = sys.argv[2]
        cmd_clone(target)

    # --- Native Git Wrappers ---
    elif command in ["add", "status", "log"]:
        passthrough_git(command, sys.argv[2:])
    elif command in ["rm", "remove"]:
        passthrough_git("rm", sys.argv[2:])
    elif command == "commit":
        # Pass all arguments after 'commit' directly to Git
        passthrough_git("commit", sys.argv[2:])
    else:
        print(f"[-] Invalid command or missing arguments.")
