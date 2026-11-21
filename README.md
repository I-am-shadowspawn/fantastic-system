# fantastic-system
ESP32 HA Console

Base [ESPHome](https://esphome.io) template that turns a **Waveshare ESP32-S3
touchscreen** into an interactive dashboard / console for
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
| [Waveshare ESP32-S3-Touch-LCD-4.3](https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-4.3) (800×480, GT911) | `esphome/packages/hardware/waveshare-esp32-s3-touch-lcd-4.3.yaml` |

Other Waveshare RGB panels (e.g. the 7" 800×480 / 5" 1024×600 variants) can be
added by copying the hardware package and changing the `mipi_rgb` `model:` and
pins. The UI only depends on the ids `main_display`, `main_touch` and
`backlight`.

## Repository layout

```
esphome/
├── ha-console.yaml              # entry point – edit substitutions here
├── secrets.yaml.example         # copy to secrets.yaml
└── packages/
    ├── base.yaml                # WiFi, API, OTA, logger, time, diagnostics
    ├── homeassistant.yaml       # HA entity imports + entities exposed to HA
    ├── ui.yaml                  # LVGL pages, status/nav bar, screen timeout
    └── hardware/
        └── waveshare-esp32-s3-touch-lcd-4.3.yaml
```

## Getting started

1. Install ESPHome (`pip install esphome`) or use the ESPHome Device Builder add-on.
2. Create your secrets:
   ```bash
   cd esphome
   cp secrets.yaml.example secrets.yaml
   openssl rand -base64 32   # paste into api_encryption_key
   ```
3. Edit the `substitutions:` in `esphome/ha-console.yaml` – device name,
   timezone and the Home Assistant entity IDs/labels you want on the screen.
4. Connect the board over USB and flash it:
   ```bash
   esphome run ha-console.yaml
   ```
   Later updates can be done over the air.
5. In Home Assistant the device is auto-discovered under
   **Settings → Devices & services → ESPHome**. Add it with the API encryption key.
6. Open the device's integration options (**Configure**) and enable
   **Allow the device to perform Home Assistant actions** – required for the
   Home tiles to toggle entities.

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
