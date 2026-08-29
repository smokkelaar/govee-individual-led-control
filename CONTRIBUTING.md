# Contributing

Contributions are welcome, especially captures and physical verification for additional Govee models.

## Evidence levels

- **Physically verified:** an individual element visibly changed on owned hardware and the exact command path is documented.
- **Officially advertised:** Govee documents the feature, but the local command protocol is not yet proven.
- **Experimental:** packet or implementation hypothesis that must not replace a stable adapter.

Never publish account credentials, API keys, unique device addresses, private IPs or captures containing unrelated traffic.

## Adding a model

1. Add a separate pure protocol module and model controller.
2. Register an explicit transport capability contract in `model_registry.py`.
3. Add dependency-free reference-vector tests.
4. Ensure setup, restore and reload transmit nothing.
5. Physically test one unmistakable identification pattern.
6. Update model support, protocol and user documentation.

Run before opening a pull request:

```bash
python -m compileall -q custom_components/govee_led_control
python -m unittest discover -s tests -v
```

All HACS Action and Hassfest checks must pass without ignores.
