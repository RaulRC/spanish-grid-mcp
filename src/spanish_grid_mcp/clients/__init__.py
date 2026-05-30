from pathlib import Path

from dotenv import load_dotenv

_dotenv_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_dotenv_path)
