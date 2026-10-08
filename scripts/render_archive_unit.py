"""Generate the archive service for the actual installation owner and path."""
import pwd
from pathlib import Path
import sys


def render(root, user, charts=False):
    root = Path(root).resolve()
    # Values enter systemd syntax, not a shell. Reject control characters;
    # quote paths and escape systemd's percent specifiers.
    if any(character in user for character in '\n\r\x00') or not user or any(character.isspace() for character in user):
        raise ValueError('Invalid installation user')
    if any(character in str(root) for character in '\n\r\x00'):
        raise ValueError('Invalid installation path')
    path = str(root).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return (root / ('templates/birdnet-archive-charts.service' if charts else 'templates/birdnet-archive-analysis.service')).read_text().replace(
        '@BIRDNET_USER@', user).replace('@BIRDNET_ROOT@', path)


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    sys.stdout.write(render(root, pwd.getpwuid(root.stat().st_uid).pw_name, charts=sys.argv[1:]==['--charts']))
