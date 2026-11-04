"""pytest configuration — ensure project root is on sys.path for all tests."""

import sys
from pathlib import Path

# Insert the project root so imports like `from config import settings` resolve without
# needing to run pytest from a specific directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
