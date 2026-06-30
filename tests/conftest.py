import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Make both the package (src) and the top level agents/tools dirs importable
# without installation.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
