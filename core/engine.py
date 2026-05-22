import json
import os
from utils import get_current_timestamp, setup_logger

class KVStore:
    def __init__(self, persist_path=None):
        """
        Initializes the Key-Value Store.
        
        :param persist_path: Optional path to a JSON file for persistence.
        """
        self._store = {}
        self.persist_path = persist_path
        self.logger = setup_logger()
        self.logger.info("KV-MX9 initialized.")

    def set(self, key, value, ttl=None):
        """
        Store a key-value pair, optionally with a Time-To-Live (TTL).
        
        :param key: The key under which to store the value.
        :param value: The value to store.
        :param ttl: Optional Time-To-Live in seconds.
        """
        expire_at = None
        if ttl is not None:
            expire_at = get_current_timestamp() + ttl
            
        self._store[key] = {
            "value": value,
            "expire_at": expire_at
        }
        self.logger.info(f"Set key: '{key}' (TTL: {ttl}s)")

    def get(self, key):
        """
        Retrieve a value by key. Handles lazy expiration.
        
        :param key: The key to retrieve.
        :return: The value if it exists and hasn't expired, else None.
        """
        if key not in self._store:
            return None
            
        item = self._store[key]
        expire_at = item.get("expire_at")
        
        if expire_at is not None and get_current_timestamp() > expire_at:
            # Lazy expiration
            self.logger.info(f"Key '{key}' expired. Lazily deleting.")
            self.delete(key)
            return None
            
        return item.get("value")

    def delete(self, key):
        """
        Delete a key from the store.
        
        :param key: The key to delete.
        :return: True if deleted, False if key was not found.
        """
        if key in self._store:
            del self._store[key]
            self.logger.info(f"Deleted key: '{key}'")
            return True
        return False

    def save(self):
        """
        Save the current state of the store to the persistence file.
        """
        if not self.persist_path:
            self.logger.warning("No persist_path defined. Cannot save.")
            return False
            
        try:
            with open(self.persist_path, 'w') as f:
                json.dump(self._store, f)
            self.logger.info(f"Successfully saved store to {self.persist_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save store: {e}")
            return False

    def load(self):
        """
        Load the state of the store from the persistence file.
        """
        if not self.persist_path:
            self.logger.warning("No persist_path defined. Cannot load.")
            return False
            
        if not os.path.exists(self.persist_path):
            self.logger.info(f"Persistence file {self.persist_path} does not exist yet.")
            return False
            
        try:
            with open(self.persist_path, 'r') as f:
                self._store = json.load(f)
            self.logger.info(f"Successfully loaded store from {self.persist_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load store: {e}")
            return False
