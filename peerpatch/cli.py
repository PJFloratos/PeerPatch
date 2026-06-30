import sys
import os
from .core.repo import GitEngine
from .core.identity import IdentityManager
from .core.network import P2PNetwork
from .core.consensus import ConsensusEngine


class PeerPatchCLI:
    def __init__(self):
        self.node_name = os.getenv("NODE_NAME", "unknown_node")
        self.git = GitEngine()
        self.identity = IdentityManager()
        self.network = P2PNetwork(self.git, self.identity)
        self.consensus = ConsensusEngine(self.git, self.identity)

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
            self.git.commit_trust_anchor()

        elif command == "clone" and len(args) == 3:
            target = args[2]
            self.network.clone_from_peer(target, self.node_name)

        elif command == "promote" and len(args) == 4:
            pub_key = args[2]
            target_node = args[3]
            success = self.identity.propose_governance_change(
                "add_delegate", pub_key=pub_key, name=target_node
            )
            if success:
                my_peer_id = self.identity.get_peer_id()
                self.git.commit_trust_anchor(peer_id=my_peer_id)
                self.network.remove_from_address_book(target_node)

                print("[*] Synchronizing with Delegate Council...")
                self.network.sync()
                print("[*] Broadcasting to Downstream Contributors...")
                self.network.broadcast()
                print(
                    f"[+] Promotion Pipeline complete. {target_node} has been invited to the Delegate Council.\n"
                )
            else:
                print(f"[-] Promotion Pipeline aborted.")

        elif command == "demote" and len(args) == 4:
            pub_key = args[2]
            target_node = args[3]
            success = self.identity.propose_governance_change(
                "remove_delegate", pub_key=pub_key
            )
            if success:
                my_peer_id = self.identity.get_peer_id()
                self.git.commit_trust_anchor(peer_id=my_peer_id)
                self.network.add_to_address_book(target_node, "downstream_nodes")

                print("[*] Synchronizing with the remaining Delegate Council...")
                self.network.sync()
                print("[*] Broadcasting revocation to Downstream Contributors...")
                self.network.broadcast()
                print(
                    f"[+] Demotion Pipeline complete. {target_node} has been removed from the Delegate Council.\n"
                )
            else:
                print(f"[-] Demotion Pipeline aborted.")

        elif command == "register" and len(args) == 4:  # Internal
            # Usage: peerp register <role> <network_address>
            role = args[2]
            peer_address = args[3]
            self.network.add_to_address_book(peer_address, role)

        elif command == "broadcast":
            self.network.broadcast()

        elif command == "consensus":
            self.consensus.evaluate()

        elif command == "sync":
            if len(args) == 3:
                # User typed: peerp sync alice_node
                target = args[2]
                self.network.sync(target)
            else:
                # User typed: peerp sync
                self.network.sync()

        elif command == "commit":
            if self.consensus.has_pending_governance():
                print("\n[-] Pending Network Topology Updates Detected!")
                print("[-] You have received a new constitution from the network.")
                print(
                    "[-] You MUST run 'peerp consensus' to mathematically verify and accept"
                )
                print("[-] the new Delegates before you are allowed to commit code.\n")
                return

            # If safe, pass it to Git
            self.git.passthrough("commit", args[2:])

        elif command in ["add", "status", "log"]:
            self.git.passthrough(command, args[2:])

        elif command in ["rm", "remove"]:
            self.git.passthrough("rm", args[2:])

        else:
            print(f"[-] Invalid command or missing arguments.")


def main():
    cli = PeerPatchCLI()
    cli.handle_command(sys.argv)
