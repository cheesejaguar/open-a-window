# Evening Cooler Alert (Home Assistant)

Send exactly one alert each evening (after sunset) when it’s cooler outside than inside by a configurable delta. Ideal for Nest thermostats (uses `current_temperature`) and any numeric outdoor temperature sensor.

**Domain**: `evening_cooler_alert`  •  **Path**: `custom_components/evening_cooler_alert/`

## Features
- One notification per evening after sunset
- Compares outdoor sensor vs. Nest `current_temperature`
- Delta threshold (default 2.0 °) and optional stability window
- Sunset offset and “latest evening” time window
- Daily reset time (default 12:00)
- Restart-safe persistence (`sent_today`, `last_sent`)
- Entities: binary sensor + reset button
- Multiple entries supported (different rooms/sensors)

## Requirements
- Home Assistant OS (HAOS) or Core/Supervised with access to `config/custom_components`
- One climate entity (e.g., `climate.living_room`) exposing `current_temperature`
- One outdoor temperature sensor (e.g., `sensor.outdoor_temperature`) with numeric state
- A working `notify.*` service (mobile app, persistent notifications, etc.)

## Install on HAOS
Manual installation is simplest on HAOS via the Samba or SSH add-on.

1) Enable file access
- Add-on store → install and start either:
  - Samba share (access `\\<HA_IP>\\config` from your computer), or
  - SSH & Web Terminal (access `/config` over SSH).

2) Copy the integration
- On your PC: create the folder `config/custom_components/evening_cooler_alert/`.
- Copy this repository’s `custom_components/evening_cooler_alert/` contents into that folder.

Final structure should look like:
```
/config/custom_components/evening_cooler_alert/
  __init__.py
  manifest.json
  const.py
  coordinator.py
  binary_sensor.py
  button.py
  entity.py
  config_flow.py
  strings.json
  translations/en.json
```

3) Restart Home Assistant
- Settings → System → Restart (or `Developer Tools → YAML → Restart`).

4) Add the integration
- Settings → Devices & Services → Add Integration → search for “Evening Cooler Alert”.

### Upgrading
- Replace the files in `/config/custom_components/evening_cooler_alert/` with the new version.
- Restart Home Assistant.

## Configuration (UI)
- Name: Display name (default: “Evening Cooler Alert”). Used to derive entity slugs.
- Nest climate entity: Pick your `climate.*` entity; the integration reads `current_temperature`.
- Outdoor temperature entity: Pick your `sensor.*` entity; must be numeric.
- Delta threshold: Required difference (inside - outside) to alert. Default 2.0.
- Notify service: A `notify.*` service (e.g., `notify.mobile_app_pixel_8` or `notify.persistent_notification`).
- Sunset offset minutes: Shift sunset trigger by minutes (negative = earlier). Default 0.
- Evening latest time: Optional HH:MM; suppress alerts after this time.
- Daily reset time: Time of day to clear the “sent today” flag (default 12:00).
- Stability window seconds: Require condition to hold continuously for this many seconds before sending (default 0).
- Notification title: Default “Cooler Outside Now”.
- Notification body template: Jinja template; variables: `inside`, `outside`, `delta`.

Example body:
```
Outside ({{ outside }}°) is cooler than inside ({{ inside }}°) by {{ delta }}°.
Open some windows to cool down naturally.
```

### Editing options later
- Settings → Devices & Services → Evening Cooler Alert → Configure.

## How It Works
1) Listens for: outdoor temp changes, climate entity changes, sunset (with offset), and a 5‑minute tick in the evening window.
2) When after sunset (and before latest time if set) and `outside < inside - delta`:
   - If `stability_window == 0`: sends immediately.
   - Else: confirms the condition stays true for the configured seconds, then sends.
3) Sets `sent_today = true` and stores `last_sent`.
4) At the daily reset time, clears `sent_today`.
5) State is persisted across restarts.

## Entities
- Binary sensor: `<slug>_outside_cooler_than_inside_by_delta`
  - On when `outside < inside - delta`.
  - Attributes: `inside`, `outside`, `delta`, `sent_today`, `last_sent`, `sunset_offset_min`, `last_sunset`, `stability_window`, `evening_latest`, `daily_reset`.

- Button: `<slug>_reset_today`
  - Press to clear `sent_today` immediately.

`<slug>` is derived from the configured Name (lowercase; spaces → underscores). Multiple entries can coexist with different names.

## Examples
- Typical: `climate.living_room`, `sensor.backyard_temp`, delta `2.0`, notify `notify.mobile_app_mypixel`.
- Earlier checks: sunset offset `-30` (start 30 minutes before sunset).
- Quiet hours: latest time `22:30` to avoid late-night alerts.
- Flapping protection: stability `300` (5 minutes).

## Troubleshooting
- No alert received:
  - Verify `notify.*` service exists (Developer Tools → Services).
  - Check the binary sensor state; confirm the attributes show valid `inside`/`outside` numbers.
  - Ensure it’s after sunset (respecting any offset) and before your latest time.
  - Confirm the climate entity exposes `current_temperature` and it’s available.
- Re-send tonight: use the `<slug>_reset_today` button.
- Logs: Settings → System → Logs; filter by `custom_components.evening_cooler_alert`.

## Advanced Use
- Multiple Nests/rooms: Add multiple entries, each with its own climate and sensor.
- Averaging or filtering: Create a template/average sensor from multiple outdoor sensors, then select it here.

## FAQ
- Does it require the Sun integration?
  - It listens for sunset; if unavailable, it approximates until the first sunset event occurs. You may use a negative offset to start checks earlier.
- Will I get spammed?
  - No. It sends at most one alert per day (reset at your chosen time).
- Can I customize the message?
  - Yes. Use the title and body template; variables: `inside`, `outside`, `delta`.

## Uninstall
- Remove the integration instance from Settings → Devices & Services.
- Optionally delete the folder `/config/custom_components/evening_cooler_alert/` and restart HA.

## License
MIT
