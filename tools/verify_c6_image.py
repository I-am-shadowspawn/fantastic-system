#!/usr/bin/env python3
"""Verify the recovery image pin, chip and app version without accessing a device."""
import argparse
import hashlib
from pathlib import Path
import struct
from urllib.request import urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]


def recovery_pin():
    # BaseLoader reads substitutions/tags as text without resolving includes.
    config = yaml.load((ROOT / 'esphome/c6-recovery.yaml').read_text(), Loader=yaml.BaseLoader)
    image = config['update'][0]
    return image['url'], image['sha256'], config['substitutions']['c6_target_version']


def verify_image(data, expected_sha256, expected_version):
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Recovery image SHA256 does not match the reviewed pin')
    if len(data) < 288 or data[0] != 0xE9:
        raise ValueError('Not an ESP application image')
    if struct.unpack_from('<H', data, 12)[0] != 13:
        raise ValueError('Recovery image does not target ESP32-C6')
    # ESP image header (24), first segment header (8), then esp_app_desc_t.
    if struct.unpack_from('<I', data, 32)[0] != 0xABCD5432:
        raise ValueError('Missing ESP application description')
    version = data[48:80].split(b'\0', 1)[0].decode('ascii')
    if version != expected_version:
        raise ValueError(f'Application version is {version!r}, expected {expected_version!r}')
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, help='Inspect a local image instead of downloading the pinned URL')
    args = parser.parse_args()
    url, digest, version = recovery_pin()
    if args.image:
        data = args.image.read_bytes()
    else:
        with urlopen(url, timeout=30) as response:
            data = response.read()
    verify_image(data, digest, version)
    print(f'Verified ESP32-C6 {version}: {len(data):,} bytes, SHA256 {digest}')
    print('This is an application image for the SDIO updater, not a complete UART flash layout.')


if __name__ == '__main__':
    main()
