"""Declarative model and transport capability registry."""

from __future__ import annotations

from dataclasses import dataclass

from .const import MODEL_H6069, MODEL_H70B3, TRANSPORT_BLUETOOTH, TRANSPORT_LAN


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Capabilities known for one tested Govee model."""

    key: str
    sku: str
    name: str
    full_control_transport: str
    element_label: str
    element_count: int
    transport_support: dict[str, str]
    smart_functions: dict[str, str]
    evidence: str


MODEL_SPECS: dict[str, ModelSpec] = {
    MODEL_H6069: ModelSpec(
        key=MODEL_H6069,
        sku="H6069",
        name="Mini Panel Lights",
        full_control_transport=TRANSPORT_LAN,
        element_label="panel",
        element_count=40,
        transport_support={
            "lan": "Volledige individuele paneelcontrole, fysiek bewezen",
            "bluetooth": "Hardware aanwezig; niet geïmplementeerd voor panelen",
            "matter": "Basisbediening door apparaat; geen individuele panelen",
        },
        smart_functions={
            "music_sync": "Officieel beschikbaar; protocol nog niet geïmplementeerd",
            "shape_recognition": "Fysieke indeling via alleen-lezen LAN-status uitleesbaar",
            "inner_panel_leds": "Hardware-indicatie gezien; externe adressering nog niet bewezen",
            "sensor_level_demo": "Beschikbaar via een Home Assistant-sensor",
            "motion_sensor": "Geen ingebouwde bewegingssensor aangetoond",
        },
        evidence="LAN ptReal/A3 en status.pt-topologie op echte 40-paneelinstallatie bevestigd",
    ),
    MODEL_H70B3: ModelSpec(
        key=MODEL_H70B3,
        sku="H70B3",
        name="Curtain Lights 2",
        full_control_transport=TRANSPORT_BLUETOOTH,
        element_label="led",
        element_count=520,
        transport_support={
            "lan": "Alleen basisbediening; 520-pixelupload fysiek afgewezen",
            "bluetooth": "Volledige 20x26-pixelcontrole, fysiek bewezen",
            "matter": "Basisbediening door apparaat; geen individuele leds",
        },
        smart_functions={
            "music_sync": "Acht modi officieel genoemd; invoer/protocol nog onbekend",
            "image_gif": "Officieel beschikbaar; statische PNG via BLE bewezen",
            "sensor_level_demo": "Beschikbaar via een Home Assistant-sensor",
            "motion_sensor": "Geen ingebouwde bewegingssensor aangetoond",
        },
        evidence="Versleutelde BLE A4/58-upload op echte 520-led H70B3 bevestigd",
    ),
}


def get_model_spec(model: str) -> ModelSpec:
    """Return the immutable specification for a configured model."""
    try:
        return MODEL_SPECS[model]
    except KeyError as err:
        raise ValueError(f"Unsupported Govee model {model!r}") from err
