# fantastic-system
ESP32 HA Console

Base [ESPHome](https://esphome.io) template that turns a **Waveshare
ESP32-P4-WIFI6-Touch-LCD-7B** into an interactive dashboard / console for
[Home Assistant](https://www.home-assistant.io). The device talks to Home
Assistant through a **single integration** – the built-in ESPHome (native API)
integration. No MQTT broker, custom component or add-on is required.

## Features

| Page | What it does |
|------|--------------|
| **Home** | 4 toggle tiles bound to HA lights/switches. Tile state follows HA; tapping calls `homeassistant.toggle`. |
| **Sensors** | Live indoor temperature, humidity and outdoor temperature imported from HA. |
| **Console** | 6 buttons that fire a **Console Button** event entity in HA – use them to trigger any automation/scene/script. |

Always visible: status bar (clock from HA, message from an `input_text`,
HA connection indicator) and a navigation bar.

Entities exposed to Home Assistant:

* `event.<name>_console_button` – event types `scene_1` … `scene_6`
* `switch.<name>_backlight` – turn the screen on/off from automations
* `number.<name>_screen_timeout` – seconds of inactivity before the screen blanks (0 = never)
* Diagnostics: WiFi signal, uptime, IP address, restart button

## Supported hardware

| Board | Hardware package |
|-------|------------------|
| [Waveshare ESP32-P4-WIFI6-Touch-LCD-7B](https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-7B) (1024×600 MIPI-DSI, GT911, ESP32-C6 Wi-Fi) | `esphome/packages/hardware/waveshare-esp32-p4-wifi6-touch-lcd-7b.yaml` |

The original ESP32-S3-Touch-LCD-4.3 hardware package remains available; select
it in `ha-console.yaml` to use that board instead. Hardware packages provide
the ids `main_display`, `main_touch` and `backlight` used by the UI.

## Repository layout

```
esphome/
├── README.md                    # dashboard setup and troubleshooting
├── ha-console.yaml              # entry point – edit substitutions here
├── secrets.yaml.example         # copy to secrets.yaml
└── packages/
    ├── base.yaml                # WiFi, API, OTA, logger, time, diagnostics
    ├── homeassistant.yaml       # HA entity imports + entities exposed to HA
    ├── ui.yaml                  # LVGL pages, status/nav bar, screen timeout
    └── hardware/
        ├── waveshare-esp32-p4-wifi6-touch-lcd-7b.yaml
        └── waveshare-esp32-s3-touch-lcd-4.3.yaml
```

## Getting started — ESPHome dashboard (default)

Use **ESPHome Device Builder** (the ESPHome dashboard) to configure, compile
and flash the ESP32-P4. A terminal is not required for normal installation.
Install or update Device Builder to **ESPHome 2026.11.0 or newer** using the
[ESPHome installation guide](https://esphome.io/install/).

1. Before replacing stock firmware, see the optional
   [stock backup instructions](#stock-firmware-with-wi-fi-credentials).
2. Download this repository and copy **the contents of its `esphome/` folder**
   into Device Builder's configuration folder, preserving `packages/` and
   `packages/hardware/`. On Home Assistant OS this is normally
   `/config/esphome/`, accessible through a file editor or network share.
   Copy `ha-console.yaml` and `packages/`; do not copy a personal `secrets.yaml`
   or experimental device YAML files from another checkout.
3. In Device Builder, open **Secrets**. Merge the four keys from
   `esphome/secrets.yaml.example` into the existing secrets file and fill them
   in. Do not replace secrets used by other devices. For the API encryption
   key, create a temporary device in the dashboard and copy its generated
   `api.encryption.key` before deleting that temporary configuration. Use a
   separate random password of at least eight characters for the fallback AP.
4. Open **Edit** on the `ha-console` card. Set the device name, timezone and
   Home Assistant entity IDs/labels in `substitutions:`. The default hardware
   package selects the Waveshare ESP32-P4-WIFI6-Touch-LCD-7B. Save, then choose
   **Validate** from the card menu and resolve any errors before installing.
5. Connect the **P4 USB serial port** using a data cable. Select **Install**:
   - If USB is attached to the computer running your browser, choose
     **Plug into this computer**. Use Chrome or Edge with Web Serial support
     and a secure dashboard connection (HTTPS or localhost).
   - If USB is attached to the Device Builder host, choose
     **Plug into the computer running ESPHome Device Builder** and select
     the P4 serial port (the wording can vary with dashboard version).
   - If browser flashing is unavailable, choose **Manual download**, select
     the factory format for first installation, then use
     [ESPHome Web](https://web.esphome.io/) in Chrome or Edge to install that
     downloaded image through the P4 USB port.
6. After flashing, let the board restart and join your 2.4 GHz Wi-Fi network.
   For subsequent updates, select **Install → Wirelessly** on its dashboard
   card. Initial installation requires USB; wireless updates require working
   ESPHome firmware and network connectivity.
7. In Home Assistant, add the discovered device under
   **Settings → Devices & services → ESPHome**, supplying the API encryption
   key when requested. Open its integration options (**Configure**) and enable
   **Allow the device to perform Home Assistant actions** for tile controls.

See [the configuration guide](esphome/README.md) for the destination folder
layout and troubleshooting. Local package includes work in Device Builder;
`ha-console.yaml` alone is not a complete configuration.

ESPHome and the C6 must have compatible ESP-Hosted firmware; compatibility
with the original C6 firmware is not guaranteed. Flashing the P4 does not
update the C6. See the [ESPHome hosted firmware project](https://github.com/esphome/esp-hosted-firmware)
and Waveshare's instructions before changing the C6 firmware; keep a
compatible C6 image for stock recovery.

The GT911 is polled and probes `0x5D` and then `0x14`. Display and touch
orientation may need adjustment for your mounting.

### Optional command line installation

Advanced users can still install ESPHome locally, copy
`esphome/secrets.yaml.example` to `esphome/secrets.yaml`, fill in the secrets,
and run `esphome run ha-console.yaml` from the repository's `esphome/` folder.
Use the same minimum ESPHome version and P4 USB port as the dashboard method.
The stock backup/recovery commands below are a separate optional workflow.

### Stock firmware with Wi-Fi credentials

This option restores a **complete backup of this board**, including the Wi-Fi
settings saved by its stock firmware. It is not an ESPHome configuration and
does not inject `secrets.yaml` credentials into a vendor binary.

Before flashing ESPHome, configure Wi-Fi in the stock Settings UI and confirm
that it reconnects after restarting. Install `esptool` (`pip install esptool`),
connect the P4 USB serial port, and replace `/dev/ttyUSB0` below with that port:

```bash
umask 077
mkdir -p "$HOME/ha-console-stock" && \
  cd "$HOME/ha-console-stock" && \
  test ! -e stock-p4.bin && \
  python -m esptool --chip esp32p4 --port /dev/ttyUSB0 read-flash 0 0x2000000 stock-p4.bin && \
  test "$(wc -c < stock-p4.bin)" -eq 33554432 && \
  sha256sum stock-p4.bin > stock-p4.sha256
```

Confirm the backup is 33,554,432 bytes and keep both files private and outside
the repository: the image can contain Wi-Fi passwords and other device data.
If the backup fails, remove the incomplete image before retrying; the command
will not overwrite an existing one.
Do not use this method with flash encryption or secure boot enabled; a raw
backup may not be restorable. The backup covers the P4 flash only, not the C6.

To reflash the preconfigured stock image on the **same board**, with a compatible
C6 firmware still installed:

```bash
cd "$HOME/ha-console-stock" && \
  sha256sum -c stock-p4.sha256 && \
  test "$(wc -c < stock-p4.bin)" -eq 33554432 && \
  python -m esptool --chip esp32p4 --port /dev/ttyUSB0 write-flash 0 stock-p4.bin
```

This overwrites the ESPHome firmware, settings and all P4 flash data. If no
backup was made, use Waveshare's complete recovery package and instructions
for your board and silicon revision. Its published factory-only application
binary is not a complete flash image; do not write it at offset zero. Configure
Wi-Fi in stock firmware after recovery. Restore a compatible C6 image separately
if it was changed.

### Using the console buttons

Create an automation triggered by the **Console Button** event entity and
check which button was pressed (triggering on the entity state – the event
timestamp – fires on every press, including repeated presses of the same button):

```yaml
automation:
  - alias: "Console: scene 1"
    triggers:
      - trigger: state
        entity_id: event.ha_console_console_button
        not_from: unavailable
    conditions:
      - condition: state
        entity_id: event.ha_console_console_button
        attribute: event_type
        state: scene_1
    actions:
      - action: scene.turn_on
        target:
          entity_id: scene.movie_night
```

### Status bar message

Create an `input_text.ha_console_message` helper (or point `message_entity`
at any entity) – its state is shown in the middle of the status bar.

## CI

`.github/workflows/esphome.yml` validates and compiles the configuration on
every push and pull request.
