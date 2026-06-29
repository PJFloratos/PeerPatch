import sys
import os
from .core.repo import GitEngine
from .core.identity import IdentityManager
from .core.network import P2PNetwork


class PeerPatchCLI:
    def __init__(self):
        self.node_name = os.getenv("NODE_NAME", "unknown_node")
        self.git = GitEngine()
        self.identity = IdentityManager()
        self.network = P2PNetwork(self.git, self.identity)

    def handle_command(self, args):
        if len(args) < 2:
            print(
                "Usage: python peerp.py [init | clone | add | rm | commit | status | log]"
            )
            sys.exit(1)

        command = args[1]

        if command == "init":
            print("[*] Initializing PeerPatch Repository...")
            self.git.initialize_workspace(self.node_name)
            self.identity.setup_identity(self.node_name)

        elif command == "clone" and len(args) == 3:
            target = args[2]
            self.network.clone_from_peer(target, self.node_name)

        elif command in ["add", "status", "log", "commit"]:
            self.git.passthrough(command, args[2:])

        elif command in ["rm", "remove"]:
            self.git.passthrough("rm", args[2:])

        else:
            print(f"[-] Invalid command or missing arguments.")


def main():
    cli = PeerPatchCLI()
    cli.handle_command(sys.argv)
