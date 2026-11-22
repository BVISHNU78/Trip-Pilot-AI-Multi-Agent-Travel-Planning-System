"""Every test runs in mock mode: no API keys, no network, no quota."""
import os
import sys
from pathlib import Path

os.environ["TRAVEL_MOCK"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
