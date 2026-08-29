# Ontwikkelhandleiding

## Ontwerpregels

1. Een modeladapter bezit zijn protocol, transport en framebuffer.
2. De generieke laag kent alleen modelkey, uniforme elementacties en capabilities.
3. Een transport krijgt pas de status **volledige controle** na fysieke elementtest.
4. Setup, restore, opties en reload mogen nooit lichtdata verzenden.
5. Meerdere snelle wijzigingen worden tot één volledig frame samengevoegd.
6. Bestaande adapters blijven regressietestbaar zonder Home Assistant te importeren.

## Bestandsindeling

```text
custom_components/govee_led_control/
  __init__.py              generieke services en runtimekeuze
  config_flow.py           model-first configuratie
  model_registry.py        capabilitycontract
  runtime.py               één geconfigureerd apparaat
  h6069_protocol.py        pure LAN-encoding
  h6069_topology.py        pure status.pt-vormdecoder + read-only query
  h6069_controller.py      paneelshadow + UDP
  crypto.py                pure H70B3-bescherming
  h70b3_protocol.py        pure PNG/pakketencoding
  h70b3_ble.py             connectable Bluetoothtransport
  h70b3_controller.py      20x26-shadow + debounce
  light.py                 matrix, panelen en pixels
  button.py                expliciete test/clear/uitleesknoppen
  number.py/select.py      sensorvisualisatie-preview
  sensor.py                transport, topologie en diagnostiek
  switch.py                montage/spiegeling
```

## Uniforme acties

- `set_elements`: nulgebaseerde protocolindex voor ieder model.
- `set_pixels`: H70B3 x/y-gemaksvorm.
- `set_frame`: exact het geconfigureerde elementaantal.
- `apply_level`: generieke 0..100 mapping.
- `clear`, `commit`, `show_demo`; plus H70B3 `show_orientation`.

Wanneer meer dan één apparaat is geladen, vereist een service `config_entry_id`. Entiteiten en device buttons zijn daarom geschikter voor Lovelace.

## Een nieuw model toevoegen

1. Leg SKU, elementtype, count/dimensies en transportsupport vast in `model_registry.py`.
2. Maak een pure protocolmodule met inputvalidatie en vaste referentievectoren.
3. Schrijf regressietests die zonder HA kunnen draaien.
4. Maak een controller met dezelfde kernmethoden: `set_elements`, `set_frame`, `clear`, `apply_level`, `async_commit`, `async_shutdown`, `diagnostics`.
5. Voeg een config-flowstap toe die alleen noodzakelijke transportgegevens vraagt.
6. Voeg platforms toe zonder bestaande modelplatforms te conditioneren op toevallige attributen.
7. Documenteer wat fysiek bewezen, officieel genoemd, mislukt of onbekend is.
8. Test setup zonder verzending en daarna één duidelijk fysiek identificatiepatroon.

## Sensorvisualisatie

De controllers accepteren alleen een genormaliseerd geheel getal 0..100:

- `bar`: hoeveelheid licht als groen/geel/rood niveau;
- `position`: één positie/kolom volgt de waarde;
- `pulse`: compleet beeld verschuift van blauw naar rood.

Normalisatie van echte sensoreenheden hoort in de HA-automation, niet in de protocolcontroller. Zo blijft bijvoorbeeld 30–100 dB of 0–5 meter expliciet en controleerbaar.

## Lokale verificatie

```powershell
python -m compileall -q custom_components\govee_led_control
python -m unittest discover -s tests -v
```

Validatie vóór uitgifte:

- alle JSON parseert;
- alle YAML parseert;
- geen oude domeinnaam in code of actieve voorbeelden;
- geen pycache/pyc in archieven;
- installatiezip opent met `custom_components/govee_led_control/`;
- SHA-256 is gerapporteerd.

Pure unit tests bewijzen encoding, geen radio- of lampwerking. Een nieuwe transportwijziging moet altijd met één herkenbaar patroon fysiek worden bevestigd.
