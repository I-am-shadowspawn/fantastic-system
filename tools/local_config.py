#!/usr/bin/env python3
"""Make an ignored ESPHome entry point that tests packages from this checkout."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--hardware', choices=['p4', 's3'], default='p4')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
board = {'p4': 'waveshare-esp32-p4-wifi6-touch-lcd-7b',
         's3': 'waveshare-esp32-s3-touch-lcd-4.3'}[args.hardware]
source = (root / 'esphome/ha-console.yaml').read_text()
source, count = re.subn(
    r'^packages:\n.*?(?=^# Keep connectivity)',
    f'packages:\n  hardware: !include packages/hardware/{board}.yaml\n'
    '  homeassistant: !include packages/homeassistant.yaml\n'
    '  ui: !include packages/ui.yaml\n'
    '  heating: !include packages/heating.yaml\n\n',
    source, flags=re.M | re.S)
if count != 1:
    raise SystemExit('Could not locate the remote package block')
if args.hardware == 's3':
    source = source.replace('esphome:\n', 'esphome:\n  build_path: .esphome/build/ha-console-s3\n', 1)
output = root / f'esphome/.ci-{args.hardware}.yaml'
output.write_text(source)
print(output.relative_to(root))
