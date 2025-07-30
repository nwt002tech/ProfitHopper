# /mount/src/profithopper/app.py
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Now import from src
from src.app import main

if __name__ == '__main__':
    main()