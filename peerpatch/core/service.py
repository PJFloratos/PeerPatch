import hashlib


class PeerPatchService:
    def __init__(self, git, identity, network, consensus, address_book, node_name):
        self.git = git
        self.identity = identity
        self.network = network
        self.consensus = consensus
        self.address_book = address_book
        self.node_name = node_name

    def initialize(self):
        print("[*] Initializing PeerPatch Repository...")
        self.git.initialize_workspace(self.node_name)
        self.identity.setup_identity(self.node_name)
        self.git.commit_trust_anchor(self.identity.trust_file_path)

    def clone(self, target):
        print(f"[*] Attempting P2P clone from target node: {target}...")
        self.git.initialize_workspace(self.node_name)

        remote_pubkey = self.network.get_remote_pubkey(target)
        if not remote_pubkey:
            return

        safe_namespace = hashlib.sha256(remote_pubkey.encode()).hexdigest()
        print(f"[+] Target Peer ID resolved: {safe_namespace}")

        print("[*] Streaming Git objects from peer...")
        self.network.fetch_peer_state(target, safe_namespace)
        self.git.extract_trust_anchor(self.identity.trust_file_path)

        target_head = self.git.run_with_output(
            ["rev-parse", f"refs/namespaces/{safe_namespace}/heads/main"]
        )
        if target_head:
            self.git.run_quiet(["update-ref", "refs/heads/main", target_head])
            self.git.run_quiet(["checkout", "main", "--force"])

        print("[*] Setting up local Web of Trust identity...")
        self.identity.setup_identity(self.node_name)
        self.git.configure_profile(self.node_name)
        print(f"[+] Repository successfully cloned and aligned to {target}.")

        print("[*] Reading Global Constitution for logical network topology...")
        delegates = self.identity.get_delegates()
        print(
            f"[*] Registering as a Contributor with {len(delegates)} official Delegate Hub(s)..."
        )

        for delegate in delegates:
            if delegate != self.node_name:
                self.network.remote_register(delegate, self.node_name)

    def promote(self, pub_key, target_node):
        print(f"\n[*] === Starting Promotion Pipeline for {target_node} ===")
        if self.identity.propose_governance_change(
            "add_delegate", pub_key=pub_key, name=target_node
        ):
            self.git.commit_trust_anchor(
                self.identity.trust_file_path, peer_id=self.identity.get_peer_id()
            )
            self.address_book.remove(target_node)

            print("[*] Synchronizing with Delegate Council...")
            self.sync()
            print("[*] Broadcasting to Downstream Contributors...")
            self.broadcast()
            print(
                f"[+] Promotion Pipeline complete. {target_node} is now a Delegate.\n"
            )
        else:
            print("[-] Promotion Pipeline aborted.")

    def demote(self, pub_key, target_node):
        print(f"\n[*] === Starting Demotion Pipeline for {target_node} ===")
        if self.identity.propose_governance_change("remove_delegate", pub_key=pub_key):
            self.git.commit_trust_anchor(
                self.identity.trust_file_path, peer_id=self.identity.get_peer_id()
            )
            self.address_book.add(target_node)

            print("[*] Synchronizing with remaining Delegate Council...")
            self.sync()
            print("[*] Broadcasting revocation to Downstream Contributors...")
            self.broadcast()
            print(
                f"[+] Demotion Pipeline complete. {target_node} removed from Council.\n"
            )
        else:
            print("[-] Demotion Pipeline aborted.")

    def sync(self, target=None):
        my_id = self.identity.get_peer_id()
        if not my_id:
            return

        if target:
            print(f"[*] Syncing namespace directly to: {target}...")
            self.network.push_namespace(my_id, target)
            return

        delegates = self.identity.get_delegates()
        if not delegates:
            print("[-] No upstream delegates found in constitution.")
            return

        print(
            f"[*] Synchronizing local state upstream to {len(delegates)} Delegate(s)..."
        )
        for peer in delegates:
            self.network.push_namespace(my_id, peer)

    def broadcast(self):
        contributors = self.address_book.get_downstream()
        if not contributors:
            print("[-] No downstream contributors found in Address Book.")
            return

        print(
            f"[*] Broadcasting network gossip downstream to {len(contributors)} Contributor(s)..."
        )
        for peer in contributors:
            self.network.gossip_all(peer)

    def vote(self, commit_hash):
        my_id = self.identity.get_peer_id()
        self.git.run_quiet(
            ["update-ref", f"refs/namespaces/{my_id}/heads/main", commit_hash]
        )
        print(f"[+] Voted for commit {commit_hash}")

    def approve(self, commit_hash):
        print(f"[*] Starting Approval Pipeline for {commit_hash}...")
        self.vote(commit_hash)
        self.sync()
        self.consensus.evaluate()

    def pull(self):
        """Pulls the latest state from the Delegate Council."""
        delegates = self.identity.get_delegates()
        if not delegates:
            print("[-] No upstream delegates found to pull from.")
            return

        print(
            f"[*] Pulling latest network state from {len(delegates)} Delegate Hub(s)..."
        )
        for delegate in delegates:
            if delegate != self.node_name:
                self.network.pull_all(delegate)

    def federate(self):
        """Exchange namespaces with all other Delegates."""
        my_id = self.identity.get_peer_id()
        delegates = self.identity.get_delegates()

        for peer in delegates:
            if peer != self.node_name:  # Don't sync to self
                print(f"[*] Federating namespace with Delegate: {peer}")
                self.network.push_namespace(my_id, peer, push_governance=True)
                # Pull their namespace too
                self.network.fetch_peer_namespace(peer, None)

    def review(self, commit_hash):
        """Displays the commit message and code diff for a proposed hash."""
        print(f"\n[*] === Code Review for Proposal: {commit_hash[:7]} ===")

        # 1. Verify the object actually exists on disk
        exists = self.git.run_with_output(["cat-file", "-t", commit_hash])
        if not exists:
            print(f"[-] Commit {commit_hash} not found locally.")
            print("[-] You may need to run 'peerp pull' to fetch the latest objects.")
            return

        # 2. Show the commit message/metadata
        print("\n[Commit Details]")
        self.git.passthrough("log", ["-1", commit_hash])

        # 3. Show the exact diff between the current state and the proposal
        print("\n[Proposed Changes]")
        # Using main...hash shows the changes introduced by the commit relative to main
        self.git.passthrough("diff", ["--stat", "-p", f"main...{commit_hash}"])

        print("\n[*] ===================================================")
        print(f"[*] If you agree with these changes, cast your vote:")
        print(f"[*] -> peerp approve {commit_hash}")
        print("[*] ===================================================\n")
