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

### Restart, discovery timeout, or unreliable OTA

A `Task wdt` reset means a task failed to service the watchdog; a backtrace
containing only `esp_cpu_wait_for_intr` does not identify the blocking task.
A single `api took a long time ... (73 ms)` warning also does not establish the
cause of a watchdog reset. Capture the messages **before** the reset over USB.

The Wiser package now uses one response-bearing API dispatcher, because the
pinned ESPHome 2026.11 implementation allocates response IDs per C++ action
template type. Separate snapshot/command action types can collide. API
callbacks only store data and mark the page for updating; the UI is rendered
later, while the Heating page is visible. Unchanged snapshots are cached and
unnecessary redraws are skipped.

Discovery starts only for a native client identifying itself as Home Assistant,
not for a log viewer. Failed/time-out discovery backs off for at least 60
seconds. At most two unanswered native requests are retained across reconnects;
ESPHome 2026.11 does not remove their callbacks when a reply never arrives.
After two missing replies, polling pauses instead of continuing to consume
memory. Correct the HA scripts/action permissions, then restart the console if
it still says “Wiser replies missing”. Late replies release their request slots
but cannot replace newer data. Commands are never replayed automatically.

For isolation testing, turn off the console's **Wiser Controls** configuration
switch in HA. This disables Wiser requests and card updates, and survives a
restart. Native OTA uploads also suspend Wiser polling/rendering until an
upload aborts or fails (a successful upload restarts the device). The console
exposes **Free Heap**, **Largest Free Heap Block** and **Main Loop Time**
diagnostics, sampled every 60 seconds. Watch for decreasing heap or long loop
times alongside the USB logs.

The P4 uses a separate ESP32-C6 Wi-Fi processor. ESPHome 2026.11 has a
[reported ESP-Hosted compatibility issue with older factory C6 firmware](https://github.com/esphome/esphome/issues/22896):
Wi-Fi can initially connect, then SDIO/RPC errors interrupt networking and lead
to watchdog resets and unreachable OTA. This is a possible separate cause;
the symptom alone does not confirm it. In the supplied `ha-console-logs(1).txt`,
`SDIO RX read (2560 bytes) exceeds staging target (1536 bytes)` is recorded
repeatedly immediately before API disconnections and subsequent watchdog
restarts. The subsequent USB capture, `HA Console-logs.txt`, additionally
records `major version mismatch — OTA coprocessor from host`, followed by
`loopTask (CPU 1)` watchdog failures. This confirms a host/coprocessor version
mismatch on that device. Normal installs of this repository's P4 firmware do
**not** update the C6. Check for `eh_sdio`, `esp_hosted`, RPC
timeouts or firmware-version mismatches in the boot log. If confirmed, follow
the [ESPHome coprocessor firmware documentation](https://esphome.io/components/update/esp32_hosted/)
and the instructions for this exact Waveshare board to install a compatible
C6 image. Do not automatically flash a generic image or suppress the watchdog
to hide the failure.

To capture a USB log without installing firmware:

1. Connect the laptop to the **P4 USB serial port** with a data-capable cable.
   The current firmware logs through `USB_SERIAL_JTAG` at 115200 baud.
2. In Chrome or Edge, open [ESPHome Web](https://web.esphome.io), select
   **Connect**, choose the board's serial port, and open **Logs**.
3. Press the board's **RESET** button, not BOOT, and capture through the next
   crash. If the USB connection drops, reconnect and capture the next automatic
   restart. Copy/download the complete log, including messages preceding the
   watchdog's task list. A USB serial terminal at 115200 baud is an alternative.

USB provides both data and power if the laptop port supplies sufficient power
for the panel. If changing the power source changes the failure, record that
as part of the test. The network log viewer cannot reliably capture a failure
that disconnects Wi-Fi. Keep Wi-Fi credentials and personal entity data out of
public log reports.

## Recover the C6 using the P4 USB connection

The P4 console application and C6 Wi-Fi coprocessor have separate firmware.
The supplied `c6-recovery.yaml` is a temporary **P4 application** that carries
an ESP-Hosted 3.1.0 **C6 application image**. After a physical screen-button
press, it transfers that image to the C6 over SDIO. It requires no Wi-Fi,
Home Assistant connection, API encryption key or secrets. It does not install
anything automatically on startup.

The reviewed image is 1,472,016 bytes, targets ESP32-C6, and reports application
version `3.1.0`. Its SHA-256 is
`4ac31b47eb3bf7e239e657173dcb317433a2cc7799a4ec518aeda9856d06d614`.
It comes from the [official ESP-Hosted manifest](https://esphome.github.io/esp-hosted-firmware/manifest/esp32c6.json).
The build downloads and verifies that exact image before embedding it. The
Device Builder host needs Internet access for the first download; the panel
does not need Internet access during recovery. This pin matches the 3.1.0
host library in the current ESPHome 2026.11.0 build. Review both versions when
upgrading ESPHome; do not substitute an arbitrary newer C6 image.

### USB recovery sequence

1. Save a copy of your current `ha-console.yaml` and keep its secrets. Recovery
   replaces the P4 application temporarily. It does not replace your saved HA
   configuration or automatically restore the normal console afterwards.
2. Copy `esphome/c6-recovery.yaml` from this repository into the Device Builder
   configuration directory, beside your normal console YAML. It downloads the
   same board hardware package already used by the console. Keep the normal
   device configuration and secrets in place.
3. Validate and compile the recovery device. Connect the laptop using a data
   cable to the **P4 USB serial port**, choose **Install → Plug into this
   computer**, and flash the recovery device. If using a manually downloaded
   image with ESPHome Web, choose the recovery build's **factory** image for
   this USB installation. Do not upload the C6 image directly to the P4.
4. Close any serial monitor that holds the port while flashing. After flashing,
   open USB Logs again and confirm that the panel shows **C6 Wi-Fi Firmware
   Recovery**, the detected C6 version (possibly `unknown`) and target `3.1.0`.
5. With reliable USB power connected, press **Install C6 Firmware** on the
   screen once. The status changes before installation begins. Keep power
   connected and watch the USB log. The updater verifies the image, writes the
   C6's update partition, then restarts both processors to activate it.
6. After restart, confirm **C6: 3.1.0** and **C6 is up to date**. The Install
   button should now be disabled. A version of `unknown` is not confirmation
   of success, even if the write appeared to complete.
7. USB-install your original normal `ha-console.yaml` firmware. This removes
   the recovery UI and its temporary watchdog setting. Confirm that the major
   version mismatch and SDIO staging errors are absent, then exercise Heating
   discovery/controls and a normal OTA update.

The recovery build temporarily sets the task watchdog to 30 seconds so the
old C6 firmware's blocking version query can finish during setup. Watchdog
protection remains enabled. The normal console keeps its existing watchdog
settings; do not copy this workaround into production firmware.

Recovery allows **one installation attempt per boot**. On failure, save the
complete USB log before pressing RESET to permit another deliberate attempt.
Do not repeatedly reset during a write. If SDIO recovery cannot begin or fails
because the existing C6 partition layout is incompatible, stop and investigate
before retrying. Physical compatibility and the available OTA partition on the
particular C6 still require validation on the device.

### Enable future C6 updates in Home Assistant

Enable maintenance only after recovery has restored a stable C6 connection.
In your normal P4 device YAML's remote `packages.console.files` list, uncomment
or add:

```yaml
      - esphome/packages/c6-maintenance.yaml
```

For local package configurations use:

```yaml
packages:
  c6_maintenance: !include packages/c6-maintenance.yaml
```

Merge this entry into your existing `packages:` map. The new package must be
available at the selected GitHub ref for remote-package builds. This package
is P4-only and must not be included in the S3 configuration.

Compile and install the normal console. Home Assistant will expose a **C6
Firmware** update entity. It checks the official ESP32-C6 manifest every six
hours and uses ESPHome's host-version-aware selection (it will not select a
release newer than the host library). Installation starts only when explicitly
requested through the update entity in HA. There is no automatic install on
boot or when an update is advertised. The normal device needs Internet access
to check the manifest and download a selected image.

### Independent C6 flashing fallback

The board also has a dedicated **ESP32-C6 UART terminal**, separate from the
P4 USB interface. A suitable 3.3 V serial adapter and the correct C6 download
mode/wiring can program that processor independently. Follow the exact
[Waveshare board hardware documentation](https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-7B)
and a verified C6 flash layout. The embedded recovery `.bin` is an application
image, **not** a complete bootloader/partition-table image: do not write it at
offset zero or apply P4 flashing offsets to the C6. Direct C6 serial flashing
is a separate fallback, not required for the normal USB/SDIO recovery path.

### Verification before publishing or flashing

From the repository root with ESPHome 2026.11.0 installed:

```bash
python tools/verify_c6_image.py
python -m unittest discover -s tests -v
python tools/local_config.py --configuration recovery
esphome config esphome/.ci-recovery.yaml
esphome compile esphome/.ci-recovery.yaml
python tools/local_config.py --configuration p4-c6
esphome config esphome/.ci-p4-c6.yaml
esphome compile esphome/.ci-p4-c6.yaml
```

The verifier checks the pinned SHA-256, ESP32-C6 chip ID and embedded app version
without connecting to a device. `--image /path/to/image.bin` verifies an already
downloaded image instead of downloading it again. CI compiles `p4`, `s3`,
`p4-c6` and `recovery`, and runs the image verifier on the recovery job.

Compilation and software tests do not prove a successful C6 update. Physical
acceptance requires matching host/C6 versions, no mismatch/staging errors, at
least 30 minutes without watchdog resets, working Heating discovery, and a
successful normal OTA upload. Firmware is not installed by these checks.
