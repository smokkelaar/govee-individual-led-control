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
