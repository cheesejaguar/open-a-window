from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class BaseECAEntity:
    def __init__(self, coordinator, entry) -> None:
        self.coordinator = coordinator
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title or self._entry.data.get("name"),
            manufacturer="Custom",
            model="Evening Cooler Alert",
        )

    async def async_added_to_hass(self) -> None:
        # Subscribe to coordinator update bus event
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_update_{self._entry.entry_id}", lambda _: self.async_write_ha_state()
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.coordinator.get_attributes()

