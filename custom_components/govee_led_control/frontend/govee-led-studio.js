const CARD_VERSION = "0.4.1";
const H70_WIDTH = 20;
const H70_HEIGHT = 26;
const H70_PIXELS = H70_WIDTH * H70_HEIGHT;
const DEFAULT_H6069_PANELS = 40;
const BLACK = "#000000";

const PALETTE = [
  "#ff1744", "#ff6d00", "#ffd600", "#76ff03", "#00e676",
  "#00e5ff", "#2979ff", "#651fff", "#d500f9", "#ff4081",
  "#ffffff", "#000000",
];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hsvToHex(h, s = 1, v = 1) {
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  const rgb = [
    [v, t, p], [q, v, p], [p, v, t],
    [p, q, v], [t, p, v], [v, p, q],
  ][i % 6];
  return `#${rgb.map((channel) => Math.round(channel * 255).toString(16).padStart(2, "0")).join("")}`;
}

function rgbToHex(r, g, b) {
  return `#${[r, g, b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

class GoveeLedStudio extends HTMLElement {
  static getStubConfig() {
    return {
      h6069_transport_entity: "sensor.h6069_transport",
      h6069_topology_entity: "sensor.h6069_paneelindeling",
      h70b3_transport_entity: "sensor.h70b3_transport",
      h6069_panel_count: 40,
    };
  }

  setConfig(config) {
    this.config = { ...GoveeLedStudio.getStubConfig(), ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._selectedColor ||= "#ff1744";
    this._brightness ||= 70;
    this._speed ||= 1;
    this._fit ||= "contain";
    this._tab ||= "curtain";
    this._h6069 ||= Array(this.config.h6069_panel_count || DEFAULT_H6069_PANELS).fill(BLACK);
    this._h70 ||= Array(H70_PIXELS).fill(BLACK);
    this._gifFrames ||= [];
    this._render();
  }

  set hass(value) {
    this._hass = value;
    if (this.shadowRoot && !this._rendered) this._render();
    const topology = value?.states?.[this.config?.h6069_topology_entity]?.attributes?.number_grid;
    const signature = JSON.stringify(topology || null);
    if (this._rendered && signature !== this._topologySignature) {
      this._topologySignature = signature;
      this._paintH6069();
    }
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return {
      columns: "full",
      min_columns: 6,
    };
  }

  _render() {
    if (!this.shadowRoot || !this.config) return;
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card>
        <header>
          <div>
            <div class="eyebrow">GOVEE CONTROL</div>
            <h1>LED Studio</h1>
            <p>Schilder, kies een patroon of speel een GIF af.</p>
          </div>
          <div class="status" id="status"><span></span>Klaar</div>
        </header>

        <nav>
          <button data-tab="curtain" class="active">H70B3 gordijn</button>
          <button data-tab="panels">H6069 panelen</button>
        </nav>

        <section class="toolbar">
          <label class="color-control">Kleur <input id="color" type="color" value="${this._selectedColor}"></label>
          <div class="palette">${PALETTE.map((color) => `<button class="swatch" data-color="${color}" style="--swatch:${color}" title="${color}"></button>`).join("")}</div>
          <label class="range-control">Helderheid <strong id="brightness-value">${this._brightness}%</strong>
            <input id="brightness" type="range" min="1" max="100" value="${this._brightness}">
          </label>
        </section>

        <main id="curtain" class="view active">
          <div class="stage">
            <div class="matrix-shell"><div id="h70-grid" class="matrix"></div></div>
            <div class="side-panel">
              <h2>Patronen</h2>
              <div class="button-grid">
                <button data-h70-preset="solid">Effen</button>
                <button data-h70-preset="rainbow">Regenboog</button>
                <button data-h70-preset="gradient">Verloop</button>
                <button data-h70-preset="sparkle">Sterren</button>
              </div>
              <button class="primary" id="h70-apply">Naar gordijn sturen</button>
              <button class="danger" id="h70-clear">Alles uit</button>
            </div>
          </div>

          <div class="gif-panel">
            <div>
              <div class="eyebrow">ANIMATIE</div>
              <h2>GIF naar 20 × 26 leds</h2>
              <p>De GIF wordt lokaal in je browser verkleind. Het bestand wordt nergens opgeslagen.</p>
            </div>
            <label class="upload" id="drop-zone">
              <input id="gif-file" type="file" accept="image/gif">
              <span class="upload-icon">＋</span>
              <strong>Kies een GIF</strong>
              <small>maximaal 10 MB · maximaal 120 frames</small>
            </label>
            <div class="gif-controls">
              <label>Passend maken
                <select id="fit"><option value="contain">Hele afbeelding</option><option value="cover">Beeldvullend</option><option value="stretch">Uitrekken</option></select>
              </label>
              <label>Snelheid <strong id="speed-value">${this._speed.toFixed(1)}×</strong>
                <input id="speed" type="range" min="0.25" max="2" step="0.25" value="${this._speed}">
              </label>
              <button class="primary" id="gif-play" disabled>▶ Afspelen</button>
              <button id="gif-stop" disabled>■ Stoppen</button>
            </div>
            <div id="gif-info" class="gif-info">Nog geen GIF geladen.</div>
          </div>
        </main>

        <main id="panels" class="view">
          <div class="stage">
            <div>
              <div class="panel-grid" id="h6069-grid"></div>
              <p class="hint">Klik op een paneel om de gekozen kleur toe te passen.</p>
            </div>
            <div class="side-panel">
              <h2>Panelen</h2>
              <div class="button-grid">
                <button data-panel-preset="solid">Alles dezelfde kleur</button>
                <button data-panel-preset="rainbow">Regenboog</button>
                <button data-panel-preset="checker">Om en om</button>
                <button data-panel-preset="gradient">Verloop</button>
              </div>
              <button class="primary" id="h6069-apply">Naar panelen sturen</button>
              <button class="danger" id="h6069-clear">Alles uit</button>
            </div>
          </div>
        </main>
      </ha-card>`;
    this._rendered = true;
    this._bindEvents();
    this._paintH70();
    this._paintH6069();
  }

  _bindEvents() {
    const root = this.shadowRoot;
    root.querySelectorAll("nav button").forEach((button) => button.addEventListener("click", () => this._showTab(button.dataset.tab)));
    root.querySelector("#color").addEventListener("input", (event) => { this._selectedColor = event.target.value; });
    root.querySelectorAll(".swatch").forEach((button) => button.addEventListener("click", () => {
      this._selectedColor = button.dataset.color;
      root.querySelector("#color").value = this._selectedColor;
    }));
    root.querySelector("#brightness").addEventListener("input", (event) => {
      this._brightness = Number(event.target.value);
      root.querySelector("#brightness-value").textContent = `${this._brightness}%`;
    });
    root.querySelector("#speed").addEventListener("input", (event) => {
      this._speed = Number(event.target.value);
      root.querySelector("#speed-value").textContent = `${this._speed.toFixed(1)}×`;
    });
    root.querySelector("#fit").addEventListener("change", async (event) => {
      this._fit = event.target.value;
      if (this._gifFile) await this._loadGif(this._gifFile);
    });

    root.querySelectorAll("[data-h70-preset]").forEach((button) => button.addEventListener("click", () => this._presetH70(button.dataset.h70Preset)));
    root.querySelectorAll("[data-panel-preset]").forEach((button) => button.addEventListener("click", () => this._presetH6069(button.dataset.panelPreset)));
    root.querySelector("#h70-apply").addEventListener("click", () => this._sendFrame(this._h70));
    root.querySelector("#h70-clear").addEventListener("click", () => this._clear("h70"));
    root.querySelector("#h6069-apply").addEventListener("click", () => this._sendPanels());
    root.querySelector("#h6069-clear").addEventListener("click", () => this._clear("h6069"));
    root.querySelector("#gif-file").addEventListener("change", (event) => this._loadGif(event.target.files?.[0]));
    root.querySelector("#gif-play").addEventListener("click", () => this._playGif());
    root.querySelector("#gif-stop").addEventListener("click", () => this._stopGif());
  }

  _showTab(tab) {
    this._tab = tab;
    this.shadowRoot.querySelectorAll("nav button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    this.shadowRoot.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === tab));
  }

  _paintH70() {
    const grid = this.shadowRoot.querySelector("#h70-grid");
    grid.innerHTML = this._h70.map((color, index) => `<button data-index="${index}" style="--pixel:${color}" title="${index % H70_WIDTH}, ${Math.floor(index / H70_WIDTH)}"></button>`).join("");
    grid.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
      this._h70[Number(button.dataset.index)] = this._selectedColor;
      button.style.setProperty("--pixel", this._selectedColor);
    }));
  }

  _paintH6069() {
    const grid = this.shadowRoot.querySelector("#h6069-grid");
    const topology = this._hass?.states?.[this.config.h6069_topology_entity]?.attributes?.number_grid;
    if (Array.isArray(topology) && topology.length && topology.every((row) => Array.isArray(row))) {
      const width = Math.max(...topology.map((row) => row.length));
      grid.style.gridTemplateColumns = `repeat(${width}, 1fr)`;
      grid.innerHTML = topology.flatMap((row) => Array.from({ length: width }, (_, column) => {
        const index = row[column];
        if (index === null || index === undefined) return '<span class="panel-blank"></span>';
        const color = this._h6069[index] || BLACK;
        return `<button data-index="${index}" style="--panel:${color}"><span>${String(index).padStart(2, "0")}</span></button>`;
      })).join("");
    } else {
      grid.style.gridTemplateColumns = "repeat(8, 1fr)";
      grid.innerHTML = this._h6069.map((color, index) => `<button data-index="${index}" style="--panel:${color}"><span>${String(index).padStart(2, "0")}</span></button>`).join("");
    }
    grid.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
      this._h6069[Number(button.dataset.index)] = this._selectedColor;
      button.style.setProperty("--panel", this._selectedColor);
    }));
  }

  _presetH70(name) {
    if (name === "solid") this._h70.fill(this._selectedColor);
    if (name === "rainbow") this._h70 = this._h70.map((_, index) => hsvToHex((index % H70_WIDTH) / H70_WIDTH));
    if (name === "gradient") this._h70 = this._h70.map((_, index) => hsvToHex((index % H70_WIDTH) / H70_WIDTH, 1, 0.25 + 0.75 * (Math.floor(index / H70_WIDTH) / (H70_HEIGHT - 1))));
    if (name === "sparkle") this._h70 = this._h70.map(() => Math.random() > 0.84 ? this._selectedColor : BLACK);
    this._paintH70();
  }

  _presetH6069(name) {
    if (name === "solid") this._h6069.fill(this._selectedColor);
    if (name === "rainbow") this._h6069 = this._h6069.map((_, index) => hsvToHex(index / this._h6069.length));
    if (name === "checker") this._h6069 = this._h6069.map((_, index) => index % 2 ? BLACK : this._selectedColor);
    if (name === "gradient") this._h6069 = this._h6069.map((_, index) => hsvToHex(index / this._h6069.length, 1, 0.35 + 0.65 * index / this._h6069.length));
    this._paintH6069();
  }

  _entryId(entityId) {
    const entity = this._hass?.states?.[entityId];
    return entity?.attributes?.config_entry_id || null;
  }

  async _sendFrame(colors, quiet = false) {
    const entryId = this._entryId(this.config.h70b3_transport_entity);
    if (!entryId) return this._setStatus(`Geen config_entry_id gevonden op ${this.config.h70b3_transport_entity}`, true);
    try {
      await this._hass.callService("govee_led_control", "set_frame", {
        config_entry_id: entryId,
        colors,
        brightness_percent: this._brightness,
        commit: true,
      });
      if (!quiet) this._setStatus("Frame verzonden");
      return true;
    } catch (error) {
      this._setStatus(error?.message || "Verzenden mislukt", true);
      this._stopGif();
      return false;
    }
  }

  async _sendPanels() {
    const entryId = this._entryId(this.config.h6069_transport_entity);
    if (!entryId) return this._setStatus(`Geen config_entry_id gevonden op ${this.config.h6069_transport_entity}`, true);
    const elements = this._h6069.map((color, index) => ({ index, color }));
    try {
      await this._hass.callService("govee_led_control", "set_elements", {
        config_entry_id: entryId,
        elements,
        replace: true,
        brightness_percent: this._brightness,
        commit: true,
      });
      this._setStatus("Panelen verzonden");
    } catch (error) {
      this._setStatus(error?.message || "Verzenden mislukt", true);
    }
  }

  async _clear(target) {
    this._stopGif();
    const isH70 = target === "h70";
    const entityId = isH70 ? this.config.h70b3_transport_entity : this.config.h6069_transport_entity;
    const entryId = this._entryId(entityId);
    if (!entryId) return this._setStatus(`Geen config_entry_id gevonden op ${entityId}`, true);
    try {
      await this._hass.callService("govee_led_control", "clear", { config_entry_id: entryId, commit: true });
      if (isH70) { this._h70.fill(BLACK); this._paintH70(); }
      else { this._h6069.fill(BLACK); this._paintH6069(); }
      this._setStatus("Leds uitgeschakeld");
    } catch (error) {
      this._setStatus(error?.message || "Wissen mislukt", true);
    }
  }

  async _loadGif(file) {
    if (!file) return;
    this._gifFile = file;
    this._stopGif();
    if (file.size > 10 * 1024 * 1024) return this._setStatus("GIF is groter dan 10 MB", true);
    if (!("ImageDecoder" in window)) return this._setStatus("Deze browser ondersteunt geen GIF-decoder. Gebruik Chrome, Edge of de Home Assistant-app.", true);
    const info = this.shadowRoot.querySelector("#gif-info");
    info.textContent = "GIF wordt omgezet…";
    this._setStatus("GIF verwerken…");
    try {
      const data = await file.arrayBuffer();
      const decoder = new ImageDecoder({ data, type: file.type || "image/gif" });
      await decoder.tracks.ready;
      const count = Math.min(decoder.tracks.selectedTrack.frameCount, 120);
      const frames = [];
      for (let index = 0; index < count; index += 1) {
        const result = await decoder.decode({ frameIndex: index, completeFramesOnly: true });
        const frame = result.image;
        frames.push({ colors: this._frameToColors(frame), duration: clamp((frame.duration || 100000) / 1000, 100, 2000) });
        frame.close();
        if (index % 10 === 0) info.textContent = `GIF wordt omgezet… ${index + 1}/${count}`;
      }
      decoder.close();
      this._gifFrames = frames;
      this._h70 = [...frames[0].colors];
      this._paintH70();
      info.textContent = `${file.name} · ${frames.length} frames · klaar om af te spelen`;
      this.shadowRoot.querySelector("#gif-play").disabled = false;
      this.shadowRoot.querySelector("#gif-stop").disabled = false;
      this._setStatus("GIF gereed");
    } catch (error) {
      info.textContent = "Deze GIF kon niet worden gelezen.";
      this._setStatus(error?.message || "GIF verwerken mislukt", true);
    }
  }

  _frameToColors(frame) {
    const canvas = document.createElement("canvas");
    canvas.width = H70_WIDTH;
    canvas.height = H70_HEIGHT;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.fillStyle = BLACK;
    context.fillRect(0, 0, H70_WIDTH, H70_HEIGHT);
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    const sourceWidth = frame.displayWidth;
    const sourceHeight = frame.displayHeight;
    if (this._fit === "stretch") {
      context.drawImage(frame, 0, 0, H70_WIDTH, H70_HEIGHT);
    } else {
      const scale = this._fit === "cover"
        ? Math.max(H70_WIDTH / sourceWidth, H70_HEIGHT / sourceHeight)
        : Math.min(H70_WIDTH / sourceWidth, H70_HEIGHT / sourceHeight);
      const width = sourceWidth * scale;
      const height = sourceHeight * scale;
      context.drawImage(frame, (H70_WIDTH - width) / 2, (H70_HEIGHT - height) / 2, width, height);
    }
    const pixels = context.getImageData(0, 0, H70_WIDTH, H70_HEIGHT).data;
    const colors = [];
    for (let index = 0; index < pixels.length; index += 4) {
      const alpha = pixels[index + 3] / 255;
      colors.push(rgbToHex(Math.round(pixels[index] * alpha), Math.round(pixels[index + 1] * alpha), Math.round(pixels[index + 2] * alpha)));
    }
    return colors;
  }

  async _playGif() {
    if (!this._gifFrames.length) return;
    this._stopGif();
    const generation = ++this._playGeneration;
    this._playing = true;
    this.shadowRoot.querySelector("#gif-play").textContent = "⏸ Herstart";
    this._setStatus("GIF speelt af");
    let index = 0;
    while (this._playing && generation === this._playGeneration) {
      const frame = this._gifFrames[index];
      this._h70 = [...frame.colors];
      this._paintH70();
      if (!await this._sendFrame(frame.colors, true)) break;
      await new Promise((resolve) => setTimeout(resolve, clamp(frame.duration / this._speed, 100, 2000)));
      index = (index + 1) % this._gifFrames.length;
    }
  }

  _stopGif() {
    this._playing = false;
    this._playGeneration = (this._playGeneration || 0) + 1;
    const button = this.shadowRoot?.querySelector("#gif-play");
    if (button) button.textContent = "▶ Afspelen";
  }

  _setStatus(message, error = false) {
    const status = this.shadowRoot.querySelector("#status");
    status.classList.toggle("error", error);
    status.lastChild.textContent = message;
  }

  _styles() {
    return `
      :host { --accent:#7857ff; --accent2:#21d4fd; display:block; min-width:0; }
      ha-card { container-type:inline-size; width:100%; min-width:0; box-sizing:border-box; overflow:hidden; padding:0; background:linear-gradient(145deg, rgba(20,22,31,.98), rgba(9,10,16,.98)); color:#f7f7fb; border:1px solid rgba(255,255,255,.09); }
      header { padding:24px 26px 18px; display:flex; justify-content:space-between; gap:20px; align-items:flex-start; background:radial-gradient(circle at 82% -20%, rgba(120,87,255,.3), transparent 45%); }
      h1,h2,p { margin:0; } h1 { font-size:30px; letter-spacing:-.04em; } h2 { font-size:18px; margin-bottom:10px; } p { color:#a9adbd; margin-top:5px; }
      .eyebrow { color:#8e7aff; font-size:11px; font-weight:800; letter-spacing:.16em; margin-bottom:5px; }
      .status { display:flex; gap:8px; align-items:center; color:#c7cad6; font-size:12px; padding:8px 12px; background:rgba(255,255,255,.06); border-radius:999px; max-width:45%; }
      .status span { width:8px; height:8px; border-radius:50%; background:#33df95; box-shadow:0 0 12px #33df95; flex:none; } .status.error span { background:#ff5364; box-shadow:0 0 12px #ff5364; }
      nav { display:flex; gap:6px; padding:0 26px; border-bottom:1px solid rgba(255,255,255,.08); }
      button,select,input { font:inherit; } button { min-width:0; border:0; cursor:pointer; color:#e8e9ef; background:rgba(255,255,255,.07); border-radius:10px; padding:10px 13px; transition:.15s ease; overflow-wrap:anywhere; } button:hover { background:rgba(255,255,255,.13); transform:translateY(-1px); } button:disabled { opacity:.38; cursor:not-allowed; transform:none; }
      nav button { border-radius:0; background:transparent; border-bottom:2px solid transparent; color:#9297a8; } nav button.active { color:white; border-color:var(--accent); }
      .toolbar { display:grid; grid-template-columns:auto 1fr minmax(180px,280px); gap:18px; align-items:center; padding:18px 26px; background:rgba(255,255,255,.025); }
      label { color:#aeb2c0; font-size:12px; } .color-control { display:flex; align-items:center; gap:9px; } input[type=color] { width:42px; height:34px; padding:0; border:0; background:none; }
      .palette { display:flex; flex-wrap:wrap; gap:7px; } .swatch { width:25px; height:25px; border-radius:50%; padding:0; background:var(--swatch); border:2px solid rgba(255,255,255,.22); }
      .range-control { display:grid; grid-template-columns:1fr auto; gap:5px 10px; } .range-control input { grid-column:1/-1; accent-color:var(--accent); }
      .view { display:none; padding:24px 26px 28px; } .view.active { display:block; }
      .stage { display:grid; grid-template-columns:minmax(280px,1fr) minmax(190px,260px); gap:24px; align-items:start; } .stage > *,.gif-panel > * { min-width:0; }
      .matrix-shell { width:min(100%,420px); box-sizing:border-box; margin:auto; padding:12px; border-radius:15px; background:#030408; box-shadow:inset 0 0 30px rgba(0,0,0,.8), 0 20px 50px rgba(0,0,0,.22); }
      .matrix { display:grid; grid-template-columns:repeat(20,1fr); gap:3px; aspect-ratio:20/26; } .matrix button { min-width:0; padding:0; border-radius:3px; background:var(--pixel); box-shadow:0 0 5px color-mix(in srgb, var(--pixel) 70%, transparent); }
      .side-panel,.gif-panel { padding:18px; border:1px solid rgba(255,255,255,.08); border-radius:15px; background:rgba(255,255,255,.035); }
      .button-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; margin-bottom:15px; } .primary { width:100%; background:linear-gradient(135deg,var(--accent),#5b8cff); font-weight:700; margin-top:7px; } .danger { width:100%; color:#ff8994; margin-top:8px; }
      .gif-panel { margin-top:24px; display:grid; grid-template-columns:1fr minmax(180px,260px); gap:18px 24px; align-items:center; }
      .upload { min-height:115px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; border:1px dashed rgba(255,255,255,.25); border-radius:12px; cursor:pointer; background:rgba(120,87,255,.06); } .upload:hover { border-color:var(--accent); } .upload input { display:none; } .upload-icon { font-size:30px; color:#9b86ff; } .upload small { color:#767c8f; }
      .gif-controls { grid-column:1/-1; display:grid; grid-template-columns:1fr 1fr auto auto; gap:12px; align-items:end; } .gif-controls label { display:grid; gap:7px; } select { color:#e8e9ef; background:#222532; border:0; border-radius:8px; padding:9px; } .gif-controls .primary { margin:0; width:auto; } .gif-info { grid-column:1/-1; color:#9297a8; font-size:12px; }
      .panel-grid { display:grid; grid-template-columns:repeat(8,1fr); gap:8px; } .panel-grid button { aspect-ratio:1; min-width:0; padding:0; background:var(--panel); border:1px solid rgba(255,255,255,.18); color:white; text-shadow:0 1px 4px black; } .panel-grid span { font-size:11px; font-weight:800; } .panel-grid .panel-blank { display:block; aspect-ratio:1; } .hint { font-size:12px; text-align:center; }
      @container(max-width:720px) { header { padding:20px; } .toolbar { grid-template-columns:1fr; padding:16px 20px; } .stage,.gif-panel { grid-template-columns:1fr; } .view { padding:20px; } .gif-controls { grid-template-columns:1fr 1fr; } .panel-grid { grid-template-columns:repeat(5,1fr); } .status { display:none; } }
      @container(max-width:440px) { .gif-controls,.button-grid { grid-template-columns:1fr; } nav { padding:0 16px; } nav button { padding-inline:8px; } }
      @media(max-width:700px) { header { padding:20px; } .toolbar { grid-template-columns:1fr; padding:16px 20px; } .stage,.gif-panel { grid-template-columns:1fr; } .view { padding:20px; } .gif-controls { grid-template-columns:1fr 1fr; } .panel-grid { grid-template-columns:repeat(5,1fr); } .status { display:none; } }
    `;
  }
}

if (!customElements.get("govee-led-studio")) customElements.define("govee-led-studio", GoveeLedStudio);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "govee-led-studio")) {
  window.customCards.push({ type: "govee-led-studio", name: "Govee LED Studio", description: "H6069- en H70B3-bediening met tekenvlak, patronen en GIF-speler.", preview: true });
}
console.info(`%c Govee LED Studio %c ${CARD_VERSION} `, "color:white;background:#7857ff;font-weight:bold", "color:#7857ff;background:#eee");
