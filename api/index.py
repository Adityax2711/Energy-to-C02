import sys
import os

# Add the project root directory to sys.path so 'app' can be imported by Vercel
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app

# Expose both 'app' and 'handler' for Vercel Serverless Python runtime
handler = app
