"""Enable/disable an already installed optimized V3; effective at next load."""
import json
import os
from pathlib import Path
import sys

path = Path('/etc/birdnet/v3-runtime.json')
if sys.argv[1:] not in (['enable'], ['disable'], ['status']):
    raise SystemExit('Expected enable, disable, or status')
if not path.exists():
    raise SystemExit('Optimized V3 has not been installed; original runtime is active')
profile = json.loads(path.read_text())
if sys.argv[1] != 'status':
    profile['enabled'] = sys.argv[1] == 'enable'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(profile, indent=2))
    os.chmod(temporary, 0o644)
    temporary.replace(path)
print(json.dumps({'enabled': profile['enabled'], 'effective': 'next analyzer model load',
                  'model': profile['model'], 'fallback': 'original full V3 model without the weight cache',
                  'unified_runtime': profile.get('unified_runtime', False)}))
