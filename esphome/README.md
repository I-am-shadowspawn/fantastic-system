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
