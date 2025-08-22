from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Any, Callable, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_point_in_time,
    async_track_sunset,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import Template
from homeassistant.util.dt import now as dt_now, as_local, parse_time

from .const import (
    DOMAIN,
    STORAGE_KEY_FMT,
    STORAGE_VERSION,
    CONF_CLIMATE_ENTITY,
    CONF_OUTDOOR_ENTITY,
    CONF_DELTA,
    CONF_NOTIFY_SERVICE,
    CONF_SUNSET_OFFSET_MIN,
    CONF_EVENING_LATEST,
    CONF_DAILY_RESET,
    CONF_STABILITY_WINDOW,
    CONF_TITLE,
    CONF_BODY_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class StoredState:
    sent_today: bool = False
    last_sent_iso: Optional[str] = None


class CoolerAlertCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data = entry.data
        self.options = entry.options

        self.climate_entity: str = self._cfg(CONF_CLIMATE_ENTITY)
        self.outdoor_entity: str = self._cfg(CONF_OUTDOOR_ENTITY)
        self.delta: float = float(self._cfg(CONF_DELTA))
        self.notify_service: str = self._normalize_notify_service(
            str(self._cfg(CONF_NOTIFY_SERVICE))
        )
        self.sunset_offset_min: int = int(self._cfg(CONF_SUNSET_OFFSET_MIN))
        self.evening_latest: Optional[str] = self._cfg(CONF_EVENING_LATEST)
        self.daily_reset: str = self._cfg(CONF_DAILY_RESET)
        self.stability_window: int = int(self._cfg(CONF_STABILITY_WINDOW))
        self.title: str = self._cfg(CONF_TITLE)
        self.body_template: str = self._cfg(CONF_BODY_TEMPLATE)

        self._listeners: list[Callable[[], None]] = []
        self._every5_listener: Optional[Callable[[], None]] = None
        self._pending_stability: Optional[Callable[[], None]] = None

        self.store = Store[dict[str, Any]](
            self.hass, STORAGE_VERSION, STORAGE_KEY_FMT.format(self.entry.entry_id)
        )
        self.sent_today: bool = False
        self.last_sent: Optional[datetime] = None

        self._last_sunset: Optional[datetime] = None

    async def async_start(self) -> None:
        await self._async_load_store()
        self._setup_listeners()
        # Initial compute for attributes
        await self.async_evaluate("startup")

    def _cfg(self, key: str, default: Any | None = None) -> Any:
        if key in self.options:
            return self.options.get(key)
        return self.data.get(key, default)

    async def async_unload(self) -> None:
        for unsub in self._listeners:
            try:
                unsub()
            except Exception:  # noqa: BLE001
                pass
        self._listeners.clear()
        if self._every5_listener:
            try:
                self._every5_listener()
            except Exception:  # noqa: BLE001
                pass
            self._every5_listener = None
        self._cancel_stability()

    def _normalize_notify_service(self, value: str) -> str:
        value = value.strip()
        if value.startswith("notify."):
            return value
        return f"notify.{value}"

    async def _async_load_store(self) -> None:
        data = await self.store.async_load()
        if data:
            self.sent_today = bool(data.get("sent_today", False))
            last = data.get("last_sent_iso")
            if last:
                try:
                    self.last_sent = as_local(datetime.fromisoformat(last))
                except Exception:  # noqa: BLE001
                    self.last_sent = None

    async def _async_save_store(self) -> None:
        await self.store.async_save(
            {
                "sent_today": self.sent_today,
                "last_sent_iso": self.last_sent.isoformat() if self.last_sent else None,
            }
        )

    def _setup_listeners(self) -> None:
        # State change listeners
        self._listeners.append(
            async_track_state_change_event(
                self.hass, [self.outdoor_entity, self.climate_entity], self._state_changed
            )
        )

        # Sunset listener with offset
        offset = timedelta(minutes=self.sunset_offset_min)
        self._listeners.append(
            async_track_sunset(self.hass, self._handle_sunset, offset=offset)
        )

        # Every 5 minutes tick
        self._every5_listener = async_track_time_change(
            self.hass, self._handle_every5, second=0, minute=list(range(0, 60, 5))
        )

        # Daily reset
        reset_t = parse_time(self.daily_reset)
        if reset_t is None:
            reset_t = time(12, 0)
        self._listeners.append(
            async_track_time_change(
                self.hass, self._handle_daily_reset, hour=reset_t.hour, minute=reset_t.minute, second=0
            )
        )

    @callback
    async def _state_changed(self, event) -> None:  # type: ignore[override]
        await self.async_evaluate("state_change")

    @callback
    async def _handle_sunset(self, _dt: datetime) -> None:
        self._last_sunset = _dt
        await self.async_evaluate("sunset")

    @callback
    async def _handle_every5(self, now_dt: datetime) -> None:
        # Only evaluate in evening window
        if self._is_evening(now_dt):
            await self.async_evaluate("every5")

    @callback
    async def _handle_daily_reset(self, _dt: datetime) -> None:
        self.sent_today = False
        await self._async_save_store()
        # Also clear pending stability
        self._cancel_stability()
        # Entities can update
        self._async_request_entity_updates()

    def _is_after_sunset(self, when: Optional[datetime] = None) -> bool:
        # We rely on last sunset event or compute logically using hass sun if available
        when = when or dt_now()
        # If we have received sunset callback and it's before midnight relative to now
        if self._last_sunset:
            return when >= self._last_sunset
        # Fallback: allow checks any time after 15:00 local as an approximation until first sunset event
        return when.time() >= time(15, 0)

    def _is_before_latest(self, when: Optional[datetime] = None) -> bool:
        if not self.evening_latest:
            return True
        t = parse_time(self.evening_latest)
        if t is None:
            return True
        when = when or dt_now()
        return when.time() <= t

    def _is_evening(self, when: Optional[datetime] = None) -> bool:
        return self._is_after_sunset(when) and self._is_before_latest(when)

    def _get_inside_outside(self) -> tuple[Optional[float], Optional[float]]:
        st_out = self.hass.states.get(self.outdoor_entity)
        st_in = self.hass.states.get(self.climate_entity)
        outside = None
        inside = None
        if st_out and st_out.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            try:
                outside = float(st_out.state)
            except (ValueError, TypeError):
                outside = None
        if st_in:
            # For climate entity, current_temperature attribute
            try:
                inside_val = st_in.attributes.get("current_temperature")
                if inside_val is not None:
                    inside = float(inside_val)
            except (ValueError, TypeError):
                inside = None
        return inside, outside

    def condition_holds(self) -> bool:
        inside, outside = self._get_inside_outside()
        if inside is None or outside is None:
            return False
        return outside < (inside - self.delta)

    async def async_evaluate(self, reason: str) -> None:
        # Update attributes on entities
        self._async_request_entity_updates()

        if not self._is_evening():
            self._cancel_stability()
            return

        if self.sent_today:
            return

        # Evaluate condition with (optional) stability window
        if not self.condition_holds():
            self._cancel_stability()
            return

        if self.stability_window > 0:
            # Schedule delayed confirmation if not already scheduled
            if self._pending_stability is None:
                when = dt_now() + timedelta(seconds=self.stability_window)
                _LOGGER.debug("Scheduling stability confirmation at %s (%s)", when, reason)
                self._pending_stability = async_track_point_in_time(
                    self.hass, self._confirm_and_fire, when
                )
            return
        # Fire immediately
        await self._fire_notification()

    def _cancel_stability(self) -> None:
        if self._pending_stability is not None:
            try:
                self._pending_stability()
            except Exception:  # noqa: BLE001
                pass
            self._pending_stability = None

    @callback
    async def _confirm_and_fire(self, _dt: datetime) -> None:
        self._pending_stability = None
        if self._is_evening() and not self.sent_today and self.condition_holds():
            await self._fire_notification()

    async def _fire_notification(self) -> None:
        # Render template
        inside, outside = self._get_inside_outside()
        delta_val = round((inside - outside) if inside is not None and outside is not None else self.delta, 2)
        try:
            template = Template(self.body_template, self.hass)
            body = template.async_render({
                "inside": inside,
                "outside": outside,
                "delta": delta_val,
            })
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Template render failed: %s", err)
            body = self.body_template

        # Call notify service
        try:
            domain, service = self.notify_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {"title": self.title, "message": body},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to send notification via %s: %s", self.notify_service, err)
            return

        self.sent_today = True
        self.last_sent = as_local(dt_now())
        await self._async_save_store()
        self._async_request_entity_updates()

    def _async_request_entity_updates(self) -> None:
        # Let entities know to update
        self.hass.bus.async_fire(f"{DOMAIN}_update_{self.entry.entry_id}")

    # Public helpers for entities
    def get_attributes(self) -> dict[str, Any]:
        inside, outside = self._get_inside_outside()
        return {
            "inside": inside,
            "outside": outside,
            "delta": self.delta,
            "sent_today": self.sent_today,
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
            "sunset_offset_min": self.sunset_offset_min,
            "last_sunset": self._last_sunset.isoformat() if self._last_sunset else None,
            "stability_window": self.stability_window,
            "evening_latest": self.evening_latest,
            "daily_reset": self.daily_reset,
        }

    def is_cooler(self) -> bool:
        return self.condition_holds()

    async def async_reset_today(self) -> None:
        self.sent_today = False
        await self._async_save_store()
        self._async_request_entity_updates()
