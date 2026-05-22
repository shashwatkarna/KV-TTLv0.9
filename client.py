import socket
import sys

def main():
    print("=== KV-TTLv0.9 Admin CLI ===")
    print("Connecting to database at localhost:9000...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 9000))
        print("Connected! Type help for commands, exit to quit.\n")
    except Exception as e:
        print(f"Error connecting to database core: {e}")
        print("Make sure the database is running (e.g. python main.py).")
        sys.exit(1)
        
    while True:
        try:
            cmd = input("kv-ttl> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ('exit', 'quit'):
                break
            if cmd.lower() == 'help':
                print("Commands:")
                print("  SET <key> <ttl_seconds> <value>  - Store a value (0 ttl = no expiration)")
                print("  GET <key>                        - Retrieve a value")
                print("  DEL <key>                        - Delete a key")
                continue
            
            s.sendall((cmd + '\n').encode('utf-8'))
            reply = s.recv(4096).decode('utf-8')
            print(reply, end="")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Connection lost: {e}")
            break
            
    s.close()

if __name__ == '__main__':
    main()
