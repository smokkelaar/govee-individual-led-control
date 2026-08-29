# H70B3 via actieve ESPHome Bluetooth-proxy

De integratie gebruikt Home Assistants centrale Bluetoothlaag. Daardoor hoeft er in de Govee-code geen apart proxy-IP te staan: Home Assistant kiest een connectable lokale adapter of actieve ESPHome-proxy die het MAC-adres ziet.

## Minimale ESPHome-basis

Neem in het ESP32-configuratiebestand ten minste dit op naast de normale `wifi`, `api`, `ota` en loggerconfiguratie:

```yaml
esp32_ble_tracker:

bluetooth_proxy:
  active: true
```

`active: true` is essentieel: advertenties alleen zijn niet genoeg. H70B3 vereist verbinden, notifications inschakelen, geauthenticeerde GATT-writes en antwoorden ontvangen.

## Plaatsing

- Plaats de proxy eerst dichtbij het H70B3-regelkastje, niet alleen dichtbij het doek.
- Zorg voor stabiele Wi-Fi en USB-voeding.
- Laat bij de eerste proef de Govee Android-app volledig gesloten; die kan de Bluetoothverbinding bezet houden.
- Eén proxy kan meerdere Bluetoothapparaten bedienen, maar gelijktijdige zware transfers kunnen vertragen.

## Veilige testvolgorde

1. Controleer in Home Assistant dat de ESPHome-node online is en Bluetooth Proxy vermeldt.
2. Voeg H70B3 toe met het Bluetooth-MAC-adres dat Home Assistant of de Govee-app voor jouw unit toont.
3. Configuratie/setup mag niets aan het zichtbare patroon veranderen.
4. Druk één keer op **Oriëntatie tonen**.
5. Verwacht: linksboven rood, rechtsboven groen, linksonder blauw, rechtsonder wit.
6. Kijk in de transportsensor naar `connected`, `successful_uploads` en `last_error`.
7. Test daarna pas één pixel of de demoschuif.

Als de fysieke mapping gespiegeld is, gebruik de horizontale of verticale spiegelswitch. Verander de automationcoördinaten niet.

## Fouten duiden

- **not currently visible over Bluetooth**: proxy ziet geen connectable advertentie; controleer afstand, actieve modus en of de app dicht is.
- **connection was lost**: radio/Wi-Fi/voeding of een tweede client onderbrak de sessie.
- **write characteristic is missing**: verkeerde unit, onvolledige service discovery of firmwareverschil.
- **frame upload failed after reconnect**: diagnostiek bewaren; niet meteen protocolbytes wijzigen.
- upload telt op maar geen beeld: controleer eerst activatieantwoord, montage/spiegeling en fysieke power state.

De directe PC-Bluetoothroute is bewezen. De ESPHome-proxyroute gebruikt dezelfde Home Assistant-connectable API, maar moet op deze installatie nog één keer fysiek met het hoekpatroon worden bevestigd.

Officiële achtergrond:

- https://www.home-assistant.io/integrations/bluetooth
- https://esphome.io/components/bluetooth_proxy/
- https://developers.home-assistant.io/docs/core/bluetooth/api/
