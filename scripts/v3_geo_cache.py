"""Calculate geographic lists before the V3 acoustic model enters RAM."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.models import get_meta_model, get_geo_v3_labels, GEO_V3_NAME, tflite
from utils.helpers import get_model_labels, MODEL_PATH
import numpy as np


def main():
    request = json.load(sys.stdin)
    if request.get('geo_v3'):
        labels = get_geo_v3_labels()
        model = tflite.Interpreter(os.path.join(MODEL_PATH, GEO_V3_NAME + '_FP32.tflite'), num_threads=1)
        model.allocate_tensors()
        input_info = model.get_input_details()[0]
        output_info = model.get_output_details()[0]
        if list(input_info['shape']) != [1, 3] or list(output_info['shape']) != [1, len(labels)]:
            raise ValueError('Unexpected geomodel tensor shape')
        result = {}
        yearly = np.zeros(len(labels), dtype=np.float32)
        for week in range(1, 49):
            model.set_tensor(input_info['index'], np.array([[request['lat'], request['lon'], week]], dtype=np.float32))
            model.invoke()
            probabilities = model.get_tensor(output_info['index'])[0]
            if not np.isfinite(probabilities).all() or probabilities.min() < 0 or probabilities.max() > 1:
                raise ValueError('Invalid geomodel probabilities')
            yearly = np.maximum(yearly, probabilities)
            result[str(week)] = np.flatnonzero(probabilities >= request['threshold']).tolist()
        result['-1'] = result['0'] = np.flatnonzero(yearly >= request['threshold']).tolist()
        json.dump(result, sys.stdout)
        return
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
