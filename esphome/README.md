# ESPHome dashboard configuration

The default installation uses **ESPHome Device Builder**, also called the
ESPHome dashboard. Use ESPHome **2026.11.0 or newer** for the P4 configuration.
See the [main README](../README.md#getting-started--esphome-dashboard-default)
for the complete installation sequence.

## Copy the configuration

Using a file editor or network share, copy `ha-console.yaml` and the complete
`packages/` folder into your dashboard configuration directory. In Home
Assistant OS this is normally `/config/esphome/`. For a standalone dashboard,
use the directory configured for that dashboard.

The destination must look like this:

```text
/config/esphome/
├── ha-console.yaml
├── secrets.yaml
└── packages/
    ├── base.yaml
    ├── homeassistant.yaml
    ├── ui.yaml
    ├── heating.yaml
    └── hardware/
        ├── waveshare-esp32-p4-wifi6-touch-lcd-7b.yaml
        └── waveshare-esp32-s3-touch-lcd-4.3.yaml
```

Do not create `/config/esphome/esphome/ha-console.yaml`: the device YAML belongs
at the dashboard configuration root. Keep package files below `packages/`,
rather than placing them at the root as separate dashboard devices.

## Secrets and customization

Open the dashboard's **Secrets** editor and merge the four keys from
`secrets.yaml.example`: `wifi_ssid`, `wifi_password`, `fallback_ap_password`
and `api_encryption_key`. Preserve existing secrets. Use your 2.4 GHz Wi-Fi
credentials and a random fallback password of at least eight characters.

For a key without terminal commands, create a temporary device in Device
Builder, copy its generated `api.encryption.key` value, then delete the
temporary device configuration. Paste that value into `api_encryption_key`.
Never commit the populated `secrets.yaml` file.

Open **Edit** on the `ha-console` card and adjust `substitutions:`. Use a unique
device name. Set each entity ID to an entity from your Home Assistant instance;
temperature and humidity entries must refer to sensors with numeric states.
The supplied entity IDs reflect an example/local setup and must be reviewed.
In particular, a camera entity cannot provide a numeric temperature reading.

Edit `substitutions.home_tiles` to add, remove, or reorder Home buttons. Each
list entry needs an `entity` (a toggleable Home Assistant entity ID) and a
`label` (the button text). The Home screen shows fifteen entries per page in a
5-column, 3-row grid. Swipe up to see the next page or down to go back. With
fifteen or fewer entries, the Home screen stays on one page. Existing configurations can keep
the four `tile_N_entity` and `tile_N_label` pairs until they adopt `home_tiles`.

`hardware_package` defaults to the ESP32-P4 7B board. To use the supported S3
board instead, change it to
`packages/hardware/waveshare-esp32-s3-touch-lcd-4.3.yaml`.
Save and select **Validate** before installing.

## Flash and update

For first installation, connect the P4 USB serial port with a data cable and
choose **Install** on the card. Choose the browser computer or Device Builder
host according to where USB is connected. Browser flashing needs Web Serial
support (Chrome/Edge) and HTTPS or localhost. If necessary, use **Manual
download** with factory format and install the result using
[ESPHome Web](https://web.esphome.io/).

Once the board runs ESPHome and joins Wi-Fi, use **Install → Wirelessly** for
later updates. P4 flashing does not update the ESP32-C6 Wi-Fi coprocessor;
check the compatibility guidance in the main README if Wi-Fi fails.

## Troubleshooting

- **Include file not found:** restore the exact folder layout above. Paths are
  relative to `ha-console.yaml`, not to your repository checkout.
- **Secret not defined:** merge all four example keys in the dashboard Secrets
  editor. A repository-side secrets file is not automatically available to a
  dashboard running on another machine.
- **Serial port missing:** check the P4 port, data cable and USB permissions;
  close other serial monitors. Use the board's documented bootloader procedure
  if it does not enter download mode automatically.
- **Offline after USB installation:** check logs, 2.4 GHz Wi-Fi credentials and
  ESP-Hosted/C6 compatibility before attempting a wireless installation.
- **Tiles do not control HA:** enable **Allow the device to perform Home
  Assistant actions** in the device's Home Assistant integration options.

## Optional terminal workflow

From this folder, with ESPHome installed and secrets configured,
`esphome run ha-console.yaml` remains available for advanced users.

## Wiser heating and hot water

Use the `asantaga/wiserHomeAssistantPlatform` integration (domain `wiser`).
Discovery runs in HA, where the entity/device registry is available. One card
represents one heating room, even if it contains several radiator valves.
Hot water appears once per Wiser hot water device. Rooms are sorted by name,
followed by hot water. Entities renamed in HA are supported.

### Install the Home Assistant package

1. Copy `homeassistant/packages/ha_console_wiser.yaml` from this repository to
   `/config/packages/ha_console_wiser.yaml` on **Home Assistant**. This file
   belongs to HA, not Device Builder or the console's `packages/` directory.
2. If HA packages are not enabled, merge this into `configuration.yaml` under
   the existing `homeassistant:` key (do not create a duplicate key):

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. Check HA's configuration and restart HA to load the package. It creates
   `script.ha_console_wiser_snapshot` and `script.ha_console_wiser_command`.
   Later script-only changes can be applied with Reload Scripts.
4. Keep **Allow the device to perform Home Assistant actions** enabled on the
   console's ESPHome integration. Use HA Core 2026.11 or newer (including climate temperature-unit attributes)
   and ESPHome 2026.11.0 or newer for this configuration.
5. Validate, compile and install the console firmware. Its remote package list
   now includes `esphome/packages/heating.yaml`; that file must be present on
   the selected GitHub ref before remote-package builds can succeed.

The page refreshes every 15 seconds, on entry, and after commands. Added and
removed devices appear automatically. Readings older than 45 seconds disable
controls. Loading, empty discovery, unavailable entities and script/action
failures have separate messages. Commands are not replayed after reconnection.
If a command times out, check HA/device state before retrying: HA may already
have applied it.

### Controls and layout

```yaml
substitutions:
  heating_rows: '2'
  heating_columns: '3'
```

Both values must be positive integers. Each horizontal screen holds their
product in row-major order. One screen disables further useful scrolling;
extra cards create additional horizontally snapped screens. Row/column changes
require a firmware rebuild. Higher densities can reduce text and touch usability;
the default is intended for the supported landscape displays.

Tap a room's target to open minus/plus controls. Apply sends one target change;
Cancel leaves the target alone. Limits and step come from HA (0.5° step if HA
omits it). Wiser's configured setpoint mode still determines how long a target
change lasts. Passive rooms exposing only a temperature range are read-only.
Boost uses the Wiser integration's configured heating duration and temperature
increase. Cancel uses its cancel-overrides preset and is enabled during boost.

Hot water uses its per-device Boost Hot Water and Cancel Hot Water Overrides
buttons, retaining Wiser's hot water boost duration. Current/target temperatures
are shown only when the optional tank climate setup supplies them, including
low/high targets where applicable. Hot water temperatures are read-only.
When boost status is unknown, cancellation is available if HA exposes its
cancel button; Wiser's cancellation also clears other hot water overrides.

### Customized hot water entities

Discovery associates hot water entities by the HA device model `Hot Water`.
Within that device it identifies the boost/cancel buttons using their Wiser
icons (`mdi:water-plus`, `mdi:water-off`). It prefers a climate entity for status,
then a sensor with Wiser boost attributes, then the hot water relay switch.
Disabled or ambiguous entities can produce “Check HA mapping”. Enable the
required entities in HA, or edit `hot_water_overrides` in the snapshot script:

```yaml
hot_water_overrides:
  YOUR_HA_HOT_WATER_DEVICE_ID:
    boost_entity: button.your_boost_hot_water
    cancel_entity: button.your_cancel_hot_water_overrides
    status_entity: sensor.your_hot_water
```

The device ID is the final component of its HA device settings URL. Overrides
must refer to entities belonging to that same Wiser device. Use one mapping
per hot water device when several hubs are installed. Reload Scripts after
editing. If the scripts are renamed, set `heating_snapshot_action` and
`heating_command_action` substitutions to their new action names.

### Local checks

To test this checkout without waiting for changes to reach GitHub:

```bash
python tools/local_config.py --hardware p4
esphome config esphome/.ci-p4.yaml
esphome compile esphome/.ci-p4.yaml
python -m unittest discover -s tests -v
```

Use `--hardware s3` and `.ci-s3.yaml` for the smaller board. Generated entry
points are ignored by Git and use the existing local secrets. Tests exercise
the actual HA discovery and command templates against simulated states and
registry data; they do not replace HA configuration checking or physical touch
testing. On hardware, check six-card readability, seventh-card swiping without
accidental activation, target editing, boost/cancellation, and HA reconnection.
