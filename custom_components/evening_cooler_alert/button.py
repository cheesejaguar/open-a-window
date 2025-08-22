from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CoolerAlertCoordinator
from .entity import BaseECAEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: CoolerAlertCoordinator = hass.data[DOMAIN][entry.entry_id]
    ent = ResetTodayButton(coordinator, entry)
    async_add_entities([ent])


class ResetTodayButton(BaseECAEntity, ButtonEntity):
    def __init__(self, coordinator: CoolerAlertCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        slug = (entry.title or entry.data.get("name") or "evening_cooler_alert").lower().replace(" ", "_")
        self._attr_has_entity_name = False
        self._attr_name = f"{slug}_reset_today"
        self._attr_unique_id = f"{entry.entry_id}_reset_today"
        self._attr_icon = "mdi:backup-restore"

    async def async_press(self) -> None:
        await self.coordinator.async_reset_today()
