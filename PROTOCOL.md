# Bewezen protocolgrenzen

Dit bestand scheidt fysieke waarneming van aannames. Code buiten deze grenzen moet eerst als experiment worden gemarkeerd en mag een bestaande adapter niet automatisch vervangen.

## Routering

| Model | Volledige elementdata | Endpoint | Bevestiging |
|---|---|---|---|
| H6069 | LAN UDP `ptReal` | apparaat-IP, UDP 4003 | alleen lokaal verzenden; geen ack/readback |
| H70B3 | Bluetooth GATT | het unieke MAC-adres van de unit | protocolmelding na upload en activatie |

Matter is geen elementtransport in deze integratie. De native H70B3-LAN-proeven met 520 pixels faalden; een Razer/B0-commando maakte het gordijn zwart maar renderde geen frame. Normale LAN-status bleef werken. Daarom wordt pixel-LAN niet aangeboden als werkende functie.

## H6069 Mini Panel Lights

- Getest met 40 panelen; paneel-ID's zijn nulgebaseerd.
- Eén wijziging verzendt altijd het complete actuele paneelbeeld.
- De payload groepeert gelijke RGB-kleuren en wordt in 20-byte A3-frames verdeeld.
- Ieder frame bevat een XOR-checksum; het laatste A3-dataframe gebruikt index `0xFF`.
- Daarna volgt het statische activatieframe met prefix `33 05 0A 20 03`.
- De frames worden Base64 opgenomen in een compacte Govee `ptReal` JSON-datagram.

Fysieke referentievector: 39 panelen blauw en protocolpaneel 5 rood. Dit veranderde exact één paneel binnen ongeveer 300 ms. De vijf Base64-frames staan als vaste regressietest in `tests/test_h6069_protocol.py`.

Omdat UDP `sendto` geen apparaatbevestiging geeft, betekent `successful_uploads` uitsluitend dat het besturingssysteem de datagram zonder socketfout heeft verzonden. De UI blijft `assumed_state`.

## H70B3 Curtain Lights 2

- Getest apparaat: H70B3, 20 kolommen × 26 rijen = 520 leds.
- Logische index: `index = y * 20 + x`, met x=0..19 en y=0..25.
- Volledige frames worden als RGB-PNG opgebouwd en via A4/58-pakketten verzonden.
- Iedere GATT-write is beschermd; de RC4-status wordt bewust per write opnieuw gestart.
- Een sessie gebruikt de bewezen E7-handshake, een tijdelijke 16-byte sessiesleutel, device-info/capability-uitwisseling en keepalive.
- Het pakketformaat past zich aan de maximaal toegestane write-without-response-grootte aan, met 20 bytes als minimum.
- Na een bevestigde upload volgt een apart activatiecommando.

Fysiek bewezen patronen:

- rode/blauwe X;
- hoekblokken: linksboven rood, rechtsboven groen, linksonder blauw, rechtsonder wit;
- willekeurige afzonderlijke pixels via de complete geauthenticeerde frame-upload.

Horizontaal en verticaal spiegelen gebeuren vóór encoding. Logische automationcoördinaten blijven daardoor gelijk wanneer het gordijn andersom wordt opgehangen.

Een actieve ESPHome Bluetooth-proxy is volgens het Home Assistant Bluetoothmodel een externe connectable adapter. De uiteindelijke proxyroute moet nog fysiek worden getest met dit GATT-protocol; de directe Bluetoothprotocolproef zelf is al geslaagd.

## Schrijfsnelheid en veiligheid

- Losse entiteitswijzigingen worden gedebounced en tot één compleet frame samengevoegd.
- H6069 gebruikt standaard 200 ms; H70B3 150 ms.
- Voor doorlopende sensorsignalen is 1–3 seconden een verstandige eerste interval. Een H70B3-upload is veel zwaarder dan één LAN-datagram.
- Setup, restore, opties en reload veranderen alleen geheugenstatus en verzenden niets.
- Onbekende bytes, firmware-updates, Govee-scènes en muziekmoduscommando's horen niet in de stabiele adapter totdat ze apart fysiek zijn bewezen.
