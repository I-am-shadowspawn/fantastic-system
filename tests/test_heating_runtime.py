"""Run the shipped request lifecycle lambdas as native C++ with a fake clock.

No Wi-Fi, LVGL or ESPHome build is required. This covers the watchdog-related
failure paths that HA-template tests cannot exercise.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('!lambda', lambda loader, node: loader.construct_scalar(node))
ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.load((ROOT / 'esphome/packages/heating.yaml').read_text(), Loader=Loader)
SCRIPTS = {script['id']: script for script in CONFIG['script']}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class HeatingRuntimeTests(unittest.TestCase):
    def test_native_response_calls_share_one_dispatcher(self):
        actions = [item['homeassistant.action'] for item in walk(CONFIG) if 'homeassistant.action' in item]
        self.assertEqual(len(actions), 1, 'Multiple template instantiations can reuse native response call IDs')
        self.assertTrue(actions[0]['capture_response'])
        for name in ('on_success', 'on_error'):
            callback = actions[0][name]
            self.assertFalse(any('script.execute' in item and item['script.execute'] == 'heating_render'
                                 for item in walk(callback)), 'API callbacks must defer rendering')
            self.assertNotIn('lv_', str(callback))

    @unittest.skipUnless(shutil.which('g++'), 'Requires a native C++ compiler')
    def test_request_lifecycle_with_missing_and_late_replies(self):
        definitions, resets = [], []
        for item in CONFIG['globals']:
            initial = item.get('initial_value', '{}')
            definitions.append(f"{item['type']} {item['id']} = {initial};")
            resets.append(f"{item['id']} = {initial};")
        gate = SCRIPTS['heating_refresh']['then'][0]['if']['condition']['lambda']
        command_gate = SCRIPTS['heating_command']['then'][0]['if']['condition']['lambda']
        dispatcher = SCRIPTS['heating_api_call']['then']
        on_error = dispatcher[1]['homeassistant.action']['on_error'][0]['lambda']
        tick = CONFIG['interval'][1]['then'][0]['lambda']
        on_connect = CONFIG['api']['on_client_connected'][0]['lambda']
        on_disconnect = CONFIG['api']['on_client_disconnected'][0]['lambda']
        code = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
#define id(name) name
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGD(...) ((void)0)
uint32_t now_ms = 1000;
uint32_t millis() { return now_ms; }
struct Switch { bool state = true; } heating_enabled;
DEFINITIONS
void reset() { RESETS heating_enabled.state = true; now_ms = 1000; }
bool ready() { GATE }
bool command_ready() { COMMAND_GATE }
void tick() { TICK }
void connected(std::string client_info, std::string client_address) { CONNECT }
void disconnected(std::string client_info, std::string client_address) { DISCONNECT }
void received_error(int request_id, std::string kind, std::string error) { ERROR }
void send_snapshot() {
  assert(ready());
  heating_fetch_started = millis();
  ++heating_outstanding_requests;
}
int main() {
  // Log viewers must never initiate discovery, even with entity subscriptions.
  connected("ESPHome Logs 2026.11.0", "logs");
  assert(!ready());
  connected("Home Assistant 2026.11.2", "ha");
  connected("Home Assistant 2026.11.2", "ha");
  assert(heating_ha_clients.size() == 1 && ready());
  disconnected("ESPHome Logs 2026.11.0", "logs");
  assert(ready());
  disconnected("Home Assistant 2026.11.2", "ha");
  assert(!ready());

  // A week with no replies must retain at most two native callbacks, rather
  // than adding another callback every 15 seconds or on each reconnect.
  reset();
  connected("Home Assistant", "ha");
  int sent = 0;
  for (now_ms = 1000; now_ms < 7 * 86400000u; now_ms += 1000) {
    if (ready()) { send_snapshot(); ++sent; }
    tick();
    assert(heating_outstanding_requests <= 2);
    if (now_ms % 60000 == 0) {
      disconnected("Home Assistant", "ha");
      connected("Home Assistant", "ha");
    }
  }
  assert(sent == 2 && !ready());
  assert(heating_error.find("replies missing") != std::string::npos);

  // A late callback releases its credit but cannot invalidate a newer fetch.
  reset();
  connected("Home Assistant", "ha");
  heating_fetch_started = 12345;
  heating_outstanding_requests = 2;
  received_error(123, "snapshot", "late");
  assert(heating_fetch_started == 12345 && heating_outstanding_requests == 1);
  assert(heating_error.empty());
  received_error(12345, "snapshot", "script unavailable");
  assert(heating_fetch_started == 0 && heating_outstanding_requests == 0);
  assert(!ready() && heating_render_dirty);
  now_ms += 59999;
  assert(!ready());
  ++now_ms;
  assert(ready());

  // Backoff and freshness checks must survive the 32-bit clock wrapping.
  now_ms = UINT32_MAX - 1000;
  heating_retry_after = now_ms + 60000;
  assert(!ready());
  now_ms += 60000;
  assert(ready());
  heating_retry_after = 0;
  heating_last_snapshot = now_ms - 1000;
  assert(command_ready());
  now_ms += 45000;
  assert(!command_ready());

  // A late failed command must not clear a newer command's identity/status.
  heating_command_generation = 200;
  heating_pending = "climate.room";
  heating_command_started = now_ms;
  heating_outstanding_requests = 1;
  received_error(199, "command", "late");
  assert(heating_pending == "climate.room" && heating_command_started == now_ms);
  assert(heating_outstanding_requests == 0);

  // Neither missing replies nor user input may cause heating work during OTA.
  reset();
  connected("Home Assistant", "ha");
  heating_last_snapshot = 500;
  heating_ota_active = true;
  assert(!ready() && !command_ready());
  heating_fetch_started = 100;
  now_ms = 20000;
  tick();
  assert(heating_fetch_started == 100);
  heating_ota_active = false;
  tick();
  assert(heating_fetch_started == 0);
  heating_enabled.state = false;
  assert(!ready() && !command_ready());
}
'''
        for key, value in {'DEFINITIONS': '\n'.join(definitions), 'RESETS': '\n'.join(resets),
                           'COMMAND_GATE': command_gate, 'GATE': gate, 'TICK': tick,
                           'DISCONNECT': on_disconnect, 'CONNECT': on_connect, 'ERROR': on_error}.items():
            code = code.replace(key, value)
        with tempfile.TemporaryDirectory(prefix='wiser-runtime-') as directory:
            source = Path(directory) / 'runtime.cpp'
            binary = Path(directory) / 'runtime'
            source.write_text(code)
            compiled = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', str(source), '-o', str(binary)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)


if __name__ == '__main__':
    unittest.main()
