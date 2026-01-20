from pathlib import Path
import re as _re

path = Path("src/oncology_registry_copilot/evaluation.py")
lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

# If module-level import already exists, do nothing
if any(line == "import re" for line in lines[:30]):
    print("top-level import re already present")
else:
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if (not inserted) and line.strip() == "import pandas as pd":
            out.append("import re")
            inserted = True

    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")
    print("added top-level import re")
