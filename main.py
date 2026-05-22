import uvicorn
from utils import setup_logger

logger = setup_logger("main")

def main():
    logger.info("Starting KV-MX9 Advanced REST Server...")
    # Start the FastAPI server using Uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
