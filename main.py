import time
from core.engine import KVStore

def main():
    print("--- Starting KV-MX9 Demo ---")
    
    # 1. Basic CRUD Operations
    print("\n[Basic CRUD]")
    kv = KVStore()
    kv.set("user_1", {"name": "Alice", "role": "admin"})
    kv.set("user_2", {"name": "Bob", "role": "user"})
    
    print(f"Get 'user_1': {kv.get('user_1')}")
    print(f"Get 'user_3' (not set): {kv.get('user_3')}")
    
    kv.delete("user_2")
    print(f"Get 'user_2' after delete: {kv.get('user_2')}")
    
    # 2. TTL (Time-To-Live) Demonstration
    print("\n[TTL Demonstration]")
    kv.set("session_token", "abc123xyz", ttl=2) # 2 seconds TTL
    print(f"Get 'session_token' immediately: {kv.get('session_token')}")
    
    print("Waiting for 3 seconds...")
    time.sleep(3)
    
    print(f"Get 'session_token' after waiting: {kv.get('session_token')}")
    
    # 3. Persistence Demonstration
    print("\n[Persistence Demonstration]")
    persist_file = "data.json"
    kv_persist = KVStore(persist_path=persist_file)
    
    # Set data and save
    kv_persist.set("config_theme", "dark")
    kv_persist.set("config_lang", "en")
    kv_persist.save()
    
    # Simulate restart by creating a new instance
    print("\nSimulating restart...")
    kv_restarted = KVStore(persist_path=persist_file)
    kv_restarted.load()
    
    print(f"Get 'config_theme' from loaded store: {kv_restarted.get('config_theme')}")
    print(f"Get 'config_lang' from loaded store: {kv_restarted.get('config_lang')}")
    
    print("\n--- Demo Completed ---")

if __name__ == "__main__":
    main()
