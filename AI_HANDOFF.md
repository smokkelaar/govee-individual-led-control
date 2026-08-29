# AI-overdracht — Govee Individual LED Control

## Doel en status

Dit is de beoogde algemene Govee-bibliotheek voor Home Assistant. Versie 0.2.0 combineert twee afzonderlijk bewezen adapters zonder de oude installaties te wijzigen:

- H6069 Mini Panel Lights: volledige individuele paneelcontrole via LAN.
- H70B3 Curtain Lights 2: volledige 520-ledcontrole via Bluetooth; bedoeld voor directe Bluetooth of een actieve ESPHome Bluetooth-proxy.

De integratie maakt bij setup geen fysiek commando of statusquery. Demo's,
sensorreacties en de read-only H6069-topologiequery zijn alleen expliciet
bedienbaar.

## Fysiek bewezen feiten — niet opnieuw gokken

### H6069

- het privé-IP van de geteste installatie is bewust niet gepubliceerd;
- UDP-poort 4003, `ptReal`, gegroepeerde A3-data;
- 40 fysieke panelen; nulgebaseerde protocol-ID's;
- referentietest: ID 5 rood en alle andere blauw veranderde exact één paneel;
- zichtbare reactie ongeveer 300 ms;
- UDP heeft geen ack of kleur-readback; toestand is optimistisch.
- `status` retourneert een checksum-beschermde `pt`-topologie; de decoder levert
  exact de 40-paneelvorm en nummering uit de Shape Recognition-screenshot.
- knop **Paneelindeling uitlezen** verandert geen lichtdata; sensor
  **Paneelindeling** bevat rooster, coördinaten, verbindingen en fingerprint.
- de sensor herstelt zijn laatste geslaagde rooster na HA-herstart; een nieuwe
  query blijft expliciet en is alleen nodig na vormwijziging of live controle.
- statische A3-frames bewijzen alleen één RGB-waarde per paneel. Een zichtbare
  blauw/groene foutwaas suggereert interne emittercontrole, maar is geen bewijs
  voor een extern subpaneelprotocol; zie `H6069_INNER_LED_RESEARCH.md`.

De oude terugvalintegratie staat in `outputs/govee_h6069_panels` en de oude installatiezip blijft behouden.

### H70B3

- het unieke BLE-adres van de geteste unit is bewust niet gepubliceerd;
- advertentienaam volgt het patroon `Govee_H70B3_*`;
- matrix: 20×26 = 520 RGB-leds;
- versleutelde/geauthenticeerde BLE A4/58 PNG-upload is fysiek bewezen;
- bewezen: rode/blauwe X, afzonderlijke pixels en vier hoekblokken;
- fysieke hoekmapping: linksboven rood, rechtsboven groen, linksonder blauw, rechtsonder wit;
- horizontale/verticale spiegeling hoort als blijvende HA-instelling beschikbaar te blijven.

Native LAN-pixelproeven zijn afgerond als negatief: B0/Razer maakte zwart maar renderde niet; drie ptReal-batchvormen veranderden niets. Basis-LAN bleef gezond. Claim dus geen werkende 520-pixel-LAN-route zonder nieuw, duidelijk fysiek bewijs.

De oude terugvalintegratie staat in `outputs/govee_h70b3_curtain`.

## Architectuur

- Domein: `govee_led_control`.
- `model_registry.py`: gebruikerszichtbare capability- en transportclaims.
- `h6069_topology.py`: strikte pure decoder en expliciete read-only LAN-query.
- `h6069_protocol.py` + `h6069_controller.py`: zelfstandige LAN-adapter.
- `crypto.py`, `h70b3_protocol.py`, `h70b3_ble.py`, `h70b3_controller.py`: zelfstandige Bluetoothadapter.
- `runtime.py`: dunne adapterhouder plus herstelde demosettings.
- `light.py`: paneel-, pixel- en matrixentiteiten.
- `button.py`, `number.py`, `select.py`, `sensor.py`, `switch.py`: algemene bediening, status en montage.
- `__init__.py`: generieke services; routeert alleen op `ModelSpec.key`.

Nieuwe modellen krijgen nieuwe bestanden. Breng geen modelafhankelijke heuristiek aan in bestaande protocolencoders.

## Slimme functies

Officieel bekend maar nog niet als raw Govee-modus geïmplementeerd:

- H6069: muzieksynchronisatie en vormherkenning.
- H70B3: acht muziekmodi en appafbeelding/GIF-functies.

Niet bewezen: een ingebouwde bewegingssensor, de precieze gebruikte microfoon, HA-uitlezing van audiometingen en raw commando's om Govee-muziekmodi te kiezen.

Wel geïmplementeerd: generieke 0..100 mapping (`bar`, `position`, `pulse`). Daardoor kan een externe HA-sensor veilig als bron dienen. `SMART_DEMOS.yaml` bevat uitgeschakelde, vervangbare automations. Houd H70B3-sensorupdates aanvankelijk op ongeveer één per drie seconden.

## Eerstvolgende fysieke stappen

1. Wacht tot de actieve ESPHome Bluetooth-proxy online en connectable in HA zichtbaar is.
2. Installeer de nieuwe map, herstart HA en voeg alleen H70B3 toe.
3. Druk eenmaal **Oriëntatie tonen**. Controleer de vier bekende hoeken.
4. Bekijk de transportsensor: `connected`, `successful_uploads`, `last_error`, pakketgrootte en verzendduur.
5. Test pas daarna slider, individuele pixel en sensor-demo.
6. Migreer H6069 los: oude entry eerst uitschakelen, nieuwe toevoegen en paneel-5-demo fysiek controleren.

Als een Home Assistant-knop, raw editor of herstart nodig is, stop direct en vraag de gebruiker die concrete klik uit te voeren. Besteed geen tijd aan omwegen door de HA-interface.

## Dashboard

De gebruiker wil onder **Lichtbediening** tabs voor overzicht, H6069 en H70B3. De templates zijn voorbereid maar niet live ingevoegd. Na installatie eerst de werkelijke entity-id's uitlezen; Home Assistant kan een suffix toevoegen wanneer oude entity-id's nog bestaan. Pas daarna de placeholders in `DASHBOARD_TABS.yaml` aan en laat de gebruiker de raw dashboardconfiguratie opslaan.

De H6069-tab bevat een standaard Markdown-kaart die `grid_text` uit de
topologiesensor toont; daarvoor is geen custom frontendkaart nodig. De optionele
520-ledkaart in `DASHBOARD_H70B3_FULL_GRID.yaml` gebruikt Auto Entities.
Controleer eerst of die HACS-frontendkaart al is geïnstalleerd; maak de hoofdtab
niet afhankelijk van die kaart.

## Verificatie

Voer vanuit de projectmap uit met een beschikbare Python 3.12-runtime:

```powershell
python -m compileall -q custom_components\govee_led_control
python -m unittest discover -s tests -v
```

Er horen 25 protocol-, topologie-, crypto- en visualisatietests te slagen.
Controleer ook JSON en YAML en zorg dat geen `__pycache__` of `.pyc` in de zip
komt.

De installatiezip moet bovenaan exact `custom_components/govee_led_control/` bevatten. De ontwikkelaarszip mag documentatie en tests bevatten.
