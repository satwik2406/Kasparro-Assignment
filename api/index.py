import sys
from pathlib import Path

# Ensure root directory is in sys.path so 'src' modules resolve correctly in Vercel Serverless
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.api import app
