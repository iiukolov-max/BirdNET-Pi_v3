#!/usr/bin/env python3
"""Wait for the current worker's readiness marker, not just its process state."""
from model_switch import CONFIG, await_ready, values

if __name__ == '__main__':
    model = values(CONFIG.read_text())['MODEL']
    await_ready(model)
    print('Analyzer is ready: ' + model)
