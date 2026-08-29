# HACS publication status

## Ready now

- public single-integration GitHub repository layout;
- root `hacs.json`;
- complete `custom_components/govee_led_control/` runtime tree;
- manifest with domain, documentation, issue tracker, code owner, name and version;
- repository description, issues and topics;
- HACS Action and Hassfest workflows without ignored checks;
- original local brand assets in `custom_components/govee_led_control/brand/`;
- full GitHub release matching the manifest version;
- README, license, support and contribution information.

This is sufficient for installation as a **HACS custom repository** once the validation workflow passes.

## Required before default HACS-store inclusion

1. Confirm both HACS Action and Hassfest pass without ignored checks, including the brand check against the bundled local icon supported by Home Assistant 2026.3 and newer.
2. Keep at least one full GitHub release available.
3. Follow the then-current HACS checklist if it still requests a separate `home-assistant/brands` entry; use the same original integration icon and never a Govee trademark without permission.
4. Fork `hacs/default`, add `smokkelaar/govee-individual-led-control` alphabetically to `integration`, and submit an editable PR as the repository owner.
5. Complete the HACS PR template accurately and wait for review.

Until both review PRs are accepted, documentation must say **HACS custom repository compatible**, not **official/default HACS integration**.

References:

- https://hacs.xyz/docs/publish/integration/
- https://hacs.xyz/docs/publish/include/
- https://github.com/home-assistant/brands
- https://github.com/hacs/default
