import sys
import os
from dotenv import load_dotenv
load_dotenv()
# Force the current folder to be the absolute priority for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import uvicorn
from main import app  # <--- Import the app object directly!

if __name__ == "__main__":
    # Pass the actual app object directly instead of the string "main:app"
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)