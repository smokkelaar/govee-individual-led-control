# Govee Individual LED Control

[![Validate](https://github.com/smokkelaar/govee-individual-led-control/actions/workflows/validate.yml/badge.svg)](https://github.com/smokkelaar/govee-individual-led-control/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/smokkelaar/govee-individual-led-control)](https://github.com/smokkelaar/govee-individual-led-control/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An unofficial Home Assistant integration focused on the deepest practical control of individual Govee panels, segments and LEDs. Model adapters explicitly distinguish verified full-element transports from basic LAN, Bluetooth and Matter support.

> This project is not affiliated with or endorsed by Govee. Govee product names are used only to identify compatible hardware.

## Supported models

| Model | Elements | Full-control transport | LAN | Bluetooth | Matter |
|---|---:|---|---|---|---|
| H6069 Mini Panel Lights | 40 physically tested; encoder supports up to 70 | **LAN** | individual panels physically verified | not implemented for panels | basic device control only |
| H70B3 Curtain Lights 2 | 20×26 = 520 LEDs | **Bluetooth** | basic control; native pixel upload failed physical tests | individual pixels physically verified | basic device control only |

The integration never silently substitutes Matter or cloud control for individual-element control.

## Highlights

- one RGB light entity per H6069 panel;
- strict H6069 Shape Recognition topology import, exposed as a numbered grid
  and structured panel coordinates, plus an experimental read-only LAN probe;
- one H70B3 matrix light and, optionally, 520 individual RGB light entities;
- complete-frame updates with debouncing to combine rapid changes;
- persistent horizontal and vertical curtain mirroring;
- explicit clear, proven-demo and orientation buttons;
- a transport/capability sensor with connection source and diagnostics;
- generic `0..100` visualizations: `bar`, `position` and `pulse`;
- service actions for indexed elements, H70B3 x/y pixels and complete frames;
- an included **Govee LED Studio** dashboard card with a visual editor, presets
  and local GIF-to-H70B3 animation playback;
- no physical output during setup, reload or state restoration.

The state is optimistic. H6069 UDP has no acknowledgement or visual-state readback. H70B3 acknowledges the Bluetooth upload and activation, but the visible pixel colors are not read back.

H6069 setup and reload do not query the device. A captured Shape Recognition
Base64 value can be pasted under **Configure → Shape Recognition topology**;
the options flow strictly validates its header, length, checksum, tree and panel
count before storing it. This changes no color, brightness or saved Govee
configuration. The related sensor exposes the zero-based number grid, panel
coordinates, connections and a fingerprint.

**Paneelindeling via LAN proberen** is a read-only LAN probe. H6069 replies through the
Govee multicast group on UDP 4002, but the tested firmware normally returns a
six-byte runtime `pt`, not the 129-byte learned map. The button therefore cannot
replace an import on that firmware and now reports this distinction explicitly.
The last validated map remains available after a failed probe or restart.

## HACS installation

This repository is ready to use as a HACS custom repository:

1. Open HACS in Home Assistant.
2. Open **Custom repositories**.
3. Add `https://github.com/smokkelaar/govee-individual-led-control`.
4. Select category **Integration**.
5. Install **Govee Individual LED Control** and restart Home Assistant.
6. Add the integration from **Settings → Devices & services**.

The integration also serves and loads its bundled dashboard card automatically.
After restarting Home Assistant, add **Govee LED Studio** from the dashboard card
picker or use the YAML below. GIF files stay in the browser: frames are decoded
locally and sent directly to the configured H70B3 through the integration.

The card uses the full width of a dashboard section and is container-responsive:
in a narrow section its controls stack vertically, while a wider section shows
the LED canvas and controls side by side without clipping.

```yaml
type: custom:govee-led-studio
h6069_transport_entity: sensor.h6069_transport
h6069_topology_entity: sensor.h6069_paneelindeling
h70b3_transport_entity: sensor.h70b3_transport
h6069_panel_count: 40
```

Existing entity registries can append a suffix to these entity IDs. Check the
transport and topology sensors in Home Assistant and adjust the card YAML when
needed.

The repository is prepared for later submission to the default HACS store, but is not presented as a default-store integration until the Home Assistant Brands and `hacs/default` reviews have been accepted. See [HACS_STATUS.md](HACS_STATUS.md).

### Safe migration

Earlier standalone `govee_h6069_panels` and `govee_h70b3_curtain` installations remain valid rollback options. Do not load the same physical H6069 in both integrations simultaneously. Disable the old entry first, add the new model adapter and verify the panel-5 identification demo.

For H70B3, full control requires a local connectable Bluetooth adapter or an active ESPHome Bluetooth proxy. Close the Govee mobile app during the first connection test.

## Home Assistant actions

The domain is `govee_led_control`.

```yaml
action: govee_led_control.set_pixels
data:
  pixels:
    - {x: 0, y: 0, color: "#ff0000"}
    - {x: 19, y: 25, color: "#ffffff"}
  replace: true
  commit: true
```

When more than one device is configured, provide `config_entry_id`. It is exposed as an attribute on each device's transport sensor.

See [SERVICES_EXAMPLES.yaml](SERVICES_EXAMPLES.yaml) for batching and frame examples.

## Sensor and smart-home demos

Govee advertises music-reactive modes for both products, including eight music modes for H70B3. Their raw control commands, audio source and any onboard motion sensor are not yet proven, so this integration does not fabricate those capabilities.

Instead, any real Home Assistant sensor can drive a normalized static visualization. [SMART_DEMOS.yaml](SMART_DEMOS.yaml) contains disabled examples for sound level, motion, mmWave distance and media volume. Enable a demo only after replacing its entity and config-entry placeholders.

## Dashboard examples

- **Govee LED Studio** is bundled with the integration and provides the easiest
  visual control for both supported models, including browser-local GIF playback
  for the 20×26 H70B3 matrix.
- [DASHBOARD_TABS.yaml](DASHBOARD_TABS.yaml): overview, H6069 and H70B3 views using standard cards.
- [DASHBOARD_H70B3_FULL_GRID.yaml](DASHBOARD_H70B3_FULL_GRID.yaml): optional 20×26 direct LED grid using the Auto Entities HACS frontend card.

Verify the actual Home Assistant entity IDs before adding the views; an existing entity registry may append a suffix.

## Technical documentation

- [MODEL_SUPPORT.md](MODEL_SUPPORT.md) — capability and transport contract.
- [PROTOCOL.md](PROTOCOL.md) — physically verified protocol boundaries.
- [H6069_INNER_LED_RESEARCH.md](H6069_INNER_LED_RESEARCH.md) — current evidence
  and a safe test plan for possible LEDs inside each panel.
- [PROXY_SETUP.md](PROXY_SETUP.md) — active ESPHome Bluetooth proxy setup.
- [DEVELOPMENT.md](DEVELOPMENT.md) — extension architecture and tests.
- [AI_HANDOFF.md](AI_HANDOFF.md) — evidence and continuation notes for another AI or developer.
- [RELEASE_NOTES.md](RELEASE_NOTES.md) — current release notes.

The protocol, topology, crypto and visualization suite currently contains 25 regression tests:

```bash
python -m unittest discover -s tests -v
```

## Privacy and responsible protocol research

The public repository intentionally excludes private IP addresses, unique Bluetooth addresses, API keys, account data and captures containing unrelated traffic. Protocol observations are limited to user-owned hardware.

## License

MIT. See [LICENSE](LICENSE).
