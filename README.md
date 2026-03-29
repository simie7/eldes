# Eldes Alarm with Bypass

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom Home Assistant integration for Eldes security systems. Adds **zone bypass**, **zone discovery**, **event entities**, and **system fault monitoring** on top of the original arm/disarm, outputs, and temperature functionality.

> **Fork notice** -- This project is a fork of [augustas2/eldes](https://github.com/augustas2/eldes). The original author is no longer maintaining the integration. Full credit to [@augustas2](https://github.com/augustas2) for the original work.

## Features

| Feature | Description |
|---|---|
| Arm / Disarm / Arm Stay | Control alarm partitions from Home Assistant |
| **Zone Bypass** | Arm with open doors/windows by bypassing specific zones |
| **Zone Discovery** | Binary sensors for each configured zone (names, IDs, device class auto-detection) |
| **Arm Failure Detection** | Fires HA event when arming fails, enabling bypass notification automations |
| **Event Entity** | Native HA event entity that fires on alarm events |
| **System Faults** | Sensor showing active system faults |
| **Multi-Device Fix** | Shared API client prevents token conflicts when using multiple alarms on one account |
| Output Switches | Control relay outputs |
| Temperature Sensors | Read temperature probes |
| Events Sensor | Categorized event history (alarms, user actions, troubles) |
| Battery / GSM / Connection | Device health monitoring |

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **three dots** menu (top right) and select **Custom repositories**
4. Add the repository URL: `https://github.com/simie7/eldes`
5. Select category: **Integration**
6. Click **Add**
7. Search for "Eldes Alarm with Bypass" and click **Download**
8. **Restart** Home Assistant

### Manual Installation

1. Download the `custom_components/eldes_alarm` folder from this repository
2. Copy it to your Home Assistant `/config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Eldes Alarm**
3. Enter your Eldes Cloud credentials:
   - **Email** -- your Eldes Cloud account email
   - **Password** -- your Eldes Cloud account password
   - **PIN** -- your alarm system PIN code
4. Select the device/location you want to integrate
5. The integration will create entities for all partitions, outputs, sensors, and zones

**Multiple devices:** If you have multiple Eldes alarms on the same cloud account, add each one as a separate integration entry. They will share a single API session, avoiding the token collision issues present in the original integration.

## Configuration Options

After setup, click **Configure** on the integration to adjust:

| Option | Default | Range | Description |
|---|---|---|---|
| Scan interval | 15 seconds | 5--300 | How often to poll the Eldes Cloud API |
| Events list size | 10 | 5--50 | Number of recent events to fetch |
| PIN | -- | -- | Update the alarm PIN code |

## Zone Bypass

### Service: `eldes_alarm.arm_with_bypass`

Arm the alarm in **away** mode while bypassing specified zones.

```yaml
service: eldes_alarm.arm_with_bypass
data:
  bypass_zones:
    - 7
    - 12
```

### Service: `eldes_alarm.arm_home_with_bypass`

Arm the alarm in **home/stay** mode while bypassing specified zones.

```yaml
service: eldes_alarm.arm_home_with_bypass
data:
  bypass_all: true
```

| Field | Type | Description |
|---|---|---|
| `bypass_zones` | list of integers | Zone IDs to bypass (find IDs in zone entity attributes) |
| `bypass_all` | boolean | Bypass all non-disabled zones |

### Bypass Notification Automation

When arming fails (e.g., a door is open), the integration fires an `eldes_alarm_arm_failed` event. You can use this to send an actionable notification to your phone with a "Bypass & Arm" button.

An example automation is provided in [`docs/automations/bypass_notification.yaml`](docs/automations/bypass_notification.yaml). To use it:

1. Copy the automation into your `automations.yaml` or the HA automation editor
2. Replace `notify.mobile_app_YOUR_PHONE` with your actual notification service
3. Reload automations

The notification includes a 60-second timeout, giving you time to read the zone list and decide.

## Zone Binary Sensors

Each non-disabled zone from your alarm system appears as a binary sensor. The device class is automatically detected from the zone name:

| Keywords (EN/LT) | Device Class |
|---|---|
| door, durys, gate, vartai | Door |
| window, langas | Window |
| PIR, motion, judesio | Motion |
| smoke, dumai | Smoke |
| gas, dujos | Gas |
| water, flood, vanduo | Moisture |
| SD, stikl, glass | Vibration (glass break) |

Zone IDs are available as entity attributes for use with bypass services.

> **Note:** Zone binary sensors show **discovery data only** -- they list all configured zones with their names, IDs, and device class. Real-time zone status (door open/closed, motion detected) is **not available** via the Eldes Cloud API. The cloud only reports zone violations when an arm command is attempted. For real-time zone monitoring, a local integration (USB/RS485) would be needed.

## Event Entity

The integration creates an **Event Feed** entity that fires native Home Assistant events for:
- Alarms
- Arm/disarm actions
- Zone tamper/restore
- Trouble/restore
- Power failure/restore
- Zone bypass/restore

Use these in automations via the `state_changed` trigger on the event entity.

## Supported Devices

- [ESIM364](https://eldesalarms.com/hybrid-alarm-control-panel-with-gsm-gprs-communicator-esim364)
- [ESIM384](https://eldesalarms.com/esim384)
- [Pitbull Alarm PRO](https://eldesalarms.com/pitbull-alarm-pro)
- EPIR3

## Troubleshooting

- **Zones not appearing?** Make sure the integration has restarted after updating. Zones are fetched from the `device/list-zones` API endpoint.
- **Bypass not working?** Verify the zone IDs match what the API returns (check the `zone_id` attribute on binary sensor entities).
- **Events missing?** The events endpoint may return empty for some devices. Check HA logs with `logger` set to `debug` for `custom_components.eldes_alarm`.
- **One alarm going unavailable?** If you have multiple alarms on the same account, make sure you are on v2.1.1+ which shares a single API session. Older versions created separate sessions that invalidated each other's tokens.
- **Token refresh errors?** The integration automatically falls back to a full re-login if token refresh fails. If you see persistent auth errors, verify your credentials in the integration options.

## License

This project is licensed under the MIT License -- see [LICENSE](LICENSE) for details.

## Credits

- Original integration by [@augustas2](https://github.com/augustas2) -- [augustas2/eldes](https://github.com/augustas2/eldes)
- Zone bypass, zone sensors, event entities, system fault monitoring, multi-device fix, and arm failure detection by [@simie7](https://github.com/simie7)
