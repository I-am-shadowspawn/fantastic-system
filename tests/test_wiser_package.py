"""Exercise the shipped HA templates against representative registry/state data.

This is a small script-sequence interpreter, not a replacement for HA validation.
It executes the real package templates and records the resulting HA service calls.
"""
from pathlib import Path
import math
import unittest

from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = yaml.safe_load((ROOT / 'homeassistant/packages/ha_console_wiser.yaml').read_text())


class ScriptStop(Exception):
    def __init__(self, message, error=False, response=None):
        super().__init__(message)
        self.error, self.response = error, response


class HomeAssistantFixture:
    def __init__(self):
        self.entities, self.devices, self.calls = {}, {}, []
        self.env = NativeEnvironment(undefined=StrictUndefined)
        self.env.filters['bitwise_and'] = lambda value, mask: int(value) & mask
        self.env.globals.update(
            integration_entities=lambda domain: [e for e, s in self.entities.items() if s['integration'] == domain],
            device_id=lambda entity: self.entities.get(entity, {}).get('device'),
            device_attr=lambda device, attr: self.devices.get(device, {}).get(attr),
            device_entities=lambda device: [e for e, s in self.entities.items() if s.get('device') == device],
            states=lambda entity: self.entities.get(entity, {}).get('state', 'unknown'),
            state_attr=lambda entity, attr: self.entities.get(entity, {}).get('attributes', {}).get(attr),
            area_id=lambda e: self.devices.get(self.entities.get(e, {}).get('device'), {}).get('area'),
            area_name=lambda e: self.devices.get(self.entities.get(e, {}).get('device'), {}).get('area'),
            config_entry_id=lambda e: self.devices.get(self.entities.get(e, {}).get('device'), {}).get('hub', 'hub1') if e in self.entities else None,
            room_battery_entities={},
            is_number=lambda value: self.is_number(value),
            expand=lambda entity: [self.entities[entity]] if entity in self.entities and self.entities[entity].get('present', True) else [],
        )

    @staticmethod
    def is_number(value):
        try:
            return math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    def add(self, entity, device, state='auto', integration='wiser', **attributes):
        self.entities[entity] = dict(device=device, state=state, integration=integration, attributes=attributes)

    def room(self, entity='climate.renamed_lounge', device='room1', **attributes):
        self.devices[device] = dict(model='Room', name=device)
        attrs = dict(friendly_name='Lounge', heating_type='Radiator', current_temperature=19.5,
                     temperature=20.0, min_temp=5, max_temp=30, target_temp_step=0.5,
                     supported_features=17, preset_modes=['boost_1h', 'cancel_overrides'],
                     is_boosted=False, is_heating=True, boost_time_remaining=0)
        attrs.update(attributes)
        self.add(entity, device, **attrs)

    def hot_water(self, device='water1', climate=False):
        self.devices[device] = dict(model='Hot Water', name='Hot water ' + device)
        self.add(f'button.{device}_start', device, state='unknown', icon='mdi:water-plus')
        self.add(f'button.{device}_stop', device, state='unknown', icon='mdi:water-off')
        self.add(f'switch.{device}_relay', device, state='on', icon='mdi:water-boiler')
        self.add(f'sensor.{device}_state', device, state='on', icon='mdi:fire',
                 is_boosted=True, boost_time_remaining=42)
        if climate:
            self.add(f'climate.{device}', device, current_temperature=48, target_temp_low=45,
                     target_temp_high=55, is_heating=True, is_boosted=True, boost_time_remaining=42)

    def render(self, value, context):
        if isinstance(value, str):
            return self.env.from_string(value).render(**context)
        if isinstance(value, dict):
            return {key: self.render(item, context) for key, item in value.items()}
        if isinstance(value, list):
            return [self.render(item, context) for item in value]
        return value

    def run_sequence(self, sequence, context):
        for step in sequence:
            if 'variables' in step:
                for key, value in step['variables'].items():
                    context[key] = self.render(value, context)
            elif 'if' in step:
                if self.render(step['if'], context):
                    self.run_sequence(step['then'], context)
            elif 'choose' in step:
                for branch in step['choose']:
                    if self.render(branch['conditions'], context):
                        self.run_sequence(branch['sequence'], context)
                        break
                else:
                    self.run_sequence(step.get('default', []), context)
            elif 'action' in step:
                if step['action'] == 'script.ha_console_wiser_snapshot':
                    context[step['response_variable']] = self.snapshot()
                else:
                    self.calls.append(self.render(step, context))
            elif 'stop' in step:
                raise ScriptStop(step['stop'], step.get('error', False), context.get(step.get('response_variable')))
            else:
                raise AssertionError(f'Unsupported script step {step}')

    def script(self, name, **context):
        try:
            self.run_sequence(PACKAGE['script'][name]['sequence'], context)
        except ScriptStop as result:
            if result.error:
                raise
            return result.response
        raise AssertionError('Script did not return a response')

    def snapshot(self):
        return self.script('ha_console_wiser_snapshot')

    def command(self, card_id, operation, **kwargs):
        return self.script('ha_console_wiser_command', card_id=card_id, operation=operation, **kwargs)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.ha = HomeAssistantFixture()

    def battery(self, entity, value, area='Lounge', hub='hub1', model='iTRV'):
        device = entity + '_device'
        self.ha.devices[device] = dict(model=model, area=area, hub=hub)
        self.ha.add(entity, device, state=str(value), device_class='battery', unit_of_measurement='%')

    def test_plain_room_name_preferred_to_entity_label(self):
        self.ha.room(name='Lounge', friendly_name='Wiser Heater Control Lounge')
        self.assertEqual(self.ha.snapshot()['cards'][0]['name'], 'Lounge')
        self.ha.entities['climate.renamed_lounge']['attributes'].pop('name')
        self.ha.devices['room1']['area'] = 'Living room'
        self.assertEqual(self.ha.snapshot()['cards'][0]['name'], 'Living room')

    def test_lowest_battery_only_from_heating_devices_in_room_and_hub(self):
        self.ha.room(name='Lounge')
        self.ha.devices['room1'].update(area='Lounge', hub='hub1')
        self.battery('sensor.valve1', 80)
        self.battery('sensor.valve2', 45)
        self.battery('sensor.stat', 60, model='RoomStat')
        self.battery('sensor.other_room', 10, area='Kitchen')
        self.battery('sensor.other_hub', 5, hub='hub2')
        self.battery('sensor.smoke_alarm', 1, model='SmokeAlarm')
        self.assertEqual(self.ha.snapshot()['cards'][0]['battery_percent'], 45)

    def test_malformed_battery_override_does_not_collect_other_rooms(self):
        self.ha.room(name='Lounge')
        self.battery('sensor.other_room', 10, area='Kitchen')
        template = PACKAGE['script']['ha_console_wiser_snapshot']['sequence'][0]['variables']['snapshot']
        for invalid in ['sensor.other_room', None, {'sensor.other_room': 'bad'}]:
            with self.subTest(invalid=invalid):
                snapshot = self.ha.render(template, dict(hot_water_overrides={}, room_battery_entities={'climate.renamed_lounge': invalid}))
                self.assertIsNone(snapshot['cards'][0]['battery_percent'])

    def test_missing_invalid_and_unavailable_battery(self):
        self.ha.room(name='Lounge')
        self.ha.devices['room1']['area'] = 'Lounge'
        for i, value in enumerate(['unavailable', 'unknown', 'nan', -1, 101]):
            self.battery(f'sensor.invalid{i}', value)
        self.assertIsNone(self.ha.snapshot()['cards'][0]['battery_percent'])
        self.battery('sensor.zero', 0)
        self.assertEqual(self.ha.snapshot()['cards'][0]['battery_percent'], 0)

    def test_ambiguous_area_needs_explicit_battery_map(self):
        self.ha.room('climate.one', 'room1', name='Room one')
        self.ha.room('climate.two', 'room2', name='Room two')
        for dev in ('room1', 'room2'):
            self.ha.devices[dev]['area'] = 'Lounge'
        self.battery('sensor.valve1', 75)
        self.battery('sensor.other_hub', 1, hub='hub2')
        self.assertTrue(all(c['battery_percent'] is None for c in self.ha.snapshot()['cards']))
        template = PACKAGE['script']['ha_console_wiser_snapshot']['sequence'][0]['variables']['snapshot']
        snapshot = self.ha.render(template, dict(hot_water_overrides={}, room_battery_entities={
            'climate.one': ['sensor.valve1', 'sensor.other_hub'], 'climate.two': [],
        }))
        self.assertEqual(snapshot['cards'][0]['battery_percent'], 75)
        self.assertIsNone(snapshot['cards'][1]['battery_percent'])

    def test_room_counts_and_stable_order(self):
        for count in (0, 1, 6, 7, 13):
            with self.subTest(count=count):
                self.ha = HomeAssistantFixture()
                for n in reversed(range(count)):
                    self.ha.room(f'climate.room_{n}', f'dev{n}', friendly_name=f'Room {n:02}')
                result = self.ha.snapshot()
                self.assertEqual(result['version'], 1)
                self.assertEqual(len(result['cards']), count)
                self.assertEqual([c['name'] for c in result['cards']], [f'Room {n:02}' for n in range(count)])

    def test_renamed_room_and_non_wiser_entities(self):
        self.ha.room()
        self.ha.add('climate.wiser_fake', 'other', integration='generic', heating_type='Radiator')
        self.ha.add('climate.floor_probe', 'probe', current_temperature=20)
        self.assertEqual([c['id'] for c in self.ha.snapshot()['cards']], ['climate.renamed_lounge'])

    def test_missing_temperatures_and_passive_range_are_not_editable(self):
        self.ha.room(current_temperature=None, temperature=None)
        card = self.ha.snapshot()['cards'][0]
        self.assertIsNone(card['current'])
        self.assertFalse(card['can_set'])
        self.ha.room(supported_features=2)
        self.assertFalse(self.ha.snapshot()['cards'][0]['can_set'])

    def test_fahrenheit_values_limits_and_units_are_preserved(self):
        self.ha.room(current_temperature=67.1, temperature=68, min_temp=41, max_temp=86,
                     target_temp_step=1, temperature_unit='°F')
        card = self.ha.snapshot()['cards'][0]
        self.assertEqual((card['current'], card['target'], card['unit']), (67.1, 68, '°F'))
        self.assertEqual((card['minimum'], card['maximum'], card['step']), (41, 86, 1))
        self.ha.command(card['id'], 'set_temperature', temperature=69)
        self.assertEqual(self.ha.calls[-1]['data']['temperature'], 69)

    def test_unavailable_room(self):
        self.ha.room()
        self.ha.entities['climate.renamed_lounge']['state'] = 'unavailable'
        card = self.ha.snapshot()['cards'][0]
        self.assertFalse(card['available'])
        self.assertFalse(card['can_set'])
        self.assertFalse(card['can_boost'])

    def test_hot_water_sensor_preferred_to_switch_and_climate_deduplicated(self):
        self.ha.hot_water('hub1')
        self.ha.hot_water('hub2', climate=True)
        cards = self.ha.snapshot()['cards']
        self.assertEqual(len(cards), 2)
        self.assertTrue(all(c['kind'] == 'hot_water' and c['boosted'] for c in cards))
        self.assertTrue(all(c['can_boost'] and c['can_cancel'] and not c['can_set'] for c in cards))
        self.assertIsNone(cards[0]['current'])
        self.assertEqual(cards[1]['current'], 48)
        self.assertEqual(cards[1]['high'], 55)

    def test_ambiguous_buttons_disable_control(self):
        self.ha.hot_water()
        self.ha.add('button.duplicate', 'water1', state='unknown', icon='mdi:water-plus')
        card = self.ha.snapshot()['cards'][0]
        self.assertFalse(card['can_boost'])
        self.assertIn('overrides', card['diagnostic'])

    def test_overrides_cannot_route_to_another_device(self):
        self.ha.hot_water('hub1')
        self.ha.hot_water('hub2')
        template = PACKAGE['script']['ha_console_wiser_snapshot']['sequence'][0]['variables']['snapshot']
        snapshot = self.ha.render(template, dict(hot_water_overrides={
            'hub1': {'boost_entity': 'button.hub2_start', 'cancel_entity': 'button.hub2_stop'},
        }))
        card = next(c for c in snapshot['cards'] if c['id'] == 'hub1')
        self.assertFalse(card['can_boost'])
        self.assertFalse(card['can_cancel'])

    def test_override_recovers_customized_button_icon(self):
        self.ha.hot_water()
        self.ha.entities['button.water1_start']['attributes']['icon'] = 'mdi:custom'
        template = PACKAGE['script']['ha_console_wiser_snapshot']['sequence'][0]['variables']['snapshot']
        snapshot = self.ha.render(template, dict(hot_water_overrides={
            'water1': {'boost_entity': 'button.water1_start'},
        }))
        self.assertTrue(snapshot['cards'][0]['can_boost'])

    def test_disabled_override_button_is_not_usable(self):
        self.ha.hot_water()
        self.ha.entities['button.water1_start']['present'] = False
        self.assertFalse(self.ha.snapshot()['cards'][0]['can_boost'])

    def test_removed_device_disappears(self):
        self.ha.room()
        self.ha.entities.clear()
        self.assertEqual(self.ha.snapshot()['cards'], [])


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.ha = HomeAssistantFixture()
        self.ha.room()

    def test_target_temperature_and_limits(self):
        for temperature in (5, 20.5, 30):
            self.ha.command('climate.renamed_lounge', 'set_temperature', temperature=temperature)
            self.assertEqual(self.ha.calls[-1]['data']['temperature'], temperature)
        for temperature in (4.5, 30.5, 20.25, 'bad', float('nan')):
            with self.subTest(temperature=temperature), self.assertRaises(ScriptStop):
                self.ha.command('climate.renamed_lounge', 'set_temperature', temperature=temperature)

    def test_boost_uses_wiser_defaults(self):
        self.assertTrue(self.ha.command('climate.renamed_lounge', 'boost')['ok'])
        self.assertEqual(self.ha.calls[-1], dict(action='wiser.boost_heating', target=dict(entity_id='climate.renamed_lounge')))

    def test_cancel_only_when_boosted(self):
        with self.assertRaises(ScriptStop):
            self.ha.command('climate.renamed_lounge', 'cancel_boost')
        self.ha.room(is_boosted=True)
        self.ha.command('climate.renamed_lounge', 'cancel_boost')
        self.assertEqual(self.ha.calls[-1]['data']['preset_mode'], 'cancel_overrides')

    def test_hot_water_command_targets_same_device(self):
        self.ha.hot_water('hub1')
        self.ha.hot_water('hub2')
        self.ha.command('hub2', 'boost')
        self.assertEqual(self.ha.calls[-1]['target']['entity_id'], 'button.hub2_start')
        self.ha.command('hub1', 'cancel_boost')
        self.assertEqual(self.ha.calls[-1]['target']['entity_id'], 'button.hub1_stop')
        with self.assertRaises(ScriptStop):
            self.ha.command('hub1', 'set_temperature', temperature=50)

    def test_unknown_removed_or_unavailable_targets_rejected(self):
        for card, operation in [('climate.other', 'boost'), ('climate.renamed_lounge', 'delete')]:
            with self.assertRaises(ScriptStop):
                self.ha.command(card, operation)
        self.ha.entities['climate.renamed_lounge']['state'] = 'unavailable'
        with self.assertRaises(ScriptStop):
            self.ha.command('climate.renamed_lounge', 'boost')
        self.assertEqual(self.ha.calls, [])


if __name__ == '__main__':
    unittest.main()
