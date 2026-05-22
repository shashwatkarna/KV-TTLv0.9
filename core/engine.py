import threading
import json
import os
import time
from utils import get_current_timestamp, setup_logger

class KVStore:
    def __init__(self, aof_path="appendonly.aof"):
        """
        Initializes the Key-Value Store with AOF Persistence and Thread Safety.
        """
        self._store = {}
        self.aof_path = aof_path
        self.logger = setup_logger()
        self.lock = threading.RLock()
        
        # AOF File handle for appending commands
        self._aof_file = None
        
        # Background worker for active expiration
        self._running = True
        self._expiration_thread = threading.Thread(target=self._active_expiration_loop, daemon=True)

    def start(self):
        """Starts the KV engine, loads AOF, and starts background tasks."""
        self._load_aof()
        self._aof_file = open(self.aof_path, 'a')
        self._expiration_thread.start()
        self.logger.info("KV-MX9 Advanced Engine started.")

    def stop(self):
        """Stops the KV engine safely."""
        self._running = False
        if self._aof_file:
            self._aof_file.close()
        self.logger.info("KV-MX9 Advanced Engine stopped.")

    def _append_aof(self, command, key, value=None, ttl=None):
        """Appends a command to the AOF log."""
        if not self._aof_file:
            return
        log_entry = {
            "cmd": command,
            "key": key,
            "value": value,
            "ttl": ttl,
            "ts": get_current_timestamp()
        }
        try:
            self._aof_file.write(json.dumps(log_entry) + "\n")
            self._aof_file.flush()
        except Exception as e:
            self.logger.error(f"AOF write error: {e}")

    def _load_aof(self):
        """Reconstructs the state from the AOF log."""
        if not os.path.exists(self.aof_path):
            self.logger.info("No AOF file found. Starting fresh.")
            return

        self.logger.info("Loading from AOF...")
        with open(self.aof_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    cmd = entry["cmd"]
                    key = entry["key"]
                    
                    if cmd == "SET":
                        # We don't replay TTLs that have already expired in the past,
                        # but for simplicity we will just set them and let the active
                        # expiration clean them up immediately if needed.
                        expire_at = None
                        if entry.get("ttl") is not None:
                            # Reconstruct expire_at based on original timestamp and ttl
                            expire_at = entry["ts"] + entry["ttl"]
                            
                        self._store[key] = {
                            "value": entry["value"],
                            "expire_at": expire_at
                        }
                    elif cmd == "DELETE":
                        if key in self._store:
                            del self._store[key]
                except Exception as e:
                    self.logger.error(f"Error parsing AOF line: {e}")

    def _active_expiration_loop(self):
        """Background daemon thread to proactively clean expired keys."""
        while self._running:
            time.sleep(1) # Run every second
            keys_to_delete = []
            now = get_current_timestamp()
            
            with self.lock:
                for key, item in self._store.items():
                    expire_at = item.get("expire_at")
                    if expire_at is not None and now > expire_at:
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    self.logger.info(f"Active expiration: Key '{key}' expired. Deleting.")
                    self._delete_internal(key)

    def set(self, key, value, ttl=None):
        """Store a key-value pair, optionally with a TTL."""
        with self.lock:
            expire_at = None
            if ttl is not None:
                expire_at = get_current_timestamp() + ttl
                
            self._store[key] = {
                "value": value,
                "expire_at": expire_at
            }
            self._append_aof("SET", key, value, ttl)
            self.logger.info(f"Set key: '{key}' (TTL: {ttl}s)")

    def get(self, key):
        """Retrieve a value by key. Handles lazy expiration."""
        with self.lock:
            if key not in self._store:
                return None
                
            item = self._store[key]
            expire_at = item.get("expire_at")
            
            if expire_at is not None and get_current_timestamp() > expire_at:
                self.logger.info(f"Lazy expiration: Key '{key}' expired on read.")
                self._delete_internal(key)
                return None
                
            return item.get("value")

    def _delete_internal(self, key):
        """Internal delete without locking (to be called when lock is already held)."""
        if key in self._store:
            del self._store[key]
            self._append_aof("DELETE", key)
            return True
        return False

    def delete(self, key):
        """Delete a key from the store."""
        with self.lock:
            if self._delete_internal(key):
                self.logger.info(f"Deleted key: '{key}'")
                return True
            return False
