from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import CoolerAlertCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Evening Cooler Alert from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = CoolerAlertCoordinator(hass, entry)
    # Reload on options updates
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    coordinator: CoolerAlertCoordinator | None = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_unload()

    return unload_ok

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

