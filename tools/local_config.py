#!/usr/bin/env python3
"""Make an ignored ESPHome entry point that tests packages from this checkout."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
selection = parser.add_mutually_exclusive_group()
selection.add_argument('--hardware', choices=['p4', 's3'], help='Backwards-compatible hardware selection')
selection.add_argument('--configuration', choices=['p4', 's3', 'p4-c6', 'recovery'])
args = parser.parse_args()
configuration = args.configuration or args.hardware or 'p4'
root = Path(__file__).resolve().parents[1]
board = ('waveshare-esp32-s3-touch-lcd-4.3' if configuration == 's3'
         else 'waveshare-esp32-p4-wifi6-touch-lcd-7b')
source_name = 'c6-recovery.yaml' if configuration == 'recovery' else 'ha-console.yaml'
source = (root / 'esphome' / source_name).read_text()
includes = f'packages:\n  hardware: !include packages/hardware/{board}.yaml\n'
if configuration != 'recovery':
    includes += ('  homeassistant: !include packages/homeassistant.yaml\n'
                 '  ui: !include packages/ui.yaml\n'
                 '  heating: !include packages/heating.yaml\n')
if configuration == 'p4-c6':
    includes += '  c6_maintenance: !include packages/c6-maintenance.yaml\n'
source, count = re.subn(r'^packages:\n.*?(?=^# Keep connectivity|^esphome:)',
                         includes + '\n', source, flags=re.M | re.S)
if count != 1:
    raise SystemExit('Could not locate the remote package block')
if configuration == 's3':
    # Preserve the existing S3 cache location.
    source = source.replace('esphome:\n', 'esphome:\n  build_path: .esphome/build/ha-console-s3\n', 1)
elif configuration in ('p4-c6', 'recovery'):
    source = source.replace('esphome:\n', f'esphome:\n  build_path: build/ha-console-{configuration}\n', 1)
output = root / f'esphome/.ci-{configuration}.yaml'
output.write_text(source)
print(output.relative_to(root))
