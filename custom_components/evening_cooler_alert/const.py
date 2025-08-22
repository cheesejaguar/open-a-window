DOMAIN = "evening_cooler_alert"
PLATFORMS = ["binary_sensor", "button"]

CONF_NAME = "name"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_OUTDOOR_ENTITY = "outdoor_entity"
CONF_DELTA = "delta"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_SUNSET_OFFSET_MIN = "sunset_offset_min"
CONF_EVENING_LATEST = "evening_latest"
CONF_DAILY_RESET = "daily_reset"
CONF_STABILITY_WINDOW = "stability_window"
CONF_TITLE = "title"
CONF_BODY_TEMPLATE = "body_template"

DEFAULT_NAME = "Evening Cooler Alert"
DEFAULT_DELTA = 2.0
DEFAULT_SUNSET_OFFSET_MIN = 0
DEFAULT_DAILY_RESET = "12:00"
DEFAULT_STABILITY_WINDOW = 0
DEFAULT_TITLE = "Cooler Outside Now"
DEFAULT_BODY_TEMPLATE = (
    "Outside ({{ outside }}°) is cooler than inside ({{ inside }}°) by {{ delta }}°"
)

STORAGE_KEY_FMT = DOMAIN + ".{}"
STORAGE_VERSION = 1

