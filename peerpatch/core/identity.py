import os
import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


CONFIG_DIR = "/app/storage/.peerpatch"


def setup_identity(node_name):
    """Generates Ed25519 identity and genesis trust document."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    private_key_path = os.path.join(CONFIG_DIR, "id_ed25519")
    public_key_path = os.path.join(CONFIG_DIR, "id_ed25519.pub")

    if not os.path.exists(private_key_path):
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        with open(private_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(public_key_path, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            ))
        print("[+] Generated new cryptographic Ed25519 identity.")
    else:
        print("[*] Cryptographic identity already exists.")

    with open(public_key_path, "r") as f:
        pub_key_str = f.read().strip()

    trust_data = {
        "threshold": 1,
        "delegates": {
            pub_key_str: node_name
        }
    }

    with open(os.path.join(CONFIG_DIR, "trust.json"), "w") as f:
        json.dump(trust_data, f, indent=2)
    print(f"[+] Web of Trust initialized for {node_name}.")
