from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CoolerAlertCoordinator
from .entity import BaseECAEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: CoolerAlertCoordinator = hass.data[DOMAIN][entry.entry_id]
    name_slug = _slugify(entry.title or entry.data.get("name") or "evening_cooler_alert")
    ent = CoolerBinarySensor(coordinator, entry, name_slug)
    async_add_entities([ent])


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("__", "_")
    )


class CoolerBinarySensor(BaseECAEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.COLD

    def __init__(self, coordinator: CoolerAlertCoordinator, entry: ConfigEntry, slug: str) -> None:
        super().__init__(coordinator, entry)
        self._slug = slug
        # Use slug to control entity_id formation closely
        self._attr_has_entity_name = False
        self._attr_name = f"{slug}_outside_cooler_than_inside_by_delta"
        self._attr_unique_id = f"{entry.entry_id}_outside_cooler_than_inside_by_delta"

    @property
    def is_on(self) -> bool | None:
        try:
            return self.coordinator.is_cooler()
        except Exception:  # noqa: BLE001
            return None

    @property
    def icon(self) -> str | None:
        return "mdi:thermometer-chevron-down"
