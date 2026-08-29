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

### Vormherkenning uitlezen

Een eerder vastgelegde Shape Recognition-`pt` van de geteste installatie
decodeert naar 129 bytes:

- header `BB 00 7C B2 00`, gevolgd door paneelaantal 40;
- twee verdere headerbytes;
- exact 40 records van drie bytes: `20`, lokale ingangszijde en bitmasker van
  aangesloten kindzijden;
- één XOR-checksumbyte; XOR over de complete blob is nul.

De records vormen een depth-first preorder-boom. Lokale zijden lopen met de klok
mee als `01, 02, 04, 08`; de ingangszijde bepaalt de rotatie van ieder volgend
paneel. Met de voedingsingang van paneel 0 naar beneden levert dit 40 unieke
coördinaten zonder overlap en exact dezelfde vorm als Shape Recognition in de
Govee-app. De decoder weigert onbekende headers, verkeerde lengte, ongeldige
zijden, een fout aantal boomverbindingen, coördinaatoverlap en checksumfouten.

Een lege read-only LAN-`status`vraag is opnieuw fysiek getest. H6069 antwoordt
via multicast `239.255.255.250:4002`, waardoor een luistersocket zowel poort 4002
moet delen als de multicastgroep moet joinen. De actuele firmware retourneert
daarbij normaal een `pt` van slechts 6 bytes met runtime-status; ook met het
Shape Recognition-scherm in de Govee-app open kwam de 129-byte kaart niet terug.
De app gebruikt dus een elders opgeslagen kopie en een lege statusvraag is geen
betrouwbare kaartbron.

Home Assistant kan daarom een eerder vastgelegde Base64-kaart via de gewone
optiesdialoog importeren. Header, lengte, checksum, boom, coördinaten en
paneelaantal worden vóór opslag gecontroleerd. **Paneelindeling via LAN proberen** blijft
een expliciete experimentele alleen-lezen proef voor firmware die de lange vorm
wel retourneert. Setup, reload en restore doen geen netwerkquery of lichtschrijfopdracht.

Fysieke referentievector: 39 panelen blauw en protocolpaneel 5 rood. Dit veranderde exact één paneel binnen ongeveer 300 ms. De vijf Base64-frames staan als vaste regressietest in `tests/test_h6069_protocol.py`.

Omdat UDP `sendto` geen apparaatbevestiging geeft, betekent `successful_uploads` uitsluitend dat het besturingssysteem de datagram zonder socketfout heeft verzonden. De UI blijft `assumed_state`.

De bewezen A3-static-payload adresseert één RGB-kleur per fysiek paneel. Mogelijke
afzonderlijke leds binnen een paneel vallen nog buiten de bewezen protocolgrens;
zie `H6069_INNER_LED_RESEARCH.md`.

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
