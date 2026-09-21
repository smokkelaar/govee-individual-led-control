# 0.5.0 — opgeslagen LED-art

- LED Studio bevat nu een centrale galerij voor benoemde ontwerpen.
- Statische H70B3-gordijnbeelden en H6069-paneelontwerpen kunnen worden
  opgeslagen en later zonder direct verzenden opnieuw in de editor geladen.
- Verwerkte H70B3-GIF's kunnen inclusief alle LED-frames en timing worden
  opgeslagen en opnieuw afgespeeld.
- De galerij wordt in Home Assistant opgeslagen en is daardoor beschikbaar op
  alle browsers en apparaten die hetzelfde Home Assistant-systeem gebruiken.
- Verwijderen vereist altijd eerst een bevestiging in de kaart.

# 0.4.1 — responsieve LED Studio

- De kaart gebruikt nu zijn eigen beschikbare breedte in plaats van alleen de
  volledige browserbreedte om naar een compacte indeling over te schakelen.
- Bedieningspanelen, patroonknoppen en GIF-instellingen worden op smalle
  dashboardsecties niet meer afgekapt.
- In een sectieweergave gebruikt LED Studio standaard de volledige beschikbare
  sectiebreedte.
- Dubbele kaartvermeldingen worden voorkomen wanneer dezelfde module via meer
  dan één Home Assistant-resourcepad is geladen.

# 0.4.0 — Govee LED Studio

- Gebundelde **Govee LED Studio**-dashboardkaart toegevoegd.
- Visueel tekenen en patronen voor H6069-panelen en de H70B3 20×26-matrix.
- Lokale GIF-decodering in de browser en geanimeerde H70B3-frameweergave;
  GIF-bestanden worden niet naar Home Assistant geüpload of opgeslagen.

# 0.3.1 — veilige topology-import en correcte multicastdiagnose

- H6069 `status`-ontvangst meldt zich nu aan bij multicastgroep
  `239.255.255.250` op UDP 4002; alleen binden aan de poort bleek onvoldoende.
- Fysieke hertest vastgelegd: de actuele firmware retourneert normaal 6 bytes
  runtime-`pt`, ook wanneer Shape Recognition in de Govee-app zichtbaar is, en
  niet automatisch de eerder vastgelegde 129-byte paneelkaart.
- Optionele Shape Recognition-Base64-import toegevoegd aan **Configureren**;
  header, lengte, checksum, boomstructuur, coördinaten en paneelaantal worden
  gevalideerd voordat Home Assistant de kaart gebruikt.
- Een mislukte LAN-proef overschrijft nooit een geldige geïmporteerde of
  herstelde kaart en geeft voortaan een specifieke protocolfout in plaats van
  alleen `timed out`.
- Twee socketregressietests toegevoegd; totaal nu 27.

# 0.3.0 — H6069-vormherkenning in Home Assistant

- H6069 `status.pt`-decoder toegevoegd en geverifieerd op een vastgelegde
  40-paneelkaart. De latere 0.3.1-hertest corrigeert de aanname dat iedere lege
  LAN-statusvraag deze lange kaart opnieuw retourneert.
- Expliciete knop **Paneelindeling uitlezen**; setup, reload en restore blijven
  netwerk- en lichtdata-vrij.
- Nieuwe sensor **Paneelindeling** met nummerrooster, genormaliseerde x/y-posities,
  boomverbindingen, oriëntaties, fingerprint en configuratiecontrole.
- Laatste geslaagde nummering wordt na een Home Assistant-herstart hersteld;
  opnieuw uitlezen is alleen nodig na een fysieke vormwijziging of controle.
- Standaard Markdown-dashboardkaart toegevoegd; geen extra frontendkaart nodig.
- Strikte afwijzing van onbekende headers, verkeerde lengte, checksumfouten,
  ongeldige boomstructuren en coördinaatoverlap.
- Onderzoeksspoor voor mogelijke afzonderlijke leds binnen één H6069-paneel
  gedocumenteerd zonder onbewezen ondersteuning te claimen.
- Vier topologieregressietests toegevoegd; totaal nu 25.

# 0.2.0 — eerste algemene Govee-suite

- H6069 LAN-paneeladapter en H70B3 Bluetooth-pixeladapter samengebracht onder domein `govee_led_control`.
- Modelkeuze toont vóór configuratie volledige route en LAN/Bluetooth/Matter-beperkingen.
- Oude afzonderlijke packages blijven onaangeraakt als rollback.
- Algemene element-, pixel-, frame- en 0..100-sensoracties toegevoegd.
- Herstartbestendige bar/position/pulse-preview, clear/demo/orientation-buttons en transportsensor toegevoegd.
- H70B3-spiegeling behouden voor wisselende montage.
- Actieve ESPHome Bluetooth-proxyroute voorbereid met adaptersource en bereikbaarheidsdiagnostiek.
- Dashboardtemplates voor Govee, H6069, H70B3 en optionele 520-ledmatrix toegevoegd.
- 21 regressietests voor beide protocollen, crypto en sensorvisualisaties.

Nog fysiek te bevestigen na installatie: een complete H70B3 frame-upload via de actieve ESPHome Bluetooth-proxy. Dezelfde upload via directe Bluetooth en H6069 via LAN zijn al fysiek bewezen.
