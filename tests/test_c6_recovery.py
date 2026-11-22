"""Image integrity and no-automatic-flashing policies for C6 recovery."""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

import yaml

from tools.verify_c6_image import recovery_pin, verify_image

ROOT = Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('!lambda', lambda loader, node: loader.construct_scalar(node))
RECOVERY = yaml.load((ROOT / 'esphome/c6-recovery.yaml').read_text(), Loader=Loader)
MAINTENANCE = yaml.safe_load((ROOT / 'esphome/packages/c6-maintenance.yaml').read_text())


class C6RecoveryTests(unittest.TestCase):
    def image(self, chip=13, version='3.1.0', magic=0xABCD5432):
        data = bytearray(288)
        data[0] = 0xE9
        data[1] = 1
        struct.pack_into('<H', data, 12, chip)
        struct.pack_into('<II', data, 24, 0x42000000, 256)
        struct.pack_into('<I', data, 32, magic)
        encoded = version.encode('ascii')
        data[48:48+len(encoded)] = encoded
        return bytes(data)

    def verify(self, data):
        return verify_image(data, hashlib.sha256(data).hexdigest(), recovery_pin()[2])

    def test_reviewed_pin_is_complete(self):
        url, digest, version = recovery_pin()
        self.assertEqual(version, '3.1.0')
        self.assertEqual(url, f'https://esphome.github.io/esp-hosted-firmware/v{version}/network_adapter_esp32c6.bin')
        self.assertEqual(digest, '4ac31b47eb3bf7e239e657173dcb317433a2cc7799a4ec518aeda9856d06d614')
        self.assertEqual(self.verify(self.image()), version)

    def test_corrupt_or_wrong_target_images_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            verify_image(self.image(), '0' * 64, '3.1.0')
        for data, message in [(self.image(chip=9), 'ESP32-C6'),
                              (self.image(version='1'), 'Application version'),
                              (self.image(magic=0), 'application description'),
                              (b'bad', 'ESP application image')]:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.verify(data)

    def test_recovery_requires_no_network_or_secrets(self):
        for domain in ('wifi', 'api', 'ota', 'http_request'):
            self.assertNotIn(domain, RECOVERY)
        self.assertNotIn('!secret', (ROOT / 'esphome/c6-recovery.yaml').read_text())
        self.assertEqual(RECOVERY['update'][0]['type'], 'embedded')
        self.assertNotIn('on_update_available', RECOVERY['update'][0])
        self.assertNotIn('update.perform', str(RECOVERY['esphome']['on_boot']))
        self.assertIn('recovery_install', str(RECOVERY['lvgl']))
        actions = next(s for s in RECOVERY['script'] if s['id'] == 'recovery_install')['then'][0]['if']['then']
        self.assertIn('recovery_attempted) = true', actions[0]['lambda'])
        self.assertEqual(actions[1]['delay'], '250ms')
        self.assertEqual(actions[2]['update.perform'], 'c6_recovery_update')

    def test_manual_production_updater_keeps_watchdog_default(self):
        updater = MAINTENANCE['update'][0]
        self.assertEqual(updater['type'], 'http')
        self.assertEqual(updater['update_interval'], '6h')
        self.assertEqual(updater['source'], 'https://esphome.github.io/esp-hosted-firmware/manifest/esp32c6.json')
        self.assertNotIn('on_update_available', updater)
        self.assertNotIn('esphome', MAINTENANCE)
        self.assertNotIn('esp32', MAINTENANCE)
        self.assertTrue(MAINTENANCE['http_request']['verify_ssl'])
        self.assertEqual(RECOVERY['esp32']['framework']['sdkconfig_options']['CONFIG_ESP_TASK_WDT_TIMEOUT_S'], '30')
        for filename in ('esphome/ha-console.yaml', 'esphome/packages/hardware/waveshare-esp32-p4-wifi6-touch-lcd-7b.yaml'):
            self.assertNotIn('CONFIG_ESP_TASK_WDT_TIMEOUT_S', (ROOT / filename).read_text())

    @unittest.skipUnless(shutil.which('g++'), 'Requires a native C++ compiler')
    def test_install_gate_blocks_repeat_and_already_current(self):
        gate = next(s for s in RECOVERY['script'] if s['id'] == 'recovery_install')['then'][0]['if']['condition']['lambda']
        gate = gate.replace('${c6_target_version}', recovery_pin()[2])
        source = r'''
#include <cassert>
#include <string>
#define id(name) name
namespace update { enum State { UPDATE_STATE_UNKNOWN, UPDATE_STATE_NO_UPDATE, UPDATE_STATE_AVAILABLE }; }
struct Updater {
  struct { std::string current_version; } update_info;
  update::State state = update::UPDATE_STATE_UNKNOWN;
} c6_recovery_update;
bool recovery_attempted = false;
bool install_allowed() { GATE }
int main() {
  assert(!install_allowed());
  c6_recovery_update.state = update::UPDATE_STATE_AVAILABLE;
  c6_recovery_update.update_info.current_version = "unknown";
  assert(install_allowed());
  recovery_attempted = true;
  assert(!install_allowed());
  recovery_attempted = false;
  c6_recovery_update.update_info.current_version = "3.1.0";
  assert(!install_allowed());
  c6_recovery_update.update_info.current_version = "1.4.1";
  assert(install_allowed());
}
'''.replace('GATE', gate)
        with tempfile.TemporaryDirectory(prefix='c6-recovery-test-') as directory:
            cpp, binary = Path(directory) / 'gate.cpp', Path(directory) / 'gate'
            cpp.write_text(source)
            result = subprocess.run(['g++', '-std=c++17', str(cpp), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
