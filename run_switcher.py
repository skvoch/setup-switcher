import os
import sys
from pathlib import Path


project_dir = Path(__file__).resolve().parent
venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    os.execv(
        str(venv_python),
        [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

from switcher.app import main


if __name__ == "__main__":
    raise SystemExit(main())
