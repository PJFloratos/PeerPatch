import paramiko
import hashlib
import os
import json


class P2PNetwork:
    def __init__(self, git_engine, identity_manager):
        self.git = git_engine
        self.identity = identity_manager
        self.peers_file = os.path.join(self.identity.config_dir, "peers.json")

    def _read_address_book(self):
        """Address book now ONLY tracks downstream nodes for broadcasting."""
        default_book = {"downstream_nodes": []}

        if not os.path.exists(self.peers_file):
            return default_book

        with open(self.peers_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_book

    def _write_address_book(self, data):
        """Saves the address book to disk."""
        with open(self.peers_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_to_address_book(self, peer_address, role="upstream_delegates"):
        """Saves a known peer to a specific routing category."""
        book = self._read_address_book()

        if role not in book:
            book[role] = []

        # Only add them if we don't already know them
        if peer_address not in book[role]:
            book[role].append(peer_address)
            self._write_address_book(book)
            print(f"[*] Added {peer_address} to Address Book as '{role}'.")

    def remove_from_address_book(self, peer_address):
        """Removes a peer from the downstream subscriber list."""
        book = self._read_address_book()

        if peer_address in book.get("downstream_nodes", []):
            book["downstream_nodes"].remove(peer_address)
            self._write_address_book(book)
            print(
                f"[*] Cleaned routing table: {peer_address} removed from downstream broadcasts."
            )

    def clone_from_peer(self, target_peer, node_name):
        """Connects to a remote peer and clones their repository state."""
        print(f"[*] Attempting P2P clone from target node: {target_peer}...")

        # 1. Initialize local Git workspace
        self.git.initialize_workspace(node_name)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=target_peer, port=22, username="root", password="peerpatch123"
            )

            # 2. Fetch remote node's public key
            stdin, stdout, stderr = ssh.exec_command(
                "cat /app/storage/.peerpatch/id_ed25519.pub"
            )
            remote_pubkey = stdout.read().decode().strip()

            if not remote_pubkey:
                print(
                    f"[-] Target peer {target_peer} has not initialized PeerPatch yet."
                )
                return

            safe_namespace = hashlib.sha256(remote_pubkey.encode()).hexdigest()[:20]
            print(f"[+] Target Peer ID resolved: {safe_namespace}")

            # 3. Stream Git objects via SSH
            print("[*] Streaming Git objects from peer...")
            # --- Fetch the Constitution First ---
            self.git.run_with_output(
                [
                    "fetch",
                    f"ssh://root@{target_peer}/app/storage",
                    "refs/meta/identity:refs/meta/identity",
                ]
            )
            self.git.extract_trust_anchor()

            self.git.run_with_output(
                [
                    "fetch",
                    f"ssh://root@{target_peer}/app/storage",
                    f"refs/heads/*:refs/namespaces/{safe_namespace}/heads/*",
                ]
            )

            # 4. Fast-forward local canonical main
            target_head = self.git.run_with_output(
                ["rev-parse", f"refs/namespaces/{safe_namespace}/heads/main"]
            )

            if target_head:
                self.git.run_with_output(["update-ref", "refs/heads/main", target_head])
                self.git.run_with_output(["checkout", "main", "--force"])

                # 5. Initialize local identity and Git profile
                print("[*] Setting up local Web of Trust identity...")
                self.identity.setup_identity(node_name)

                print("[*] Configuring local Git user profile...")
                self.git.configure_profile(node_name)

                print(
                    f"[+] Repository successfully cloned and aligned to {target_peer}."
                )

                # --- THE DYNAMIC HUB HANDSHAKE ---
                print("[*] Reading Global Constitution for logical network topology...")
                trust_file = self.identity.trust_file_path

                if os.path.exists(trust_file):
                    with open(trust_file, "r") as f:
                        trust_data = json.load(f)

                    delegates = list(trust_data.get("delegates", {}).values())
                    print(
                        f"[*] Registering as a Contributor with {len(delegates)} official Delegate Hub(s)..."
                    )

                    for delegate_host in delegates:
                        if delegate_host == node_name:
                            continue  # Don't SSH into ourselves
                        try:
                            hub_ssh = paramiko.SSHClient()
                            hub_ssh.set_missing_host_key_policy(
                                paramiko.AutoAddPolicy()
                            )
                            hub_ssh.connect(
                                hostname=delegate_host,
                                port=22,
                                username="root",
                                password="peerpatch123",
                            )
                            hub_ssh.exec_command(
                                f"python3 /app/peerp.py register downstream_nodes {node_name}"
                            )
                            hub_ssh.close()
                            print(
                                f"    -> Handshake complete with Hub: {delegate_host}"
                            )
                        except Exception as e:
                            print(f"    -> Handshake failed with {delegate_host}: {e}")
            else:
                print(
                    f"[*] {target_peer} has an initialized, but empty repository. Nothing to checkout."
                )

        except Exception as e:
            print(f"[-] P2P Clone transaction failed. Error: {e}")
        finally:
            ssh.close()

    def _push_namespace(self, my_peer_id, target_peer):
        """Helper to push the local namespace to a specific peer."""
        try:
            # 1. Push the Code
            self.git.run_with_output(
                [
                    "push",
                    "--force",
                    f"ssh://root@{target_peer}/app/storage",
                    f"refs/heads/*:refs/namespaces/{my_peer_id}/heads/*",
                ]
            )

            # 2. Push Governance Proposals (if they exist)
            # We check locally first so Git doesn't throw a "src refspec missing" error
            local_gov = self.git.run_with_output(
                [
                    "rev-parse",
                    "--quiet",
                    "--verify",
                    f"refs/namespaces/{my_peer_id}/meta/identity",
                ]
            )

            if local_gov:
                self.git.run_with_output(
                    [
                        "push",
                        "--force",
                        f"ssh://root@{target_peer}/app/storage",
                        f"refs/namespaces/{my_peer_id}/meta/identity:refs/namespaces/{my_peer_id}/meta/identity",
                    ]
                )

            print(f"[+] Successfully synchronized state with {target_peer}.")
        except Exception as e:
            print(f"[-] Sync to {target_peer} failed. Error: {e}")

    def sync(self, target_peer=None):
        """Pushes local commits upstream by reading the cryptographic constitution."""
        my_peer_id = self.identity.get_peer_id()
        if not my_peer_id:
            print("[-] Local identity not found. Cannot sync.")
            return

        if target_peer:
            print(f"[*] Syncing namespace directly to: {target_peer}...")
            self._push_namespace(my_peer_id, target_peer)
            return

        # THE FLAT EDGE: Read upstream routing directly from the math (trust.json)
        trust_file = self.identity.trust_file_path
        if not os.path.exists(trust_file):
            print("[-] No constitution found. Cannot discover Delegates.")
            return

        with open(trust_file, "r") as f:
            trust_data = json.load(f)

        delegates = list(trust_data.get("delegates", {}).values())

        if not delegates:
            print("[-] No upstream delegates found in constitution.")
            return

        print(
            f"[*] Synchronizing local state upstream to {len(delegates)} official Delegate(s)..."
        )
        for peer in delegates:
            self._push_namespace(my_peer_id, peer)

    def broadcast(self):
        """Pushes finalized canonical state and network gossip downstream."""
        book = self._read_address_book()
        contributors = book.get("downstream_nodes", [])

        if not contributors:
            print("[-] No downstream contributors found in Address Book.")
            return

        print(
            f"[*] Broadcasting network gossip downstream to {len(contributors)} Contributor(s)..."
        )
        for peer in contributors:
            try:
                # THE GOSSIP PROTOCOL:
                # Instead of just pushing our own namespace, we relay ALL known
                # Delegate namespaces (*:*) to keep the downstream node fully informed.
                self.git.run_with_output(
                    [
                        "push",
                        "--force",
                        f"ssh://root@{peer}/app/storage",
                        "refs/namespaces/*:refs/namespaces/*",
                    ]
                )
                print(f"[+] Successfully gossiped full network state to {peer}.")
            except Exception as e:
                print(f"[-] Broadcast to {peer} failed. Error: {e}")
