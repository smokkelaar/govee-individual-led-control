"""Constants for Govee Individual LED Control."""

from typing import Final

DOMAIN: Final = "govee_led_control"
MANUFACTURER: Final = "Govee"

MODEL_H6069: Final = "h6069"
MODEL_H70B3: Final = "h70b3"
TRANSPORT_LAN: Final = "lan"
TRANSPORT_BLUETOOTH: Final = "bluetooth"
TRANSPORT_MATTER: Final = "matter"

CONF_MODEL: Final = "model"
CONF_TRANSPORT: Final = "transport"
CONF_PANEL_COUNT: Final = "panel_count"
CONF_TOPOLOGY_PT: Final = "topology_pt"
CONF_CREATE_PIXEL_ENTITIES: Final = "create_pixel_entities"
CONF_DEBOUNCE_MS: Final = "debounce_ms"
CONF_IDLE_DISCONNECT_SECONDS: Final = "idle_disconnect_seconds"

DEFAULT_H6069_HOST: Final = "192.168.1.100"
DEFAULT_H6069_NAME: Final = "Govee H6069 panelen"
DEFAULT_H6069_PANEL_COUNT: Final = 40
DEFAULT_H6069_DEBOUNCE_MS: Final = 200
MIN_PANEL_COUNT: Final = 1
MAX_PANEL_COUNT: Final = 70

DEFAULT_H70B3_ADDRESS: Final = "AA:BB:CC:DD:EE:FF"
DEFAULT_H70B3_NAME: Final = "Govee Curtain H70B3"
DEFAULT_CREATE_PIXEL_ENTITIES: Final = True
DEFAULT_H70B3_DEBOUNCE_MS: Final = 150
DEFAULT_IDLE_DISCONNECT_SECONDS: Final = 15

H70B3_WIDTH: Final = 20
H70B3_HEIGHT: Final = 26
H70B3_PIXEL_COUNT: Final = H70B3_WIDTH * H70B3_HEIGHT

SERVICE_SET_ELEMENTS: Final = "set_elements"
SERVICE_SET_PIXELS: Final = "set_pixels"
SERVICE_SET_FRAME: Final = "set_frame"
SERVICE_APPLY_LEVEL: Final = "apply_level"
SERVICE_CLEAR: Final = "clear"
SERVICE_COMMIT: Final = "commit"
SERVICE_SHOW_DEMO: Final = "show_demo"
SERVICE_SHOW_ORIENTATION: Final = "show_orientation"

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_ELEMENTS: Final = "elements"
ATTR_INDEX: Final = "index"
ATTR_PIXELS: Final = "pixels"
ATTR_COLORS: Final = "colors"
ATTR_COLOR: Final = "color"
ATTR_X: Final = "x"
ATTR_Y: Final = "y"
ATTR_REPLACE: Final = "replace"
ATTR_COMMIT: Final = "commit"
ATTR_BRIGHTNESS_PERCENT: Final = "brightness_percent"
ATTR_LEVEL: Final = "level"
ATTR_STYLE: Final = "style"

STYLE_BAR: Final = "bar"
STYLE_POSITION: Final = "position"
STYLE_PULSE: Final = "pulse"
LEVEL_STYLES: Final = (STYLE_BAR, STYLE_POSITION, STYLE_PULSE)

DATA_RUNTIMES: Final = "runtimes"
DATA_SERVICES_REGISTERED: Final = "services_registered"
