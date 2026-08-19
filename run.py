import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    import uvicorn
    from backend.main import app
    print("\n[BAUN BIDB Chatbot Backend Sunucusu Baslatiliyor...]")
    print("[Adres]: http://127.0.0.1:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
