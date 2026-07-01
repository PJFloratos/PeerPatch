import paramiko


class P2PNetwork:
    def __init__(self, git_engine):
        self.git = git_engine

    def get_remote_pubkey(self, target_peer):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(target_peer, port=22, username="root", password="peerpatch123")
            _, stdout, _ = ssh.exec_command(
                "cat /app/storage/.peerpatch/id_ed25519.pub"
            )
            return stdout.read().decode().strip()
        except Exception as e:
            print(f"[-] Failed to connect to {target_peer}: {e}")
            return None
        finally:
            ssh.close()

    def remote_register(self, target_peer, node_name):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(target_peer, port=22, username="root", password="peerpatch123")
            ssh.exec_command(
                f"python3 /app/peerp.py register downstream_nodes {node_name}"
            )
            print(f"    -> Handshake complete with Hub: {target_peer}")
        except Exception as e:
            print(f"    -> Handshake failed with {target_peer}: {e}")
        finally:
            ssh.close()

    def fetch_peer_state(self, target_peer, safe_namespace):
        self.git.run_with_output(
            [
                "fetch",
                f"ssh://root@{target_peer}/app/storage",
                "refs/meta/identity:refs/meta/identity",
            ]
        )
        self.git.run_with_output(
            [
                "fetch",
                f"ssh://root@{target_peer}/app/storage",
                f"refs/heads/*:refs/namespaces/{safe_namespace}/heads/*",
            ]
        )

    def push_namespace(self, my_peer_id, target_peer):
        """Pushes code votes and governance (if it exists) to a remote peer."""
        try:
            # 1. Push the VOTE namespace (not the local branch!)
            vote_ref = f"refs/namespaces/{my_peer_id}/heads/main"
            self.git.run_with_output(
                [
                    "push",
                    "--force",
                    f"ssh://root@{target_peer}/app/storage",
                    f"{vote_ref}:{vote_ref}",
                ]
            )

            # 2. Check if we have a governance proposal locally
            gov_ref = f"refs/namespaces/{my_peer_id}/meta/identity"
            local_gov = self.git.run_with_output(
                ["rev-parse", "--quiet", "--verify", gov_ref]
            )

            # 3. If it exists, explicitly push it to the peer
            if local_gov:
                self.git.run_with_output(
                    [
                        "push",
                        "--force",
                        f"ssh://root@{target_peer}/app/storage",
                        f"{gov_ref}:{gov_ref}",
                    ]
                )
                print(f"[+] Successfully pushed Governance update to {target_peer}.")

            print(f"[+] Successfully synchronized Code state with {target_peer}.")
        except Exception as e:
            print(f"[-] Sync to {target_peer} failed. Error: {e}")

    def gossip_all(self, target_peer):
        try:
            self.git.run_with_output(
                [
                    "push",
                    "--force",
                    f"ssh://root@{target_peer}/app/storage",
                    "refs/namespaces/*:refs/namespaces/*",
                ]
            )
            print(f"[+] Successfully gossiped full network state to {target_peer}.")
        except Exception as e:
            print(f"[-] Broadcast to {target_peer} failed. Error: {e}")

    def pull_all(self, target_peer):
        """Fetches the complete network state from a specific peer."""
        try:
            self.git.run_with_output(
                [
                    "fetch",
                    "--force",
                    f"ssh://root@{target_peer}/app/storage",
                    "refs/namespaces/*:refs/namespaces/*",
                    "refs/meta/identity:refs/meta/identity",
                ]
            )
            print(f"[+] Successfully pulled network state from {target_peer}.")
        except Exception as e:
            print(f"[-] Pull from {target_peer} failed. Error: {e}")

    def fetch_peer_namespace(self, target_peer, namespace_id):
        # If namespace_id is None, fetch all
        refspec = f"refs/namespaces/*:refs/namespaces/*"
        self.git.run_with_output(
            ["fetch", "--force", f"ssh://root@{target_peer}/app/storage", refspec]
        )
