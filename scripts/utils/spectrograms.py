"""Spectrogram rendering without loading the inference/reporting pipeline."""
import os
from pathlib import Path
import subprocess
import tempfile


def render_spectrogram(in_file, title, comment, raw=0):
    # Pillow is only needed when an image is actually requested.
    from PIL import Image, ImageDraw, ImageFont
    from .helpers import get_font
    destination = Path(str(in_file) + '.png')
    descriptor, temporary = tempfile.mkstemp(suffix='.png', dir=destination.parent)
    os.close(descriptor)
    try:
        args = ['sox', '-V1', str(in_file), '-n', 'remix', '1', 'rate', '24k',
                'spectrogram', '-t', '', '-c', '', '-o', temporary]
        if int(raw):
            args.append('-r')
        subprocess.run(args, check=True, capture_output=True, timeout=20)
        with Image.open(temporary) as image:
            draw = ImageDraw.Draw(image)
            title_font = ImageFont.truetype(get_font()['path'], 13)
            _, _, width, _ = draw.textbbox((0, 0), title, font=title_font)
            draw.text(((image.width-width)/2, 6), title, fill='white', font=title_font)
            comment_font = ImageFont.truetype(get_font()['path'], 11)
            _, _, _, height = draw.textbbox((0, 0), comment, font=comment_font)
            draw.text((1, image.height-height-1), comment, fill='white', font=comment_font)
            image.save(temporary)
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
