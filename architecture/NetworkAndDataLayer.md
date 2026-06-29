## 1. Network Topology: Delegates and Contributors

To achieve massive scalability while preventing spam and Sybil attacks, the network strictly divides nodes into two distinct roles:

* **Delegates (The Core/Hubs):** The trusted maintainers of the repository. Their public keys are hardcoded into the repository's cryptographic constitution. They have the authority to mathematically vote on the canonical state of the repository.
* **Contributors (The Edge/Spokes):** Standard developers who clone the code. They do not have voting power. They exist on the edge of the network, syncing their code upstream to a specific Delegate who acts as their "Sponsor."

## 2. The Routing Layer: The Address Book and Handshake

Because PeerPatch has no central database to track who is online, nodes maintain a local routing table (`.peerpatch/peers.json`) divided into two categories: `upstream_delegates` and `downstream_contributors`.

### The Two-Way Handshake

When a Contributor clones a repository from a Delegate, the network executes an automated two-way handshake over SSH:

1. **Upstream Registration:** The Contributor saves the Delegate's IP address to their `upstream_delegates` list.
2. **Downstream Registration:** The Contributor reaches back into the Delegate's machine and triggers the `peerp register` command, saving their own IP address in the Delegate's `downstream_contributors` list.

This ensures the Delegate knows exactly who is waiting to receive code updates when a consensus vote passes.

---

## 3. The Cryptographic Constitution (`trust.json`)

The absolute core of PeerPatch's security model is the `trust.json` file. It defines the "Rules of the Game," explicitly listing the public keys of the Delegates and the Quorum Threshold required to accept new code.

### The Mechanism of Distribution

If `trust.json` were just a random file, nodes wouldn't agree on the rules. Instead, it is embedded directly into the Git repository using low-level plumbing commands. It lives on a hidden, read-only branch called `refs/meta/identity`. When a node clones the repository, it fetches this hidden branch first, extracts the constitution, and uses it to verify the rest of the downloaded code.

### Why Every Node Needs It

* **Delegates (The Writers):** Use `trust.json` to calculate quorum. When they see a proposed commit, they check the constitution to see if enough *other* Delegates have signed off on it before moving their local `main` branch forward.
* **Contributors (The Readers):** Use `trust.json` for zero-trust verification. If a hacked Delegate tries to push malicious code to a Contributor, the Contributor's local engine checks the constitution. If the malicious code lacks the required signatures from the *other* Delegates, the Contributor mathematically rejects the payload, protecting their machine.

---

## 4. The Data Layer: Isolated Namespaces (The Multiverse)

In standard Git, pushing to `main` overwrites the branch. In PeerPatch, a node **never** pushes directly to another user's `main` branch.

Instead, PeerPatch heavily utilizes Git Namespaces. Every node's cryptographic Ed25519 public key is hashed into a 20-character Peer ID. When Node A syncs to Node B, Node A's commits are pushed into a highly isolated folder on Node B's hard drive:

> `refs/namespaces/<Node_A_Hash>/heads/main`

This prevents accidental overwrites, protects the canonical state, and allows a Delegate to safely store and review a Contributor's proposed code before making a merge decision.

---

## 5. The Commit and Sync Pipelines

### Flow A: The Contributor Pipeline (Proposing Code)

1. **Commit:** A Contributor writes code and runs `peerp commit`. The commit is saved locally.
2. **Sync:** The Contributor runs `peerp sync`. The engine reads the Address Book and pushes the code into their isolated namespace on their upstream Delegate's machine.
3. **Sponsorship:** The Delegate uses `peerp review` to inspect the namespace. If acceptable, the Delegate merges the Contributor's code into their own `main` branch, legally signing it.
4. **Consensus:** The Delegate syncs the sponsored code to the rest of the Delegate Council, who mathematically vote to make it canonical.

### Flow B: The Delegate Pipeline (Finalizing Code)

1. **Commit/Merge:** A Delegate either writes their own code or merges a Contributor's code.
2. **Sync:** The Delegate runs `peerp sync`. The engine pushes the new state upstream to the rest of the Delegate Council.
3. **Vote:** The Local Consensus Engines on all Delegate machines read the isolated namespaces. If Quorum is met, the canonical `refs/heads/main` fast-forwards.
4. **Broadcast:** The Delegate runs `peerp broadcast`, pushing the finalized canonical state downstream to all connected Contributors.
