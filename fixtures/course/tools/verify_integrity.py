"""Check packaged files against MANIFEST_SHA256.json (stdlib only).
New outputs produced after extraction are ignored; packaged files must not change.
"""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST_SHA256.json').read_text(encoding='utf8'))
errors=[]
for rel,expected in manifest['files'].items():
    p=root/rel
    if not p.is_file():errors.append('MISSING '+rel)
    elif hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append('CHANGED '+rel)
print(f"Checked {len(manifest['files'])} packaged files; failures={len(errors)}")
for x in errors:print(x)
sys.exit(bool(errors))
