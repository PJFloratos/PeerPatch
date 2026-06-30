### 1. Initialization and Setup

* **`init`**: The genesis command. It sets up the local Git repository, generates a new Ed25519 cryptographic identity, and creates the initial `trust.json` (the constitution) which marks the node as the Genesis Owner.
* **`clone <target>`**: Seeds the local machine with data from a remote peer. It fetches the remote node's objects and, crucially, performs a **handshake** by looking up the network's `trust.json` and automatically registering the local node as a "Contributor" with all official Delegate Hubs.

### 2. Governance and Topology (The "Macro" Pipelines)

These commands automate the complex interplay between cryptographic math, routing tables, and network synchronization.

* **`promote <pubkey> <node_name>`**:
1. Adds a node to the `trust.json` list of delegates.
2. Recalculates the dynamic consensus threshold (to $N/2 + 1$).
3. Removes the node from the `downstream_nodes` (subscriber) list.
4. Syncs the governance update to the Council and gossips the change to all known contributors.


* **`demote <pubkey> <node_name>`**:
1. Removes a node from the `trust.json` list of delegates.
2. Recalculates the threshold downward.
3. Adds the node back to the `downstream_nodes` list (so they still receive updates).
4. Synchronizes and gossips the new constitution to the network.



### 3. Network Transport (Plumbing)

These commands manage the movement of raw data between nodes.

* **`sync [target]`**: Pushes the local node's `heads/main` (code) and `meta/identity` (governance) namespaces upstream. If no target is specified, it pushes to all official Delegates listed in `trust.json`.
* **`broadcast`**: Used by Hubs (Delegates) to push the *entire* network state (all known namespaces) downstream to Contributors. This acts as the "Gossip Protocol" to keep the edge nodes updated.
* **`register <role> <address>`**: An internal/hidden command used by remote nodes during the `clone` handshake to add themselves to a Delegate's `peers.json` subscriber list.

### 4. Consensus and State Validation

* **`consensus`**: The "brain" of the node.
1. **Phase 1 (Governance):** Verifies the Owner's signature on the `meta/identity` branch. If valid, it updates the local constitution. If the rules changed, it halts to prevent processing code under outdated rules.
2. **Phase 2 (Code):** Evaluates the `heads/main` namespace. It tallies votes from all active Delegates. If the number of votes for a specific commit hash meets the current `threshold`, it fast-forwards the canonical `main` branch.



### 5. Standard Git Porcelain

These commands are pass-throughs to native Git, allowing the user to manage their code without breaking the PeerPatch security model.

* **`commit`**: Includes a **security guardrail**. Before the commit is executed, it runs `has_pending_governance`. If the node has received a new constitution that hasn't been evaluated via `consensus` yet, the commit is blocked to prevent working on a stale network topology.
* **`add` / `rm` / `status` / `log**`: Standard Git operations to manage the local working directory.
