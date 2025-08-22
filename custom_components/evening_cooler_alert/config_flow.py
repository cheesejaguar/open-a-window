from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
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
    DEFAULT_NAME,
    DEFAULT_DELTA,
    DEFAULT_SUNSET_OFFSET_MIN,
    DEFAULT_DAILY_RESET,
    DEFAULT_STABILITY_WINDOW,
    DEFAULT_TITLE,
    DEFAULT_BODY_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)


class EveningCoolerAlertFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            errors = await self._validate_user_input(self.hass, user_input)
            if not errors:
                title = user_input.get(CONF_NAME, DEFAULT_NAME)
                return self.async_create_entry(title=title, data=user_input)
        else:
            user_input = {}

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): selector.selector({"text": {}}),
                vol.Required(CONF_CLIMATE_ENTITY): selector.selector(
                    {"entity": {"domain": "climate"}}
                ),
                vol.Required(CONF_OUTDOOR_ENTITY): selector.selector(
                    {"entity": {"domain": "sensor"}}
                ),
                vol.Optional(CONF_DELTA, default=DEFAULT_DELTA): selector.selector(
                    {"number": {"min": 0, "max": 50, "step": 0.1, "mode": "box"}}
                ),
                vol.Required(CONF_NOTIFY_SERVICE): selector.selector({"text": {}}),
                vol.Optional(
                    CONF_SUNSET_OFFSET_MIN, default=DEFAULT_SUNSET_OFFSET_MIN
                ): selector.selector({"number": {"min": -240, "max": 240, "step": 1}}),
                vol.Optional(CONF_EVENING_LATEST): selector.selector({"time": {}}),
                vol.Optional(CONF_DAILY_RESET, default=DEFAULT_DAILY_RESET): selector.selector(
                    {"time": {}}
                ),
                vol.Optional(
                    CONF_STABILITY_WINDOW, default=DEFAULT_STABILITY_WINDOW
                ): selector.selector({"number": {"min": 0, "max": 7200, "step": 1}}),
                vol.Optional(CONF_TITLE, default=DEFAULT_TITLE): selector.selector(
                    {"text": {}}
                ),
                vol.Optional(
                    CONF_BODY_TEMPLATE, default=DEFAULT_BODY_TEMPLATE
                ): selector.selector({"text": {}}),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors={})

    async def _validate_user_input(self, hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
        errors: dict[str, str] = {}

        # Notify service validation
        notify = str(data.get(CONF_NOTIFY_SERVICE, "")).strip()
        if not notify:
            errors[CONF_NOTIFY_SERVICE] = "required"
        else:
            if notify.startswith("notify."):
                service = notify.split(".", 1)[1]
            else:
                service = notify
                data[CONF_NOTIFY_SERVICE] = f"notify.{service}"
            if not hass.services.has_service("notify", service):
                # Warn but allow; service may be added later
                _LOGGER.warning("Notify service %s not found at config time", service)

        # Entities exist?
        if not hass.states.get(data.get(CONF_CLIMATE_ENTITY)):
            _LOGGER.warning("Climate entity %s not found during config", data.get(CONF_CLIMATE_ENTITY))
        if not hass.states.get(data.get(CONF_OUTDOOR_ENTITY)):
            _LOGGER.warning("Outdoor entity %s not found during config", data.get(CONF_OUTDOOR_ENTITY))

        return errors

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            # Merge into data by updating entry options
            return self.async_create_entry(title="", data=user_input)

        data = {**self.entry.data, **self.entry.options}
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_DELTA, default=data.get(CONF_DELTA)): selector.selector(
                    {"number": {"min": 0, "max": 50, "step": 0.1, "mode": "box"}}
                ),
                vol.Optional(
                    CONF_SUNSET_OFFSET_MIN, default=data.get(CONF_SUNSET_OFFSET_MIN)
                ): selector.selector({"number": {"min": -240, "max": 240, "step": 1}}),
                vol.Optional(CONF_EVENING_LATEST, default=data.get(CONF_EVENING_LATEST)): selector.selector(
                    {"time": {}}
                ),
                vol.Optional(CONF_DAILY_RESET, default=data.get(CONF_DAILY_RESET)): selector.selector(
                    {"time": {}}
                ),
                vol.Optional(
                    CONF_STABILITY_WINDOW, default=data.get(CONF_STABILITY_WINDOW)
                ): selector.selector({"number": {"min": 0, "max": 7200, "step": 1}}),
                vol.Optional(CONF_TITLE, default=data.get(CONF_TITLE)): selector.selector(
                    {"text": {}}
                ),
                vol.Optional(
                    CONF_BODY_TEMPLATE, default=data.get(CONF_BODY_TEMPLATE)
                ): selector.selector({"text": {}}),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

