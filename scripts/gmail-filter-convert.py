#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "lib"))

from FilterConfig import main


if __name__ == "__main__":
  main(sys.argv[1:])
