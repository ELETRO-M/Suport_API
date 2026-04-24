import sys
from pathlib import Path

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except Exception:
    pass


ROOT_DIR = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT_DIR / ".deps"

if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))
