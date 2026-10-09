"""Transactional canonical import bridge; one native library in the profile."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def switch(python, stage):
    site = Path(subprocess.check_output([str(python), '-c',
        'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip()).resolve()
    backup = stage / 'original-python-package'
    backup.mkdir()
    targets = [stage / 'tflite_runtime', *stage.glob('tflite_runtime-*.dist-info')]
    if len(targets) != 2 or not targets[0].is_dir():
        raise ValueError('Canonical runtime bridge wheel is incomplete')
    old = [site / 'tflite_runtime', *site.glob('tflite_runtime-*.dist-info')]
    saved = []
    linked = []
    try:
        for path in old:
            if path.exists() or path.is_symlink():
                os.replace(path, backup / path.name)
                saved.append(path.name)
        for path in targets:
            link = site / path.name
            link.symlink_to(path, target_is_directory=True)
            linked.append(path.name)
        subprocess.run([str(python), '-c',
            'import tflite_runtime.interpreter as t; print(t.__file__); assert t.Interpreter'],
            check=True, timeout=60)
    except BaseException:
        rollback({'site': str(site), 'backup': str(backup), 'saved': saved, 'linked': linked})
        raise
    result = {'site': str(site), 'backup': str(backup), 'saved': saved, 'linked': linked}
    (stage / 'canonical-switch.json').write_text(json.dumps(result, indent=2))
    return result


def rollback(saved):
    site, backup = Path(saved['site']), Path(saved['backup'])
    for name in saved['linked']:
        path = site / name
        if path.is_symlink():
            path.unlink()
    for name in saved['saved']:
        if (backup / name).exists() or (backup / name).is_symlink():
            os.replace(backup / name, site / name)


def finish(saved, stage):
    backup = Path(saved['backup'])
    if backup.parent.resolve() != stage.resolve() or backup.name != 'original-python-package':
        raise ValueError('Unexpected original-package backup path')
    shutil.rmtree(backup)
