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

* **`sync [target]`**: Pushes the local node's `heads/main` (code) and `meta/identity` (governance) namespaces upstream. If no target is specified, it pushes to all official Delegates listed in `trust.json`. *Note: When executed by a Delegate, it federates (exchanges) namespaces with all other Delegates.*
* **`pull` / `fetch**`: The Contributor's lifeline. It reads the local constitution and actively fetches all namespaces and governance proposals from every official Delegate Hub, ensuring the edge node has the complete network picture.
* **`broadcast`**: Used by Hubs (Delegates) to push the *entire* network state (all known namespaces) downstream to Contributors. This acts as the "Gossip Protocol" to keep the passive edge nodes updated.
* **`register <role> <address>`**: An internal/hidden command used by remote nodes during the `clone` handshake to add themselves to a Delegate's `peers.json` subscriber list.

### 4. Code Review and Multi-Sig Action (Porcelain)

These commands bridge the gap between human intent and the mathematical consensus engine.

* **`review <hash>`**: The "Pull Request" viewer. It fetches a specific commit object, displays its metadata, and renders a standard Git line-by-line diff comparing the proposal against the current canonical `main` branch.
* **`vote <hash>`**: The raw atomic action. It simply updates the local `refs/namespaces/<YOUR_ID>/heads/main` pointer to a specific commit hash, formally registering your cryptographic support for that code.
* **`approve <hash>`** (Aliases: **`propose`**, **`sponsor`**): The ultimate workflow macro. It executes a complete submission pipeline in three steps:
1. **Votes** for the specified hash.
2. **Syncs** that vote upstream to the network.
3. **Evaluates** the local consensus engine to check if Quorum has been met.



### 5. Consensus and State Validation

* **`consensus`**: The "brain" of the node.
1. **Phase 1 (Governance):** Verifies the Owner's signature on the `meta/identity` branch. If valid, it updates the local constitution. If the rules changed, it halts to prevent processing code under outdated rules.
2. **Phase 2 (Code):** Evaluates the `heads/main` namespace. It tallies votes from all active Delegates. If the number of votes for a specific commit hash meets the current `threshold`, it queues the canonical `main` branch for a fast-forward.


It is an idempotent, side-effect-free audit with built-in safety guardrails:
* **If Quorum is NOT met:** The command prints the current tally (Delegate A votes for X, Delegate B votes for Y) and returns False. It modifies absolutely nothing.
* **If Quorum IS met:** It checks the local working directory. If dirty, it aborts to protect uncommitted work. If clean, it performs a safe atomic update (`git reset --hard`) to perfectly align the node's files with the newly accepted canonical state.



### 6. Standard Git Porcelain

These commands are pass-throughs to native Git, allowing the user to manage their code without breaking the PeerPatch security model.

* **`commit`**: Includes a **security guardrail**. Before the commit is executed, it runs `has_pending_governance`. If the node has received a new constitution that hasn't been evaluated via `consensus` yet, the commit is blocked to prevent working on a stale network topology.
* **`add` / `rm` / `status` / `log**`: Standard Git operations to manage the local working directory.

---

### The PeerPatch Operational Pipelines

Because the architecture decouples Data Availability (Transport) from Canonical Truth (Consensus), different users rely on different operational loops depending on their role in the Web of Trust.

#### Scenario A: The Delegate Code Merge (The "Happy Path")

*How two governing Hubs agree on a change.*

1. **Alice (Delegate 1)** writes code: `peerp add .` -> `peerp commit -m "feature"`
2. **Alice** proposes to the Council: `peerp approve <hash>` (Her vote is cast and synced to Bob).
3. **Bob (Delegate 2)** updates his state: `peerp pull` (or waits for Alice's sync).
4. **Bob** checks the Council: `peerp consensus` (Sees Alice's pending vote).
5. **Bob** reviews the diff: `peerp review <hash>`
6. **Bob** agrees and signs off: `peerp approve <hash>`
7. *Result:* Bob's machine reaches quorum and updates instantly. Alice's machine updates on her next `consensus` run.

#### Scenario B: The Contributor Pull Request

*How an unprivileged edge node submits code to the network.*

1. **Charlie (Contributor)** writes code: `peerp add .` -> `peerp commit -m "bugfix"`
2. **Charlie** submits to upstream Hubs: `peerp propose <hash>` (Alias for approve. Syncs data to Hubs).
3. **Alice (Delegate)** runs `consensus` and sees a non-delegate namespace update.
4. **Alice** reviews the code: `peerp review <hash>`
5. **Alice** sponsors the code: `peerp sponsor <hash>` (Alias for approve. She formally casts her Delegate vote for Charlie's hash).
6. *Result:* The Delegate Council takes over, reviewing and voting on the sponsored hash as in Scenario A.

#### Scenario C: The Edge Synchronization (Self-Healing)

*How a passive Contributor stays up to date.*

1. **Charlie** comes online after a weekend away.
2. **Charlie** grabs all new data: `peerp pull`
3. **Charlie** aligns his reality: `peerp consensus`
4. *Result:* If the Hubs passed new code over the weekend, Charlie's machine sees the quorum, ensures his local directory is clean, and magically snaps his files to the new canonical state.

#### Scenario D: The Topology Shift (Eating Your Own Dogfood)

*How the Owner enforces network reality.*

1. **Alice (Owner)** decides to add a new Delegate: `peerp promote <pubkey> bob_node`
2. **Alice's Guardrail triggers:** Her next `commit` is blocked because she has a pending Governance branch that her own machine hasn't validated.
3. **Alice** accepts her own reality: `peerp consensus`
4. *Result:* Alice's machine verifies her own Owner signature, extracts the new `trust.json` to disk, and updates the local threshold rules.

---

### The Underlying Philosophy

Your system currently functions in three distinct, disconnected layers. To complete the "Merge" successfully, a human (or automated agent) must bridge them:

1. **The Transport Layer (`sync` / `broadcast` / `pull`):** This is purely for **Data Availability**. It ensures that objects exist on hard drives.
2. **The Human Layer (`review` / `vote`):** This is the **Validation** step. The `vote` command is the formal declaration that a user has inspected the data and wants it to become the "Official Canonical Truth."
3. **The Consensus Layer (`consensus`):** This is the **Finalization**. It is a pure math engine that ignores all data not explicitly "voted" for.
