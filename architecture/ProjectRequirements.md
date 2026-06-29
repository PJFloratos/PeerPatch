# PeerPatch: A P2P Decentralized Git Architecture

PeerPatch is a decentralized wrapper around Git that shifts collaboration from a single, centralized server (like GitHub) to a peer-to-peer "Web of Trust." By leveraging Git's native Directed Acyclic Graph (DAG) and cryptographic keypairs, PeerPatch eliminates the need for a central authority to mediate code conflicts or manage repository state.


---


## 1. Core Architecture: The Web of Trust

In a P2P architecture, pushing to a shared `refs/heads/main` would cause nodes to constantly overwrite each other. Instead, PeerPatch uses cryptographic identity and local consensus to determine the canonical state of a repository.

### Step 1: The Identity Document (The Trust Anchor)
The repository constitution is defined by a machine-readable document (JSON) created by the project founder.
* **The Payload:** Lists the public keys (e.g., `ed25519`) of trusted "Delegates" (Maintainers) and sets a Quorum Threshold (e.g., "Consensus requires 2 out of 3 Delegates to agree").
* **The Signature:** The founder signs this document with their private key.
* **The Storage:** Committed directly into an isolated, hidden branch (e.g., `refs/meta/identity`). The repository's unique P2P identifier is often the hash of this genesis commit.

### Step 2: Namespaced Refs (The Multiverse)
PeerPatch heavily utilizes Git Namespaces. Every user maintains an isolated view of the repository governed by their private key.
* Alice's `main` lives at: `refs/namespaces/<Alice_PublicKey>/heads/main`
* Bob's `main` lives at: `refs/namespaces/<Bob_PublicKey>/heads/main`

Users can only sign and update their own namespaces. The network mathematically rejects gossip messages attempting to spoof another user's namespace.

### Step 3: Local Consensus Engine
When a new node clones the repository, it achieves consensus locally without an API:
1. **Fetch the Anchor:** The node fetches `refs/meta/identity` and verifies the Delegates and Quorum.
2. **Fetch the Delegates:** The node downloads the specific namespaces of the Delegates.
3. **Compute Canonical State:** If the required quorum of Delegates point their `main` refs to the exact same commit hash, the local Git wrapper automatically updates the standard `refs/heads/main` to that agreed-upon commit.

---

## 2. Collaboration: Patching and Merge Conflicts

Because code is subjective, algorithms cannot merge code automatically. PeerPatch routes collaboration through the P2P layer while relying on human Delegates for validation.

### Decentralized Pull Requests
1. A contributor (Eve) commits code locally. Her code is safely stored in her immutable namespace: `refs/namespaces/<Eve_PublicKey>/heads/patch-1`.
2. Eve signs her patch and gossips it to the network.
3. Delegates receive the patch, test it locally, and if approved, merge it into their own `main` branches.
4. Once enough Delegates gossip their updated `main` branches to meet the Quorum Threshold, the network fast-forwards to the new state.

### Handling Merge Conflicts
If Eve submits a patch based on an outdated commit:
* **The Blockage:** Delegates cannot cleanly merge the code. Because they cannot sign a new `main` commit, quorum cannot be reached, and the network ignores the patch.
* **The Protection:** Eve's code remains perfectly safe and mathematically protected in her local namespace.
* **The Resolution:** A Delegate gossips a comment asking Eve to rebase. Eve pulls the latest canonical `main`, resolves the conflict locally, and gossips an "Update" message with her new commit hash. The Delegates can now merge the updated patch via a clean fast-forward.

---

## 3. Threat Modeling and Resilience

Because PeerPatch relies on Delegate keys to move the canonical branch forward, it faces specific distributed systems challenges.

### Mitigating Liveness and Safety Failures
* **Liveness Failures:** If enough Delegates lose their keys, quorum cannot be reached, freezing the repository state.
* **Safety Failures:** If Delegate keys are compromised, attackers can mathematically force malicious code into the canonical `main`.

### The Defense Mechanisms
1. **Dynamic Delegation:** The system allows Delegates to vote to rotate keys or add/remove members by updating the `refs/meta/identity` branch chronologically.
2. **The Social Fork (The Ultimate Failsafe):** If keys are compromised and the repo is hijacked, the community can execute a Social Fork. A user takes the last known good commit, generates a new Identity Document with new Delegates, and broadcasts the new identifier. Because the underlying Git objects are already stored locally on peer hard drives, nodes simply switch to gossiping under the new cryptographic "brand" without redownloading the history.


---


## 4. The Social Layer: Collaborative Objects (COBs) and CRDTs

Standard version control tracks code, but software development requires a social layer: Issues, Pull Requests, and code review comments. Storing highly concurrent, mutable social data in standard Git branches results in constant merge conflicts. PeerPatch solves this by implementing Collaborative Objects (COBs) powered by Conflict-Free Replicated Data Types (CRDTs).

### 4.1 Event Sourcing the Social Graph
PeerPatch does not store the *state* of an Issue (e.g., a centralized database row). Instead, it stores a cryptographic ledger of *actions*. Every social interaction (opening an Issue, leaving a comment, changing a PR status) is represented as a lightweight JSON payload.

### 4.2 The Hidden DAG (Separating Code from State)
These JSON payloads are not committed to the `main` source code branch. They are committed as standard Git objects into dedicated, hidden namespaces (e.g., `refs/namespaces/<User_Key>/cobs/issues/<Issue_ID>`). By using Git as a raw database, PeerPatch leverages the Merkle tree to guarantee the integrity and authorship of every comment.

### 4.3 Conflict-Free Merging
When two peers comment on the same Issue simultaneously while offline, their local Git clients generate divergent commits with the same parent, creating a fork in the DAG.

Instead of requiring manual intervention to resolve this "conflict," PeerPatch acts as a state engine:
1. **DAG Traversal:** When nodes sync, the local client walks the Git DAG for that specific COB, collecting all concurrent JSON operations.
2. **Deterministic Sorting:** The client sorts the operations mathematically (using logical timestamps or cryptographic hash sorting).
3. **State Reduction:** The client applies the sorted operations sequentially to project the final state of the Issue/PR.


---


## 5. Spam Mitigation & Sybil Resistance
**The Flaw**: In a pure P2P network, an attacker can generate millions of fake keypairs, create infinite namespaces, and flood the gossip network with garbage patches.

To resolve the Sybil and spam problem the PeerPatch architecture abandons the *permissionless gossip* model and adopts a **Hierarchical Trusted Environment**. The default state of the network for any unauthenticated node is strictly **read-only**.

### 5.1 The Hierarchy of Power
1. **The Owner (Ultimate Authority):** The cryptographic key that signed the genesis identity document. The Owner has unilateral power to add or revoke Delegates by pushing updates to the `refs/meta/identity` branch.
2. **The Delegates (The Core Consensus):** Keys granted write and voting privileges by the Owner. Delegates send their own patches, vote on state changes, and form the quorum required to advance the canonical `refs/heads/main` branch.
3. **The Lieutenants (Delegate-Trusted Nodes):** Specific public keys trusted by individual Delegates. A Delegate explicitly whitelists these keys in their local namespace. These nodes cannot vote on the canonical state, but they are granted network access to route patches directly to their sponsoring Delegate.
4. **Read-Only Nodes (The Public):** Standard users who sync the repository to view code. They are cryptographically blocked from pushing data into the global gossip network.

### 5.2 The Routing Rules
* **The Core Rule**: By default, every node in the network only subscribes to the gossip topics and fetches the Git namespaces of the Owner and the Delegates.
* **The Edge Rule**: A Delegate node will additionally listen to the gossip from its specific list of Lieutenants. If a Lieutenant submits a patch, the Delegate reviews it. If acceptable, the Delegate signs off, merges it into their own namespace, and gossips it to the other Delegates for a quorum vote.

**The Result**: If an attacker spins up a million fake keypairs and broadcasts patches, the core nodes ignore them because those keys are not listed in `refs/meta/identity`. The Delegate nodes ignore them because the keys are not on any local Vouched Contributor list. Spam is killed at the network edge before it ever consumes disk space or bandwidth.


---


## 6. Namespace Storage Bloat (Lazy Fetching)
**The Flaw**: If a repository has 10,000 contributors, forcing every node to download 10,000 isolated multiverses (refs/namespaces/...) will exhaust local disk space and bandwidth.

### 6.1 Asymmetric Syncing (Isolating the Lieutenants)
**The Rule**: A Delegate only fetches the namespaces of their specific Lieutenants. The rest of the network (other Delegates and Read-Only nodes) completely ignores them.

**The Result**: If Delegate Alice has 50 Lieutenants, only Alice's hard drive stores their WIP branches. Once Alice approves a patch and merges it into her `refs/namespaces/<Alice>/heads/main`, the rest of the network simply pulls the finalized commit from Alice. The network never downloads the 50 isolated multiverses.

### 6.2 Shallow Consensus Syncing (For Read-Only Nodes)
**The Rule**: Standard nodes are programmed to strictly fetch the main references required to calculate consensus: `refs/namespaces/<Delegate_Keys>/heads/main`.

**The Result**: The local client mathematically verifies the quorum based on the commit hashes at the tips of those specific branches, fast-forwards the local user's working directory, and drops the connection. All other Delegate feature branches (e.g., refs/namespaces/<Delegate>/heads/feature-x) are ignored.

### 6.3 COB Pruning (Garbage Collecting the Social Graph)

**The Rule**: The Owner or Delegates can periodically issue a "State Rollup." This is a single, signed JSON payload representing the final, closed state of an Issue or merged PR.

**The Result**: Once the rollup is pushed to the Delegate consensus, nodes can safely garbage-collect and delete the underlying thousands of individual comment payloads from their local database, reclaiming disk space while maintaining the verifiable end state.


---


## 7. Large File Storage (LFS)
**The Flaw**: The Git DAG is notoriously bad at handling large binaries (images, compiled assets). P2P replication exacerbates this.

The solution is to separate the state of the repository (the Git DAG) from the bulk data (the binaries). Implement a parallel, chunk-based P2P file-sharing protocol specifically for large assets.

### 7.1 The Intercept and Pointer System
When a Delegate or Lieutenant adds a large binary to their local working directory, the PeerPatch client intercepts it before it enters the Git DAG (a local pre-commit hook identifies files over a certain threshold (e.g., 5MB) or matching specific extensions). Then, the client calculates the cryptographic hash (e.g., SHA-256) of the binary and commits a lightweight text pointer file into the Git DAG instead of the file itself. The actual binary is moved to an isolated local directory outside the Git object database.

### 7.2 Lazy Fetching (On-Demand Retrieval)
When a Read-Only node or another Delegate fetches the repository, they download the Git DAG and the tiny text pointers. They do not download the binaries during the sync phase. The binary is only requested over the network when the local user explicitly runs a checkout command that requires that specific file to be present in their working directory.

### 7.3 Hierarchical Seeding (The Delegate Responsibility)
The Owner and Delegates are designated as the primary "Pinning Nodes" for the canonical main branch. When a Delegate merges a PR containing an LFS pointer, their local node automatically streams and stores the full underlying binary from the Lieutenant. Read-Only nodes are guaranteed to find the binaries because the Delegates are mandated to seed the assets associated with the accepted canonical state.

### 7.4 Chunking and Streaming
When a node requests a 1GB file from a Delegate, the Delegate's node slices the file into smaller chunks (e.g., 256KB blocks). The downloading node mathematically verifies each chunk against a Merkle tree of the file hash as it arrives. If a connection drops, the download resumes exactly where it left off without re-downloading the entire file.

---


## 8. CRDT State Compaction
The Flaw: Event-sourcing an active Issue with thousands of comments creates a massive, deep Git history for a single COB. Walking this DAG locally becomes computationally expensive over time.

### 8.1 Tip-First Traversal via Checkpoints (Solving the Traversal Cost)
Standard event-sourcing forces a node to walk the DAG from the Genesis commit forward to the Tip. This is O(n) complexity, where n is the number of comments.

**The Mechanism**: Delegates periodically inject a special "Checkpoint Commit" into the COB namespace. This payload contains the fully computed, deterministic state of the Issue at that exact moment (e.g., the current title, status, and the list of active comment hashes).

**The Traversal**: When a local node syncs an active Issue, it walks the DAG backward from the Tip. As soon as it hits the first Checkpoint Commit signed by a recognized Delegate, it stops traversing.

**The Result**: The node loads the state from the Checkpoint and only computes the few new, un-checkpointed actions that occurred after it. Traversal becomes O(k) where k is the small number of recent events, regardless of how deep the total history is.

### 8.2 Hierarchical Checkpoint Authority (Solving the Conflict)
If anyone can submit a checkpoint, the network forks. By relying on your Trusted Environment, you enforce strict rules on state compaction.

**The Rule**: Only the Owner or the Delegates have the network authority to gossip a Checkpoint Commit.

**Conflict Resolution**: If Delegate A and Delegate B issue a checkpoint at the exact same time, it does not matter. Because the underlying data is a Conflict-Free Replicated Data Type (CRDT), the reduction is mathematically deterministic. Their checkpoints will project the exact same state hash. The network accepts both as valid causal parents for the next comment, merging the DAG cleanly.


### 8.3 Cryptographic Accumulators (Solving the Loss of Authorship)
You cannot delete history without breaking zero-trust verification, but you also cannot force nodes to store thousands of JSON signatures forever.

**The Mechanism**: When a Delegate generates a Checkpoint Commit, the payload does not just include the readable state. It must include a Merkle Root of all the individual cryptographic signatures and event hashes that are being compacted.

**The Pruning Logic**: Once a Read-Only node verifies the Delegate's Checkpoint, it can execute a local Git garbage collection. It deletes the physical JSON payloads of the thousands of old comments to save disk space, but retains the Checkpoint's Merkle Root.

**The Result**: If a user ever needs to audit a specific past comment for authorship, they can request that specific payload from a Delegate's archival node and mathematically verify it against the locally stored Merkle Root.


---


## 9. Data Availability: IPFS Integration & Proof of Retrievability (PoR)

To move away from relying on the altruism of your Delegates for Large File Storage (LFS), you must separate the verifiable metadata (the Git DAG) from the bulk storage layer, and enforce cryptographically backed storage incentives.

### 9.1 The IPFS Clean/Smudge Integration
When a user runs git add large_video.mp4, the PeerPatch clean filter intercepts the binary. It pushes the file into the user's local IPFS daemon, which chunks it and calculates the cryptographic Content Identifier (CID). The filter then writes a lightweight text pointer (e.g., ipfs://<CID>) into the Git object database instead of the video. When a user switches branches and needs large_video.mp4, the smudge filter reads the ipfs://<CID> pointer from the Git tree, queries the local IPFS daemon (which fetches it from the P2P swarm if not cached), and streams the binary back into the working directory

### 9.2 Implementing Proof of Retrievability (PoR)
To ensure Delegates are actually pinning these CIDs and not just deleting them to save disk space, the local consensus engine must enforce a PoR protocol.


---


## 10. Semantic Code Conflict Resolution (AST-CRDTs)
Traditional Git relies on line-based diffs (like Myers' diff algorithm). If User A modifies line 10 and User B modifies line 11 concurrently, standard Git often throws a merge conflict because the textual context has changed. AST-CRDTs solve this by understanding the code's structure, not its text.

### 10.1 The Pre-Merge Hook Driver
When the local consensus engine detects a branch divergence, it does not attempt a text merge. Instead, it triggers your custom driver:
* Parsing: The driver parses both the base commit and the two divergent commits into Abstract Syntax Trees (ASTs).
* Conversion to CRDTs: The ASTs are mapped into a JSON-like Conflict-Free Replicated Data Type (using a library like Yjs or Automerge).
    * Objects/Maps: Represent classes, function signatures, and variable declarations.
    * Lists/Sequences: Represent the actual lines of code or statements inside a block.

### 10.2 The Failsafe: Syntactic vs. Semantic Conflicts
It is critical to note that while AST-CRDTs eliminate syntactic merge conflicts (Git will no longer halt the merge), they can still create semantic bugs (e.g., Delegate A renames a variable, Delegate B uses the old variable name in a new line of code). The code will merge cleanly but fail to compile.

To handle this in a decentralized environment, this AST merge must be paired with the local consensus engine. If the AST auto-merge results in code that fails the project's build step (verified by a pre-commit hook), the consensus engine automatically rejects the auto-merge, flags the patch as a "Semantic Conflict," and creates a COB (Collaborative Object) issue requiring human Delegates to submit a manual resolution patch.
