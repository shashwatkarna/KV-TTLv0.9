from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from core.engine import KVStore

app = FastAPI(title="KV-MX9 API", description="High-Tech In-Memory Key-Value Store")
kv_store = KVStore(aof_path="appendonly.aof")

# Pydantic models for request bodies
class SetRequest(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = None

@app.on_event("startup")
async def startup_event():
    kv_store.start()

@app.on_event("shutdown")
async def shutdown_event():
    kv_store.stop()

@app.post("/set")
async def set_key(req: SetRequest):
    kv_store.set(req.key, req.value, req.ttl)
    return {"status": "success", "message": f"Key '{req.key}' set successfully."}

@app.get("/get/{key}")
async def get_key(key: str):
    value = kv_store.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found or expired")
    return {"key": key, "value": value}

@app.delete("/delete/{key}")
async def delete_key(key: str):
    deleted = kv_store.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "success", "message": f"Key '{key}' deleted successfully."}
