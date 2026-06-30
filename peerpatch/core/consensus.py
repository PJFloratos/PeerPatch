import json
import hashlib
import os


class ConsensusEngine:
    def __init__(self, git_engine, identity_manager):
        self.git = git_engine
        self.identity = identity_manager

    def _evaluate_branch(
        self, namespace_suffix, canonical_ref, delegates, threshold, branch_type="code"
    ):
        """Generic helper to tally votes for any P2P branch."""
        vote_tally = {}

        # 1. Collect votes from Delegates' isolated namespaces
        for pub_key, name in delegates.items():
            safe_namespace = hashlib.sha256(pub_key.encode()).hexdigest()[:20]

            target_branch = f"refs/namespaces/{safe_namespace}/{namespace_suffix}"
            commit_hash = self.git.run_with_output(
                ["rev-parse", "--quiet", "--verify", target_branch]
            )

            if commit_hash:
                print(f"    - Delegate '{name}' votes for: {commit_hash[:7]}")
                vote_tally[commit_hash] = vote_tally.get(commit_hash, 0) + 1
            else:
                print(f"    - Delegate '{name}' has no vote registered.")

        # 2. Determine if Quorum is reached
        consensus_hash = None
        for commit, count in vote_tally.items():
            if count >= threshold:
                consensus_hash = commit
                break

        # 3. Apply the Consensus
        if consensus_hash:
            current_canonical = self.git.run_with_output(
                ["rev-parse", "--quiet", "--verify", canonical_ref]
            )

            if current_canonical == consensus_hash:
                print(
                    f"[*] {branch_type.capitalize()} state is already aligned with consensus. No changes made."
                )
                return False
            else:
                print(
                    f"[+] QUORUM REACHED! Fast-forwarding canonical {branch_type} to {consensus_hash[:7]}..."
                )
                self.git.run_quiet(["update-ref", canonical_ref, consensus_hash])
                return True
        else:
            print(f"[-] No quorum reached for {branch_type}.")
            return False

    def evaluate(self):
        """Calculates canonical state based on Web of Trust rules."""
        print("[*] Starting Local Consensus Evaluation...\n")

        if not os.path.exists(self.identity.trust_file_path):
            print("[-] trust.json not found. Cannot evaluate consensus.")
            return

        with open(self.identity.trust_file_path, "r") as f:
            trust_data = json.load(f)

        threshold = trust_data.get("threshold", 1)
        delegates = trust_data.get("delegates", {})
        owner_pub_key = trust_data.get("owner")

        print(
            f"[*] Active Quorum Rules: {threshold} / {len(delegates)} Delegates required.\n"
        )

        # --- PHASE 1: GOVERNANCE EVALUATION (Owner Authority) ---
        print("[*] Evaluating Governance Proposals (meta/identity)...")
        if owner_pub_key:
            owner_namespace = hashlib.sha256(owner_pub_key.encode()).hexdigest()[:20]
            owner_gov_ref = f"refs/namespaces/{owner_namespace}/meta/identity"

            owner_hash = self.git.run_with_output(
                ["rev-parse", "--quiet", "--verify", owner_gov_ref]
            )
            current_gov_hash = self.git.run_with_output(
                ["rev-parse", "--quiet", "--verify", "refs/meta/identity"]
            )

            if owner_hash and owner_hash != current_gov_hash:
                print(
                    f"[+] Owner Authority signature verified. Fast-forwarding constitution to {owner_hash[:7]}..."
                )
                self.git.run_quiet(["update-ref", "refs/meta/identity", owner_hash])
                self.git.extract_trust_anchor()
                print("[!] The rules of consensus have changed. Halting evaluation.")
                print(
                    "[!] Please re-run 'peerp consensus' to evaluate code under the new rules."
                )
                return
            elif not owner_hash:
                print("    - Owner has not published a governance branch.")
            else:
                print("    - Governance is aligned with Owner Authority.")
        else:
            print("[-] No Owner found in trust.json. Cannot verify governance.")

        # --- PHASE 2: CODE EVALUATION (Multi-Sig Quorum) ---
        print("\n[*] Evaluating Code Commits (heads/main)...")
        code_updated = self._evaluate_branch(
            "heads/main", "refs/heads/main", delegates, threshold, "code"
        )

        if code_updated:
            # 1. Check if the working directory is clean
            status = self.git.run_with_output(["status", "--porcelain"])

            if status:
                print("\n[-] ⚠️  CONSENSUS REACHED, BUT WORKING DIRECTORY IS DIRTY.")
                print(
                    "[-] You have uncommitted changes. To update your working directory to the"
                )
                print(
                    "[-] new canonical state, please 'commit' or 'stash' your changes first."
                )
                print("[-] Then run 'peerp consensus' again to perform the checkout.\n")
                return  # Stop here, do not perform the forced checkout

            # 2. If clean, perform the safe update
            self.git.run_quiet(["checkout", "main", "--force"])
            print("[+] Working directory successfully updated with new canonical code.")

    def has_pending_governance(self):
        """Checks if there are un-evaluated constitution updates from the Owner."""
        if not os.path.exists(self.identity.trust_file_path):
            return False

        with open(self.identity.trust_file_path, "r") as f:
            trust_data = json.load(f)

        owner_pub_key = trust_data.get("owner")
        if not owner_pub_key:
            return False

        owner_namespace = hashlib.sha256(owner_pub_key.encode()).hexdigest()[:20]
        owner_gov_ref = f"refs/namespaces/{owner_namespace}/meta/identity"

        # Check what the owner's branch says vs our current canonical branch
        owner_hash = self.git.run_with_output(
            ["rev-parse", "--quiet", "--verify", owner_gov_ref]
        )
        current_gov_hash = self.git.run_with_output(
            ["rev-parse", "--quiet", "--verify", "refs/meta/identity"]
        )

        # If the owner has a new hash we haven't evaluated, return True
        if owner_hash and owner_hash != current_gov_hash:
            return True

        return False
