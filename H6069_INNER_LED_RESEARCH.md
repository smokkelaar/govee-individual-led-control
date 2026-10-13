# H6069: vijf interne ledposities via een effectmasker

## Fysiek bevestigd op 13 oktober 2026

De gebruiker ziet vijf lichtposities per paneel: vier hoeken en een middenpositie.
Een lokaal vastgelegd AI-effect uit Govee Home bevat twee effectlagen. Door in
beide lagen het selectiemasker `00 1F` naar `00 1E` te wijzigen, werd één interne
positie donker in elk van de 40 panelen. Het oorspronkelijke effect werd na deze
proef automatisch hersteld.

Daarna werden achtereenvolgens de maskers `001E`, `001C`, `0018`, `0010` en
`0000` toegepast, met ongeveer drie seconden tussen de stappen. De gebruiker
bevestigde vijf zichtbare stappen en uiteindelijk alle panelen donker. Het
apparaat bevestigde de uploads en activaties zonder het foutpatroon.

Dit bewijst selectie van vijf interne posities, waarbij dezelfde selectie tegelijk
voor alle panelen geldt. Onafhankelijke RGB-adressering van alle 200 interne
posities is nog niet bewezen. Bij single-bitproeven op 14 oktober bevestigde de gebruiker:

| Masker | Fysieke positie |
| --- | --- |
| `0001` | linksboven |
| `0002` | rechtsboven |
| `0004` | rechtsonder |
| `0008` | linksonder |
| `0010` | midden |

Alle vijf single-bitproeven zijn door de gebruiker bevestigd.
De mapping is waargenomen op deze installatie; afwijkende paneeloriëntatie
kan nader onderzoek vragen.

## Twee verschillende uploadroutes

- De stabiele A3-upload met commando `03` groepeert volledige paneel-ID's per RGB-kleur.
- De onderzochte A3-upload met commando `58` bevat een gelaagd AI-effectprogramma.
- De topologie bevat paneelverbindingen; daaruit volgt geen interne ledindeling.

De bestaande Home Assistant-bediening blijft gebaseerd op volledige panelen.
De effectmaskerproef is onderzoek en nog geen geïntegreerde subledfunctie.

## Structuur van het onderzochte effect

De vastgelegde upload bestaat uit vijf A3-frames plus een afzonderlijk
activatiecommando. Na het samenvoegen begint de effectpayload met `58 01 02`;
het laatste byte geeft hier twee lagen aan. De eerste payloadbijdrage is
framebytes `[5:19]`; de vervolgframes dragen bytes `[2:19]` bij.

De lagen hebben een subtype, een effectcode en een little-endian bodylengte:

| Laag | Subtype | Effectcode | Bodylengte | Selectiemasker |
| --- | --- | --- | --- | --- |
| 1 | 1 | `5A` | 33 | eerste twee bodybytes `00 1F` |
| 2 | 0 | `5F` | 28 | eerste twee bodybytes `00 1F` |

Alle overige effectbytes bleven tijdens de proeven gelijk. Na wijziging zijn de
XOR-checksums opnieuw berekend en zijn de frames via de bestaande geauthenticeerde
E7/AES/RC4-Bluetoothverbinding verstuurd. De vastgelegde activatie begint met
`33 05 0A 7C 00`; deze waarde is niet als universele activatie voor andere effecten
bewezen. De overige kleur- en bewegingsvelden zijn nog niet volledig gedecodeerd.

## Vervolg

1. Controleer de bovenstaande mapping bij anders georiënteerde panelen.
2. Controleer dezelfde maskers met een tweede vastgelegd effectprogramma.
3. Zoek aantoonbare selectie van één paneel binnen deze effectroute.
4. Bewijs onafhankelijke kleurkeuze per interne positie voordat vrije RGB-bediening wordt toegevoegd.

Geen nieuwe effectwrites worden automatisch toegevoegd aan setup of reload.
Volledige Android-foutrapporten, Bluetoothlogs, app-extracties, apparaatadressen en
sessiesleutels blijven buiten deze repository. De bovenstaande resultaten zijn
gebaseerd op de eigen fysieke proef en bevestiging door de gebruiker.

## Achtergrond

- [Govee H6069-productpagina](https://us.govee.com/products/govee-mini-panel-lights)
- [Android-documentatie over Bluetooth HCI-opnamen](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging)

## Paneelselectie onderzocht op 14 oktober 2026

Met masker `0001` in beide effectlagen is uitsluitend de bodyvlag
`singleControl` (offset 2) gewijzigd van 0 naar 1. Upload en activatie kregen
geldige bevestigingen. Na een eerste onzekere waarneming is dezelfde proef
45 seconden herhaald. De gebruiker bevestigde dat het licht tussen panelen
verspringt. Deze proef bewijst geen vast selecteerbaar paneel-ID. Na elke proef
is het opgeslagen AI-effect hersteld.

De onderzochte effectbody bevat volgens lokale inspectie van de eigen app:

| Bodyoffset | Veld | Bewijs |
| --- | --- | --- |
| 0..1 | interne positieselectie | vijf bits fysiek bevestigd |
| 2 | `singleControl` | wijziging fysiek getest; beweging tussen panelen |
| 3 | effectrichting | appcode; geen paneel-ID aangetoond |
| 4 | effectvorm | appcode |
| 5..8 | twee 2-bytecoördinaten | appcode; gebruikt voor animatiefocus |
| 9 | actietype | appcode: beweging, flitsen of uitbreiding |
| 10..11 | lengte van de actiegegevens | appcode en vastgelegde lagen |
| 12.. | actiegegevens, waaronder kleurpalet | appcode en vastgelegde lagen |

De coördinaten worden door een focusdialoog ingevuld. Ze mogen niet zonder
verdere proef als paneeladres worden geïnterpreteerd. De onderzochte laag bevat
geen expliciete lijst van 40 paneel-ID's. De tekenmodus gebruikt de al bekende
A3-route met commando `03`, met kleur-groepen en indices van volledige panelen.
De gebruiker bevestigt dat hij in die appfunctie alleen hele panelen kan kiezen.
Dit sluit andere firmwaremogelijkheden niet uit, maar levert geen referentie
voor een vaste interne positie op één afzonderlijk paneel.

## Looplicht en focuscoördinaten fysiek bevestigd

Een nieuwe Android-opname bevat het door de gebruiker toegepaste looplicht.
Het actuele Bluetoothlog bevatte geen H6069-verbinding; de doelupload stond in
het geroteerde vorige log uit hetzelfde rapport. Alleen de doelwrites zijn
gefilterd. De volledige rapporten en logs blijven lokaal.

Dit effect gebruikt drie A3-uploadframes met commando `58` en één laag. De laag
heeft mask `001F`, `singleControl=0`, richting 11, vorm 1, actietype 0 en een
focuspunt met bytes `40 06 28 06`. De waarden zijn little-endian X=1600 en Y=1576.
De vastgelegde activatie begint met `33 05 04 F0 46`; bij uitlezen was dezelfde
scène actief. Het vastgelegde palet bevat rood, groen en blauw.

In een gecontroleerde proef zijn uitsluitend de vier focusbytes veranderd naar
X=1700, Y=1576. Pakketlengtes, uploadtelling, checksums en onveranderde activatie
zijn vooraf gevalideerd. De gebruiker bevestigde dat het draaipunt zichtbaar
verschuift. Na 25 seconden is het vastgelegde looplicht hersteld; upload en
activatie werden bevestigd.

Hiermee is ruimtelijke besturing van de effectoorsprong bewezen. Een focuspunt
is nog geen vast adres voor één interne led. Er is nog geen bewezen koppeling
van deze coördinaten aan alle individuele paneelcentra, geen geselecteerd vast
paneel-ID in de effectlaag en geen vrije RGB-framebuffer van 200 posities.

## Coördinaten per paneel en begrenzingsproef

De appgeometrie voor vierkante panelen gebruikt een zijde/paneelafstand van 24.
De bezette paneelkaart wordt rond (1600,1600) gecentreerd. Uit de bevestigde kaart
kunnen daarom focuspunten per paneel worden berekend. Met twee ver uit elkaar
liggende fysieke proeven bevestigde de gebruiker:

- paneel 05: X=1660, Y=1660;
- paneel 35: X=1516, Y=1516.

De overige punten zijn berekend, niet elk afzonderlijk fysiek getest. Het nieuwe
read-only script `scripts/h6069_effect_coordinates.py` neemt JSON met
`number_grid`, negeert lege buitenranden en berekent dezelfde geometrie. Het
verstuurt geen lampcommando's en kent geen RGB-adressen toe.

```powershell
python scripts/h6069_effect_coordinates.py topology.json --output effect-points.json
```

De parameter Color Block Size uit de bewegingactie is ook onderzocht. De app
laat 0..50 toe. Met focus op paneel 05 is uitsluitend de bestaande blokbreedte 1
naar 0 gewijzigd naast het al geverifieerde focuspunt. De gebruiker zag nog
steeds licht op meerdere panelen. Dit veld is dus bij deze proef geen begrenzing
tot één paneel. Alle proeven kregen geldige upload-/activatiebevestigingen en
herstelden het vastgelegde looplicht automatisch.

Vier nieuwe geometriechecks toetsen beide fysieke referentiepunten, lege
buitenranden, paneelafstand/origin en ongeldige of dubbele IDs. De volledige
lokale suite telt nu 43 geslaagde tests. Een vaste interne RGB-positie op één
paneel blijft nog onbewezen; de coördinaten zijn effectfocuspunten.
