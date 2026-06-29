import paramiko
import hashlib


class P2PNetwork:
    def __init__(self, git_engine, identity_manager):
        self.git = git_engine
        self.identity = identity_manager

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
            else:
                print(
                    f"[*] {target_peer} has an initialized, but empty repository. Nothing to checkout."
                )

        except Exception as e:
            print(f"[-] P2P Clone transaction failed. Error: {e}")
        finally:
            ssh.close()
