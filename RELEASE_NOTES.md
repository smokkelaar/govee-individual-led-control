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
