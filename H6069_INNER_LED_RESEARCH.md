# H6069: mogelijke afzonderlijke leds binnen één paneel

## Aanleiding

Tijdens een fouttoestand was in de fysieke H6069-panelen een blauw/groene waas
zichtbaar waarbij meerdere lichtpunten of zones binnen één cube afzonderlijk
leken te reageren. Dat is relevante hardware-indicatie, maar nog geen bewijs dat
Home Assistant, LAN of Bluetooth die emitters rechtstreeks kan adresseren.

## Wat nu wel bewezen is

- De statische LAN- en Bluetoothuploads uit de eigen captures gebruiken dezelfde
  A3-groepering: per groep één RGB-kleur plus een lijst met paneel-ID's 0..39.
- De fysiek bewezen test met paneel 5 rood en de overige panelen blauw veranderde
  precies één volledig paneel.
- De uitgelezen `status.pt`-vorm bevat exact één verbindingsrecord per fysiek
  paneel. Er staat geen intern 3×3-rooster of subled-ID in deze vormdata.
- Govee noemt H6069 officieel RGBIC, scenes en pixel-art per lichtpaneel. Dat
  bevestigt interne effecthardware, maar documenteert geen openbare subpaneel-API.

Daarom blijft het stabiele element voorlopig **één fysiek paneel**. De foutwaas
kan bijvoorbeeld door een lokale paneel-MCU of een vaste diagnostische animatie
worden gemaakt; externe aanstuurbaarheid volgt daar niet automatisch uit.

## Veilig vervolgonderzoek

1. Maak een HCI-capture terwijl Govee Home een zelfgemaakt, stilstaand beeld
   toepast dat aantoonbaar binnen één paneel verschillende kleuren toont. Een
   ingebouwde scene-ID alleen is onvoldoende bewijs.
2. Trek bij aangesloten Android-telefoon de dynamische H6069-appmodule uit en
   zoek naar resolutieconstanten, framebouwers en commando's naast de bekende
   A3-paneelgroepering.
3. Vergelijk twee captures die op exact één interne positie verschillen. Alleen
   het veranderende byteveld wordt kandidaat-adresdata.
4. Voeg pas na decodeerbare checksums en herhaalbare writes een experimentele
   encoder toe. Begin met één paneel, lage helderheid en een bekend volledig
   paneelframe als herstelactie.
5. Promoveer dit pas naar normale HA-entiteiten wanneer minstens twee interne
   posities onafhankelijk en herhaalbaar reageren zonder de vormconfiguratie of
   firmwaremodus te beschadigen.

## Nog nodig van de fysieke installatie

De volgende bruikbare meetkans is ofwel de exacte blauw/groene fouttoestand, ofwel
een Govee-appfunctie waarmee binnen één paneel bewust een vast tweekleurenbeeld
kan worden gemaakt. Tot die tijd worden geen willekeurige onbekende bytes onderdeel
van de stabiele integratie.

## Bronnen

- [Govee H6069-productpagina](https://us.govee.com/products/govee-mini-panel-lights)
  — officiële RGBIC-, scene-, Shape Recognition- en paneelclaims.
- [Officiële ondersteunde Govee API-modellen](https://developer.govee.com/docs/support-product-model)
  — H6069 staat in de ondersteunde modellijst, zonder publieke subpaneelindeling.
- `tests/test_h6069_protocol.py` en `tests/test_h6069_topology.py` — vaste,
  geschoonde referentievectoren uit de eigen fysieke installatie.
