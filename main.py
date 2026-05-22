import subprocess
import time
import sys
import os

def main():
    print("=== KV-TTLv0.9 Orchestrator ===")
    
    # 1. Start the Go Database Core
    print("Starting Go Core Database Engine...")
    go_core_dir = os.path.join(os.path.dirname(__file__), "go_core")
    
    go_binary = os.path.join(go_core_dir, "kv-ttl.exe")
    if not os.path.exists(go_binary):
        print(f"Error: Compiled Go binary not found at {go_binary}. Please compile it first.")
        sys.exit(1)
        
    try:
        go_proc = subprocess.Popen(
            [go_binary],
            cwd=go_core_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"Error starting Go core database engine: {e}")
        sys.exit(1)

    # Give the Go server a moment to start and bind to port 9000
    time.sleep(2)
    if go_proc.poll() is not None:
        stdout, stderr = go_proc.communicate()
        print(f"Go Database Core failed to start:\nStdout: {stdout}\nStderr: {stderr}")
        sys.exit(1)
        
    print("Go Database Core is running.")

    # 2. Start the Node.js API Gateway
    print("Starting Node.js Express Gateway...")
    gateway_dir = os.path.join(os.path.dirname(__file__), "gateway")
    
    node_proc = subprocess.Popen(
        ["node", "server.js"],
        cwd=gateway_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(2)
    if node_proc.poll() is not None:
        stdout, stderr = node_proc.communicate()
        print(f"Node.js Gateway failed to start:\nStdout: {stdout}\nStderr: {stderr}")
        go_proc.terminate()
        sys.exit(1)
        
    print("Node.js Gateway is running on http://localhost:8000")
    print("\nSystem running. Press Ctrl+C to terminate both servers.")

    try:
        # Monitor processes
        while True:
            go_status = go_proc.poll()
            node_status = node_proc.poll()
            
            if go_status is not None:
                print("Go Core Database Engine terminated unexpectedly.")
                break
            if node_status is not None:
                print("Node.js API Gateway terminated unexpectedly.")
                break
                
            # Log some output from processes to console
            # To keep things clean, we can just read line by line or wait
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        go_proc.terminate()
        node_proc.terminate()
        print("Servers stopped.")

if __name__ == "__main__":
    main()
