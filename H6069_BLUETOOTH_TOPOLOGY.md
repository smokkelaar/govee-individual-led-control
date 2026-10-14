# H6069: actuele aansluitstructuur via Bluetooth

Op 13 oktober 2026 is een gewijzigde 40-paneelkaart rechtstreeks via Bluetooth
uitgelezen. De LAN-`status`vraag gaf op dezelfde installatie nog de oude kaart
terug. Een geldige checksum bewijst dus niet dat een LAN-kaart actueel is.

## Bewezen procedure

1. Sluit Govee Home volledig. Het apparaat accepteert één Bluetoothverbinding.
2. Verbind met het **Bluetoothadres** van de H6069, niet het wifi-MAC.
3. Abonneer op `00010203-0405-0607-0809-0a0b0c0d2b10`. Schrijf zonder GATT-antwoord
   naar `00010203-0405-0607-0809-0a0b0c0d2b11`.
4. Onderhandel de versleutelde E7-sessie zoals in de bestaande `h70b3_ble.py`.
   Dezelfde AES/RC4-bescherming werkte op deze H6069. Vraag daarna `AA 60 01` op.
5. Stuur `33 45 00` om de herkenningsmodus te openen; controleer het antwoord.
6. Wacht 300 ms en stuur de uitleesopdracht **`AC 02 00`**.
7. Verzamel de ontsleutelde `AC`-antwoordpakketten tot index `FF`. Houd de sessie
   actief met `AA`-keepalive.
8. Stuur ook bij een leesfout **`33 45 FF`** om de herkenningsmodus te verlaten,
   zolang de verbinding beschikbaar is.

Vul iedere opdracht tot 19 bytes aan met nullen en voeg een XOR-checksum toe.
Bereken de checksum vóór encryptie. Reset de transportversleuteling voor iedere
write/notification, zoals in `h70b3_ble.py`.

Deze procedure is **geen zuiver read-only LAN-probe**: herkenningsmodus kan het
zichtbare patroon tijdelijk veranderen. Zij wordt alleen expliciet uitgevoerd,
nooit bij setup, reload of restore. Na het afsluiten moet fysieke bediening
afzonderlijk worden gecontroleerd; een uitgelezen kaart bewijst geen kleurupload.

## Het antwoord verwerken

Elk antwoordframe heeft 20 bytes: `AC`, pakketindex, 17 databytes, XOR-checksum.
Indices beginnen bij `00`; het laatste frame gebruikt `FF`. Controleer de
checksums en volgorde en voeg alle 17-byte datadelen samen.

De samengestelde data begint met vijf transportbytes. Byte 0 geeft het aantal
frames aan. Bytes 3 en 4 zijn voor deze vraag `02 00`. De betekenis van bytes
1 en 2 is nog niet vastgesteld. Daarna volgen één byte paneelaantal en exact
drie bytes per paneel: type `20`, ingangszijde en bitmasker van uitgangen.
Na het laatste paneel volgt nul-padding.

Het script converteert de gecontroleerde records naar het bestaande Shape
Recognition-importformaat. **Die Base64-envelope is door het script gemaakt;
zij is geen nieuw ontvangen LAN-`status.pt`-antwoord.** De bestaande decoder
controleert vervolgens de checksum, boom, paneelaantal en coördinaten.

De tekening volgt de bestaande decoderoriëntatie: de voedingsingang van paneel
0 wijst omlaag. Vergelijk kaart en nummering met de echte opstelling vóór import.

## Herbruikbaar script

Vanuit de repository, met Python 3.12 of nieuwer en een lokale Bluetoothadapter:

```bash
python -m pip install bleak cryptography
python scripts/h6069_bluetooth_topology.py --address <H6069-BLUETOOTH-MAC> --output work/h6069-topology.json
```

Het script toont rooster, fingerprint en Base64-importwaarde. De optionele JSON
bevat ook de gecontroleerde Bluetoothframes en
`import_envelope_is_synthesized: true`. Bewaar eigen adressen en appcaptures
lokaal; voeg ze niet toe aan commits. De repository negeert de map `work/`.

Na fysieke vergelijking kan de importwaarde in Home Assistant worden opgeslagen
onder **Govee Individual LED Control → H6069 → Configureren → Shape Recognition
topology**. LED Studio leest daarna `number_grid` uit de topologiesensor.

## Bewijs en grenzen

- De versleutelde handshake, herkenningsmodus en uitlezing zijn uitgevoerd op
  een echte H6069 met 40 panelen en gewijzigde aansluitvolgorde.
- `AA B2` en `AA B4` leverden geen kaart op. Dat bewijst geen ontbrekende functie.
- De Home Assistant-knop gebruikt nog LAN. Dit script is een losse diagnostische
  tool; de integratie voert geen automatische Bluetooth-kaartuitlezing uit.
- De anonieme referentieframes in `tests/test_h6069_bluetooth_topology.py`
  bevatten alleen aansluitgegevens. Tests bewijzen parsing, geen radiowerking
  op elke firmware.
- De opdrachtvolgorde is afgeleid uit de op de eigen Android-telefoon
  geïnstalleerde H6069-appmodule en op eigen hardware gecontroleerd. Appbestanden
  en gedecompileerde appcode worden niet in de repository gepubliceerd.

## Apart opgelost: ongeldige kleurupload

Het opnieuw importeren van de kaart loste het foutpatroon bij een kleurupload
niet op. De A3-encoder kondigde steeds zes pakketten aan, ook wanneer het
patroon uit vier of dertien uploadpakketten bestond. De Android-pakketopbouw
berekent dat aantal dynamisch. Na correctie van zes naar vier bij de demo
bevestigde de gebruiker: paneel 05 rood, alle andere panelen blauw.
`h6069_protocol.py` berekent het aantal nu per patroon. Tests controleren
een effen beeld, de tweekleurendemo, veertig verschillende kleuren en een
korte transfer met afzonderlijk start- en sluitframe.
