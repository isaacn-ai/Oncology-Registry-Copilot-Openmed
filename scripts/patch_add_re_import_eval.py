from pathlib import Path

path = Path("src/oncology_registry_copilot/evaluation.py")
lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

# If already present, do nothing
if any(l.strip() == "import re" for l in lines):
    print("import re already present")
else:
    out = []
    inserted = False
    for l in lines:
        out.append(l)
        if (not inserted) and l.strip() == "import pandas as pd":
            out.append("import re")
            inserted = True

    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")
    print("added import re")
