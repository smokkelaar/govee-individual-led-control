# Model- en transportcontract

Iedere adapter registreert een `ModelSpec` in `model_registry.py`. Daarmee ziet de gebruiker vóór configuratie en via de transportsensor wat echt werkt.

## Betekenis van statussen

- **Volledig**: afzonderlijke panelen/pixels zijn fysiek aangestuurd.
- **Basis**: het apparaat ondersteunt gewone Govee-functies via dat transport, maar deze integratie gebruikt het niet voor elementdata.
- **Niet geïmplementeerd**: hardware of transport kan bestaan, maar er is geen stabiele adapter.
- **Onbekend**: niet claimen als ondersteund; eerst meten.

## H6069

- Volledige route: LAN UDP.
- Element: paneel-ID, 0..39 in de huidige installatie; encoder ondersteunt 1..70.
- Bluetooth: niet geïmplementeerd voor individuele panelen.
- Matter: alleen basisbediening buiten deze elementadapter.
- Slim: vormherkenning is via een expliciete alleen-lezen LAN-query beschikbaar
  als nummerrooster en coördinaten. Muzieksynchronisatie heeft nog geen stabiel
  HA-protocol en er is geen bewezen ingebouwde bewegingssensor.
- LEDs binnen één paneel: lokale hardware/firmware-indicatie gezien, maar nog
  geen bewezen extern adres of commando; daarom niet als element aangeboden.

## H70B3

- Volledige route: Bluetooth, lokaal of via actieve proxy.
- Element: RGB-led op een logische 20×26-matrix.
- LAN: basisbediening; drie varianten van directe pixeldata hadden geen zichtbaar resultaat.
- Matter: alleen basisbediening buiten deze elementadapter.
- Slim: acht officiële muziekmodi en appbeelden/GIF bekend; statische PNG-upload is bewezen, ingebouwde muziekmodus nog niet.

## Een model toevoegen

Een nieuw model krijgt een eigen protocol-, transport- en controllerbestand. Bestaande modelbestanden worden niet conditioneel verbouwd. Voeg daarna de modelkeuze, platforms en capabilitytekst toe. `evidence` noemt altijd het concrete fysieke bewijs; productmarketing alleen is onvoldoende voor het label **Volledig**.
