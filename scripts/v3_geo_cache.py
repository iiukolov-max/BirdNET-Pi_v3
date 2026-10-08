"""Calculate V2 geographic lists before the V3 acoustic model enters RAM."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.models import get_meta_model
from utils.helpers import get_model_labels


def main():
    request = json.load(sys.stdin)
    model = get_meta_model('BirdNET_GLOBAL_6K_V2.4_Model_FP16', request['version'])
    labels = get_model_labels('BirdNET_GLOBAL_6K_V2.4_Model_FP16')
    indices = {name: i for i, name in enumerate(labels)}
    result = {}
    # Include all calendar week values plus the unknown-date sentinel.
    for week in range(-1, 54):
        model.set_meta_data(request['lat'], request['lon'], week)
        result[str(week)] = [indices[name] for name in model.get_species_list(labels)]
    json.dump(result, sys.stdout)


if __name__ == '__main__':
    main()
