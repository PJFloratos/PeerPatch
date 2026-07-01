import os
import json
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class IdentityManager:
    def __init__(self, config_dir="/app/storage/.peerpatch"):
        self.config_dir = config_dir
        self.private_key_path = os.path.join(self.config_dir, "id_ed25519")
        self.public_key_path = os.path.join(self.config_dir, "id_ed25519.pub")
        self.trust_file_path = os.path.join(self.config_dir, "trust.json")

    def setup_identity(self, node_name):
        """Generates Ed25519 identity and genesis trust document."""
        os.makedirs(self.config_dir, exist_ok=True)

        if not os.path.exists(self.private_key_path):
            self._generate_keys()
            print("[+] Generated new cryptographic Ed25519 identity.")
        else:
            print("[*] Cryptographic identity already exists.")

        self._initialize_trust_anchor(node_name)

    def get_peer_id(self):
        """Returns the 20-character hash of the local public key."""
        if not os.path.exists(self.public_key_path):
            return None

        with open(self.public_key_path, "r") as f:
            pub_key_str = f.read().strip()

        return hashlib.sha256(pub_key_str.encode()).hexdigest()

    def get_delegates(self):
        """Helper to return the list of Delegate node names."""
        if not os.path.exists(self.trust_file_path):
            return []
        with open(self.trust_file_path, "r") as f:
            return list(json.load(f).get("delegates", {}).values())

    def _generate_keys(self):
        """Internal method to handle cryptographic generation."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        with open(self.private_key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.OpenSSH,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        with open(self.public_key_path, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.OpenSSH,
                    format=serialization.PublicFormat.OpenSSH,
                )
            )

    def _initialize_trust_anchor(self, node_name):
        """Builds the Genesis trust document."""
        if os.path.exists(self.trust_file_path):
            print("[*] Network Trust Anchor found. Skipping local genesis creation.")
            return

        with open(self.public_key_path, "r") as f:
            pub_key_str = f.read().strip()

        trust_data = {
            "version": "2.0",
            "owner": pub_key_str,
            "threshold": 1,
            "delegates": {pub_key_str: node_name},
        }

        with open(self.trust_file_path, "w") as f:
            json.dump(trust_data, f, indent=2)
        print(f"[+] Web of Trust initialized for {node_name}.")

    def propose_governance_change(
        self, action, pub_key=None, name=None, threshold=None
    ):
        """Modifies the local trust.json to prepare a governance proposal."""
        if not os.path.exists(self.trust_file_path):
            print("[-] No trust.json found to modify.")
            return False

        with open(self.trust_file_path, "r") as f:
            trust_data = json.load(f)

        # --- Cryptographic Authorization Check ---
        if not os.path.exists(self.public_key_path):
            print("[-] Local public key not found.")
            return False

        with open(self.public_key_path, "r") as f:
            my_pub_key = f.read().strip()

        is_owner = trust_data.get("owner") == my_pub_key

        if not is_owner:
            print("[-] UNAUTHORIZED: Only the Owner can propose governance changes.")
            return False

        # 2. Process the Action
        if action == "add_delegate" and pub_key and name:
            trust_data["delegates"][pub_key] = name
            print(f"[*] Proposed adding Delegate: {name}")
        elif action == "remove_delegate" and pub_key:
            if pub_key in trust_data["delegates"]:
                del trust_data["delegates"][pub_key]
                print(f"[*] Proposed removing Delegate: {pub_key}...")
        else:
            print("[-] Invalid governance action.")
            return False

        # 3. Dynamic Threshold Calculation (> 50% Majority)
        delegate_count = len(trust_data["delegates"])
        new_threshold = (delegate_count // 2) + 1

        trust_data["threshold"] = new_threshold
        print(
            f"[*] Dynamic Threshold recalculated: {new_threshold}/{delegate_count} required for Consensus."
        )

        # 4. Save to disk
        with open(self.trust_file_path, "w") as f:
            json.dump(trust_data, f, indent=2)

        return True
