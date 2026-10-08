"""Exercise both geographic worker branches without loading production models."""
import io
import json
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import patch
import numpy as np

WORKER = Path(__file__).resolve().parents[1] / 'scripts/v3_geo_cache.py'

class GeoWorkerTest(unittest.TestCase):
    def run_worker(self, request):
        models = types.ModuleType('utils.models')
        helpers = types.ModuleType('utils.helpers')
        calls = []
        class Interpreter:
            def __init__(self, model_path, num_threads):
                calls.append(model_path)
            def allocate_tensors(self): pass
            def get_input_details(self): return [{'shape': [1, 3], 'index': 0}]
            def get_output_details(self): return [{'shape': [1, 2], 'index': 1}]
            def set_tensor(self, index, value):
                assert value.shape == (1, 3)
            def invoke(self): pass
            def get_tensor(self, index): return np.array([[.2, .8]], dtype=np.float32)
        class Legacy:
            def set_meta_data(self, *args): pass
            def get_species_list(self, labels): return [labels[1]]
        models.get_meta_model = lambda *args: Legacy()
        models.get_geo_v3_labels = lambda: ['a', 'b']
        models.GEO_V3_NAME = 'fixture'
        models.tflite = types.SimpleNamespace(Interpreter=Interpreter)
        helpers.get_model_labels = lambda *args: ['a', 'b']
        helpers.MODEL_PATH = '/fixture/models'
        output = io.StringIO()
        with patch.dict(sys.modules, {'utils': types.ModuleType('utils'), 'utils.models': models, 'utils.helpers': helpers}), patch.object(sys, 'stdin', io.StringIO(json.dumps(request))), patch.object(sys, 'stdout', output), patch.object(sys, 'path', list(sys.path)):
            runpy.run_path(str(WORKER), run_name='__main__')
        return json.loads(output.getvalue()), calls

    def test_v3_worker_constructs_model_path_and_all_weeks(self):
        result, calls = self.run_worker({'geo_v3': True, 'lat': 55, 'lon': 37, 'threshold': .5})
        self.assertEqual(Path(calls[0]).name, 'fixture_FP32.tflite')
        self.assertEqual(set(result), {str(i) for i in range(-1, 49)})
        self.assertTrue(all(value == [1] for value in result.values()))

    def test_legacy_worker_preserves_calendar_indices(self):
        result, calls = self.run_worker({'lat': 55, 'lon': 37, 'version': '1'})
        self.assertEqual(calls, [])
        self.assertEqual(set(result), {str(i) for i in range(-1, 54)})
        self.assertTrue(all(value == [1] for value in result.values()))

if __name__ == '__main__': unittest.main()
