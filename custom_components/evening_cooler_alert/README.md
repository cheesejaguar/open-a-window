# Evening Cooler Alert

Send exactly one alert each evening (after sunset) when it becomes cooler outside than inside by a configurable delta. Designed for Nest (or any climate entity exposing `current_temperature`) with an outdoor temperature sensor.

## Features

- One notification per evening after sunset
- Compares outdoor sensor with Nest `current_temperature`
- Configurable delta threshold (default 2.0 °)
- Optional sunset offset and latest evening time window
- Stability window (hysteresis) to avoid flapping
- Daily reset time (default 12:00) to allow a new alert next evening
- Persisted state across restarts (sent_today and last_sent)
- Exposes a binary sensor for visibility and a reset button
- Multiple entries supported (e.g., different rooms/sensors)

## Installation

1. Copy this folder to `custom_components/evening_cooler_alert/` in your Home Assistant config directory.
2. Restart Home Assistant.
3. Go to Settings → Integrations → Add Integration → search for "Evening Cooler Alert".

## Configuration (UI)

- Name: Display name for this alert (default: "Evening Cooler Alert"). Used to build the entity slug.
- Nest climate entity: Choose your Nest climate entity (domain `climate.*`). The integration reads `current_temperature`.
- Outdoor temperature entity: Choose the sensor that represents outdoor temperature (domain `sensor.*`). Must be numeric.
- Delta threshold: Minimum difference (inside - outside) to trigger notification. Default 2.0.
- Notify service: A `notify.*` service to call (e.g., `notify.mobile_app_phone`).
- Sunset offset minutes: Shift the sunset trigger by minutes (negative for earlier). Default 0.
- Evening latest time: Optional HH:MM. If set, alerts only occur before this time.
- Daily reset time: Time of day to clear the "sent today" flag (default 12:00).
- Stability window seconds: If > 0, the condition must hold continuously for this many seconds before firing (default 0).
- Notification title: Title for the notification (default: "Cooler Outside Now").
- Notification body template: Jinja template with variables `inside`, `outside`, and `delta`.

### Template variables

- `inside`: Current inside temperature (float)
- `outside`: Current outside temperature (float)
- `delta`: Difference `inside - outside` at send time (float, rounded)

Example body:
```
Outside ({{ outside }}°) is cooler than inside ({{ inside }}°) by {{ delta }}°.
Try opening some windows to cool down naturally.
```

## How It Works

1. The integration monitors:
   - Outdoor sensor changes
   - Climate entity changes (for `current_temperature`)
   - Sunset (with optional offset)
   - Every 5 minutes during the evening window (after sunset and before latest time if set)
2. When `outside < inside - delta` holds after sunset and `sent_today` is false:
   - If `stability_window` is 0: sends notification immediately.
   - If `stability_window` > 0: verifies the condition remains true for the specified seconds before sending.
3. After sending, it sets `sent_today = true` and records `last_sent`.
4. At the daily reset time (default 12:00), it clears `sent_today`.
5. State persists across restarts.

## Entities

- Binary sensor: `<slug>_outside_cooler_than_inside_by_delta`
  - State: ON when `outside < inside - delta`
  - Attributes: `inside`, `outside`, `delta`, `sent_today`, `last_sent`, `sunset_offset_min`, `last_sunset`, `stability_window`, `evening_latest`, `daily_reset`

- Button: `<slug>_reset_today`
  - Press to clear `sent_today` immediately.

The `slug` is derived from the configured Name (lowercase, spaces to underscores). Multiple integrations can coexist with different names.

## Examples

- Typical setup: `climate.living_room`, `sensor.outdoor_temp`, delta `2.0`, notify `notify.mobile_app_mypixel`.
- Sunset offset: Set `-30` to start checking 30 minutes before sunset.
- Latest time: Set `22:30` to avoid late-night notifications.
- Stability: Set `300` seconds to require 5 minutes of stable coolness difference.

## Troubleshooting

- No notification sent:
  - Verify the outdoor sensor and climate `current_temperature` are available and numeric.
  - Check the binary sensor state and attributes to see if the condition is true.
  - Confirm you are after sunset or within your configured evening window.
  - Ensure your `notify.*` service exists and is working (try calling it from Developer Tools).

- Multiple entries: You can add another instance with a different name and sensor/climate pairing.

## Advanced Use

- Multiple Nests: Create separate entries per room/thermostat and sensor.
- Averaging sensors: Use a template sensor or a statistics/average sensor as the outdoor source, then point this integration to that sensor.

## FAQ

- Does it work without the Sun integration? Yes, it listens for sunset events if available and falls back to a late-afternoon approximation until first sunset is received. You can also use a negative offset to start earlier.
- Will it spam me? No, it sends at most one notification per day and only in the evening window.
- Can I change the message? Yes, use the title and body template fields; the body supports `inside`, `outside`, and `delta` variables.

## License

MIT

