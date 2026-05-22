package main

import (
	"bufio"
	"fmt"
	"log"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Item struct {
	Value    string
	ExpireAt int64 // Unix timestamp in seconds, 0 means no expiration
}

type KVStore struct {
	mu      sync.RWMutex
	store   map[string]Item
	aofPath string
	aofFile *os.File
}

func NewKVStore(aofPath string) *KVStore {
	return &KVStore{
		store:   make(map[string]Item),
		aofPath: aofPath,
	}
}

func (s *KVStore) Start() {
	s.loadAof()
	var err error
	s.aofFile, err = os.OpenFile(s.aofPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatalf("Failed to open AOF file: %v", err)
	}
	go s.activeExpirationLoop()
	log.Println("KV-TTLv0.9 Engine Started.")
}

func (s *KVStore) Close() {
	if s.aofFile != nil {
		s.aofFile.Close()
	}
}

func (s *KVStore) appendAof(op, key string, ttl int64, val string) {
	if s.aofFile == nil {
		return
	}
	// Format: OP KEY TTL TS VALUE
	// To handle value with newlines/spaces, we replace newlines in value with a placeholder, or write it cleanly
	// Since TCP commands are single-line, we assume values don't contain raw newlines.
	valClean := strings.ReplaceAll(val, "\n", "\\n")
	logLine := fmt.Sprintf("%s %s %d %d %s\n", op, key, ttl, time.Now().Unix(), valClean)
	if _, err := s.aofFile.WriteString(logLine); err != nil {
		log.Printf("AOF write error: %v\n", err)
	}
}

func (s *KVStore) loadAof() {
	if _, err := os.Stat(s.aofPath); os.IsNotExist(err) {
		log.Println("No AOF file found. Starting fresh.")
		return
	}
	log.Println("Replaying AOF...")
	file, err := os.Open(s.aofPath)
	if err != nil {
		log.Printf("Failed to open AOF for replay: %v\n", err)
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		parts := strings.SplitN(line, " ", 5)
		if len(parts) < 4 {
			continue
		}
		op := parts[0]
		key := parts[1]
		ttl, _ := strconv.ParseInt(parts[2], 10, 64)
		ts, _ := strconv.ParseInt(parts[3], 10, 64)
		
		val := ""
		if len(parts) == 5 {
			val = strings.ReplaceAll(parts[4], "\\n", "\n")
		}

		if op == "SET" {
			expireAt := int64(0)
			if ttl > 0 {
				expireAt = ts + ttl
			}
			s.store[key] = Item{Value: val, ExpireAt: expireAt}
		} else if op == "DEL" {
			delete(s.store, key)
		}
	}
	log.Printf("AOF replay complete. Loaded %d keys.\n", len(s.store))
}

func (s *KVStore) activeExpirationLoop() {
	for {
		time.Sleep(1 * time.Second)
		now := time.Now().Unix()
		s.mu.Lock()
		for k, v := range s.store {
			if v.ExpireAt > 0 && now > v.ExpireAt {
				delete(s.store, k)
				s.appendAof("DEL", k, 0, "")
				log.Printf("[ACTIVE EXPIRY] Deleted expired key: %s\n", k)
			}
		}
		s.mu.Unlock()
	}
}

func (s *KVStore) Set(key string, val string, ttl int64) {
	s.mu.Lock()
	defer s.mu.Unlock()

	expireAt := int64(0)
	if ttl > 0 {
		expireAt = time.Now().Unix() + ttl
	}

	s.store[key] = Item{Value: val, ExpireAt: expireAt}
	s.appendAof("SET", key, ttl, val)
	log.Printf("SET: %s = %s (TTL: %d)\n", key, val, ttl)
}

func (s *KVStore) Get(key string) (string, bool) {
	s.mu.RLock()
	item, found := s.store[key]
	s.mu.RUnlock()

	if !found {
		return "", false
	}

	if item.ExpireAt > 0 && time.Now().Unix() > item.ExpireAt {
		// Lazy delete
		s.mu.Lock()
		// Double check under write lock
		if item, found = s.store[key]; found && item.ExpireAt > 0 && time.Now().Unix() > item.ExpireAt {
			delete(s.store, key)
			s.appendAof("DEL", key, 0, "")
			log.Printf("[LAZY EXPIRY] Deleted expired key: %s\n", key)
		}
		s.mu.Unlock()
		return "", false
	}

	return item.Value, true
}

func (s *KVStore) Delete(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, found := s.store[key]; found {
		delete(s.store, key)
		s.appendAof("DEL", key, 0, "")
		log.Printf("DEL: %s\n", key)
		return true
	}
	return false
}

func main() {
	store := NewKVStore("appendonly.aof")
	store.Start()
	defer store.Close()

	listener, err := net.Listen("tcp", "0.0.0.0:9000")
	if err != nil {
		log.Fatalf("Failed to start TCP listener: %v", err)
	}
	defer listener.Close()
	log.Println("TCP Socket Server listening on :9000")

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Failed to accept connection: %v\n", err)
			continue
		}
		go handleConnection(conn, store)
	}
}

func handleConnection(conn net.Conn, store *KVStore) {
	defer conn.Close()
	reader := bufio.NewReader(conn)
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return // Connection closed by client
		}
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		parts := strings.SplitN(line, " ", 2)
		cmd := strings.ToUpper(parts[0])

		switch cmd {
		case "SET":
			if len(parts) < 2 {
				conn.Write([]byte("ERR INVALID_ARGS\n"))
				continue
			}
			// Format: SET <key> <ttl> <value>
			subParts := strings.SplitN(parts[1], " ", 3)
			if len(subParts) < 3 {
				conn.Write([]byte("ERR INVALID_ARGS\n"))
				continue
			}
			key := subParts[0]
			ttl, err := strconv.ParseInt(subParts[1], 10, 64)
			if err != nil {
				conn.Write([]byte("ERR INVALID_TTL\n"))
				continue
			}
			val := subParts[2]
			store.Set(key, val, ttl)
			conn.Write([]byte("OK\n"))

		case "GET":
			if len(parts) < 2 {
				conn.Write([]byte("ERR INVALID_ARGS\n"))
				continue
			}
			key := parts[1]
			val, found := store.Get(key)
			if !found {
				conn.Write([]byte("ERR NOT_FOUND\n"))
			} else {
				// Escape newlines back to keep protocol single line per response
				valClean := strings.ReplaceAll(val, "\n", "\\n")
				conn.Write([]byte(fmt.Sprintf("VALUE %s\n", valClean)))
			}

		case "DEL":
			if len(parts) < 2 {
				conn.Write([]byte("ERR INVALID_ARGS\n"))
				continue
			}
			key := parts[1]
			if store.Delete(key) {
				conn.Write([]byte("DELETED\n"))
			} else {
				conn.Write([]byte("ERR NOT_FOUND\n"))
			}

		default:
			conn.Write([]byte("ERR UNKNOWN_COMMAND\n"))
		}
	}
}
