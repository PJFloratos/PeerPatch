### **PeerPatch Architecture: The Local Sandbox**

**The Objective:** To simulate a decentralized, peer-to-peer Git network on a single machine without needing external servers, physical laptops, or third-party brokers (like GitHub).

#### **1. The Network Layer (Docker Compose)**

* **The Design:** We use `docker-compose.yml` to spin up three independent containers (`alice_node`, `bob_node`, `charlie_node`).
* **The "Why":** Docker Compose automatically creates an isolated virtual bridge network (`peerp_network`). This acts as our localized Tailscale mesh. It provides automatic DNS resolution, meaning Alice can `ping bob_node` exactly as she would ping a real IP address on a production VPN.

#### **2. The Node Operating System (Dockerfile)**

* **The Base:** `python:3.11-slim` provides a lightweight Linux environment capable of running our cryptographic scripts.
* **The Transport (SSH & sshpass):** Because Git natively communicates over SSH, we baked `openssh-server` directly into the containers. We also added `sshpass` and disabled `StrictHostKeyChecking` to allow the automated Python scripts to seamlessly fetch objects between nodes without freezing the terminal to ask for passwords or fingerprint confirmations.
* **The Hotspot DNS Fix:** We forced the Docker daemon to use `8.8.8.8` (Google) and `1.1.1.1` (Cloudflare). This bypasses restrictive mobile carrier CGNATs or corporate firewalls that block standard Docker Hub image pulls.

#### **3. State & Persistence (Volume Mapping)**

* **The Design:** The `docker-compose.yml` binds local host folders (e.g., `./nodes/alice_data`) directly into the container's `/app/storage` directory.
* **The "Why":** Containers are ephemeral (temporary). If Alice's container crashes or gets rebuilt, her cryptographic keys (`.peerpatch/`) and Git history (`.git/`) would be destroyed. By mapping volumes, the host machine acts as the permanent hard drive, ensuring state survives between reboots.
