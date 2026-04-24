#!/usr/bin/env python
import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DEPS_DIR = ROOT_DIR / ".deps"

if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django não está instalado. Instale as dependências com "
            "`pip install -r requirements.txt`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
