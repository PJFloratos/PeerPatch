import paramiko
import hashlib
import os
import json


class P2PNetwork:
    def __init__(self, git_engine, identity_manager):
        self.git = git_engine
        self.identity = identity_manager
        self.peers_file = os.path.join(self.identity.config_dir, "peers.json")

    def _add_to_address_book(self, peer_address):
        """Saves a known peer to the local routing table."""
        peers = []
        if os.path.exists(self.peers_file):
            with open(self.peers_file, "r") as f:
                try:
                    peers = json.load(f)
                except json.JSONDecodeError:
                    pass

        # Only add them if we don't already know them
        if peer_address not in peers:
            peers.append(peer_address)
            with open(self.peers_file, "w") as f:
                json.dump(peers, f, indent=2)
            print(f"[*] Added {peer_address} to local Address Book.")

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

                # --- Save the peer we just cloned from to our Address Book ---
                self._add_to_address_book(target_peer)
            else:
                print(
                    f"[*] {target_peer} has an initialized, but empty repository. Nothing to checkout."
                )

        except Exception as e:
            print(f"[-] P2P Clone transaction failed. Error: {e}")
        finally:
            ssh.close()

    def sync(self, target_peer=None):
        """Pushes local commits to peers. If no target, broadcasts to all known peers."""
        my_peer_id = self.identity.get_peer_id()
        if not my_peer_id:
            print("[-] Local identity not found. Cannot sync.")
            return

        targets = []
        if target_peer:
            # Manual override: Sync to a specific peer
            targets.append(target_peer)
        else:
            # Automatic broadcast: Read from the Address Book
            if os.path.exists(self.peers_file):
                with open(self.peers_file, "r") as f:
                    try:
                        targets = json.load(f)
                    except json.JSONDecodeError:
                        pass

            if not targets:
                print(
                    "[-] No known peers in Address Book. Specify a target manually (e.g., peerp sync alice_node)."
                )
                return

            print(f"[*] Broadcasting local state to {len(targets)} known peer(s)...")

        for peer in targets:
            print(f"[*] Syncing namespace upstream to: {peer}...")
            try:
                self.git.run_with_output(
                    [
                        "push",
                        f"ssh://root@{peer}/app/storage",
                        f"refs/heads/*:refs/namespaces/{my_peer_id}/heads/*",
                    ]
                )
                print(f"[+] Successfully synchronized state with {peer}.")
            except Exception as e:
                print(f"[-] Sync to {peer} failed. Error: {e}")
