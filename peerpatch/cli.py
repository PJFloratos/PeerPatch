import sys
import os
from .core.repo import GitEngine
from .core.identity import IdentityManager
from .core.network import P2PNetwork
from .core.consensus import ConsensusEngine
from .core.address_book import AddressBook
from .core.service import PeerPatchService


class PeerPatchCLI:
    def __init__(self):
        self.node_name = os.getenv("NODE_NAME", "unknown_node")

        # 1. Initialize atomic infrastructure
        self.git = GitEngine()
        self.identity = IdentityManager()
        self.network = P2PNetwork(self.git)
        self.consensus = ConsensusEngine(self.git, self.identity)
        self.address_book = AddressBook(self.identity.config_dir)

        # 2. Initialize the Orchestrator
        self.service = PeerPatchService(
            self.git,
            self.identity,
            self.network,
            self.consensus,
            self.address_book,
            self.node_name,
        )

    def handle_command(self, args):
        if len(args) < 2:
            print(
                "Usage: python peerp.py [init | clone | sync | broadcast | promote | demote | consensus | vote | approve | commit]"
            )
            sys.exit(1)

        command = args[1]

        if command == "init":
            self.service.initialize()

        elif command == "clone" and len(args) == 3:
            self.service.clone(args[2])

        elif command == "promote" and len(args) == 4:
            self.service.promote(pub_key=args[2], target_node=args[3])

        elif command == "demote" and len(args) == 4:
            self.service.demote(pub_key=args[2], target_node=args[3])

        elif command == "register" and len(args) == 4:
            self.address_book.add(args[3])

        elif command == "broadcast":
            self.service.broadcast()

        elif command == "sync":
            target = args[2] if len(args) == 3 else None
            self.service.sync(target)

        elif command == "consensus":
            self.consensus.evaluate()

        elif command == "vote" and len(args) == 3:
            self.service.vote(args[2])

        elif command == "approve" and len(args) == 3:
            self.service.approve(args[2])

        elif command in ["pull", "fetch"]:
            self.service.pull()

        elif command == "review" and len(args) == 3:
            self.service.review(args[2])

        elif command == "commit":
            if self.consensus.has_pending_governance():
                print("\n[-]Pending Network Topology Updates Detected!")
                print("[-] You MUST run 'peerp consensus' to verify and accept")
                print("[-] the new constitution before committing code.\n")
                return
            self.git.passthrough("commit", args[2:])

        elif command in ["add", "status", "log", "rm", "remove"]:
            cmd = "rm" if command == "remove" else command
            self.git.passthrough(cmd, args[2:])

        else:
            print("[-] Invalid command or missing arguments.")


def main():
    cli = PeerPatchCLI()
    cli.handle_command(sys.argv)
