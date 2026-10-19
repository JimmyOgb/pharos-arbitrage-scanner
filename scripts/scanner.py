#!/usr/bin/env python3
"""
SkillEngine Executable Entrypoint for Pharos Arbitrage Scanner
Delegates directly to scanner.cli.main()
"""

import sys
from pathlib import Path

# Ensure root package is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scanner.cli import main

if __name__ == "__main__":
    main()
