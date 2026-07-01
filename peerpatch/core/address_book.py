import os
import json


class AddressBook:
    def __init__(self, config_dir):
        self.file_path = os.path.join(config_dir, "peers.json")

    def _read(self):
        if not os.path.exists(self.file_path):
            return {"downstream_nodes": []}
        with open(self.file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"downstream_nodes": []}

    def _write(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_downstream(self):
        return self._read().get("downstream_nodes", [])

    def add(self, peer):
        data = self._read()
        if peer not in data.setdefault("downstream_nodes", []):
            data["downstream_nodes"].append(peer)
            self._write(data)
            print(f"[*] Added {peer} to Address Book as a downstream subscriber.")

    def remove(self, peer):
        data = self._read()
        if peer in data.get("downstream_nodes", []):
            data["downstream_nodes"].remove(peer)
            self._write(data)
            print(
                f"[*] Cleaned routing table: {peer} removed from downstream broadcasts."
            )
