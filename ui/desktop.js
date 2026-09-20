/* TZ virtual desktop — Windows 3.1 look, plain ES2020, no dependencies.
   Sections: helpers, api, events (SSE), WindowManager, MsgBox, Icons, Boot, Start, Chat,
   Search, Browser, Files, Settings, Clock, Confirm, ProgMan menus, StatusStrip, boot(). */
'use strict';

const DEFAULT_IDS = ['time-japan', 'time-new-mexico', 'time-portsmouth', 'weather-here', 'latest-news'];
const TEXT_EXT = ['.md', '.txt', '.py', '.json', '.html', '.css', '.js', '.ps1', '.cmd', '.csv', '.log'];
const IMAGE_EXT = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'];
const ICON_NAMES = ['preset', 'clock', 'search', 'browser', 'chat', 'files', 'settings', 'start', 'program', 'tz'];

// Shared page state. `state` is api/state (or null offline); `config` is api/config (or defaults).
const S = {
  state: null,
  config: { open: 'ask', wallpaper: '#008080', wallpaper_image: '', chime: false, removed: [], presets: [] },
  online: false,
  busy: false,
};

// ---------------------------------------------------------------- helpers

function $(sel, root) { return (root || document).querySelector(sel); }

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'style') node.style.cssText = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of children) if (c !== null && c !== undefined) node.append(c);
  return node;
}

function load(key, fallback) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
}
function store(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ }
}
function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }
function ext(name) { const i = name.lastIndexOf('.'); return i < 0 ? '' : name.slice(i).toLowerCase(); }
function fmtSize(n) {
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
  if (n < 1073741824) return (n / 1048576).toFixed(1) + ' MB';
  return (n / 1073741824).toFixed(1) + ' GB';
}
function iconSrc(name) { return 'icons/' + (name || 'preset') + '.svg'; }
function iconImg(name) {
  const img = el('img', { src: iconSrc(name), alt: '', draggable: 'false' });
  img.addEventListener('error', () => { if (!img.src.endsWith('preset.svg')) img.src = iconSrc('preset'); });
  return img;
}

// ---------------------------------------------------------------- api

class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

const api = {
  async call(method, path, body, raw) {
    let res;
    try {
      res = await fetch('../api/' + path, {
        method,
        cache: 'no-store',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      throw new ApiError('TZ is not reachable.', 0);
    }
    const text = await res.text();
    if (!res.ok) {
      let msg = 'HTTP ' + res.status;
      try { msg = JSON.parse(text).error || msg; } catch (e) { /* not json */ }
      if (res.status === 409) msg = 'TZ is busy with another request.';
      throw new ApiError(msg, res.status);
    }
    if (raw) return text;
    try { return JSON.parse(text); } catch (e) { return text; }
  },
  get(path) { return this.call('GET', path); },
  text(path) { return this.call('GET', path, null, true); },
  post(path, body) { return this.call('POST', path, body || {}); },
  put(path, body) { return this.call('PUT', path, body); },
};

// Report a failed call: a message box, or a status-strip note when `quiet`.
function fail(e, quiet, title) {
  const msg = (e && e.message) || String(e);
  if (quiet || (e && e.status === 0)) Status.note(msg);
  else msgBox({ title: title || 'TZ', text: msg, icon: '!' });
}

// ---------------------------------------------------------------- events (SSE)

const Events = {
  src: null,
  handlers: {},
  timer: null,
  on(type, fn) { (this.handlers[type] = this.handlers[type] || []).push(fn); },
  emit(type, ev) {
    for (const fn of this.handlers[type] || []) {
      try { fn(ev); } catch (e) { console.error('event handler', type, e); }
    }
  },
  connect() {
    clearTimeout(this.timer);
    if (this.src) this.src.close();
    let src;
    try { src = new EventSource('../api/events'); } catch (e) { this.setOnline(false); this.retry(); return; }
    this.src = src;
    src.onopen = () => this.setOnline(true);
    src.onmessage = (e) => {
      let ev;
      try { ev = JSON.parse(e.data); } catch (err) { return; }
      if (!ev || !ev.type) return;
      this.setOnline(true);
      this.emit(ev.type, ev);
    };
    src.onerror = () => {
      this.setOnline(false);
      if (src.readyState === EventSource.CLOSED) this.retry();
    };
  },
  retry() { clearTimeout(this.timer); this.timer = setTimeout(() => this.connect(), 10000); },
  setOnline(v) { if (S.online !== v) { S.online = v; Status.render(); } },
};

// ---------------------------------------------------------------- WindowManager

const Popup = {
  el: null,
  show(x, y, items) {
    this.hide();
    const menu = el('div', { class: 'popup' });
    for (const it of items) {
      if (it === '-') { menu.append(el('div', { class: 'sep' })); continue; }
      const row = el('div', { class: 'pi' + (it.disabled ? ' disabled' : ''), text: it.label });
      row.addEventListener('click', (e) => {
        e.stopPropagation();
        if (it.disabled) return;
        this.hide();
        it.action && it.action();
      });
      menu.append(row);
    }
    document.body.append(menu);
    const r = menu.getBoundingClientRect();
    menu.style.left = Math.max(0, Math.min(x, innerWidth - r.width)) + 'px';
    menu.style.top = Math.max(0, Math.min(y, innerHeight - r.height)) + 'px';
    this.el = menu;
  },
  hide() {
    if (this.el) { this.el.remove(); this.el = null; }
    document.querySelectorAll('.menu-item.open').forEach((m) => m.classList.remove('open'));
  },
};

class Win {
  constructor(opts) {
    this.opts = opts;
    this.name = opts.name;
    this.minimized = false;
    this.maximized = false;
    this.el = el('div', { class: 'win' + (opts.dialog ? ' dialog' : ''), 'data-name': opts.name });
    const title = el('div', { class: 'win-title' });
    this.sys = el('div', { class: 'sysmenu' });
    this.titleText = el('span', { class: 'title-text', text: opts.title });
    title.append(this.sys, this.titleText);
    if (!opts.dialog) {
      this.minBtn = el('div', { class: 'tbtn', text: '▼', title: 'Minimize' });
      this.maxBtn = el('div', { class: 'tbtn', text: '▲', title: 'Maximize' });
      title.append(this.minBtn, this.maxBtn);
      this.minBtn.addEventListener('click', (e) => { e.stopPropagation(); this.minimize(); });
      this.maxBtn.addEventListener('click', (e) => { e.stopPropagation(); this.maximize(); });
    }
    this.el.append(title);
    if (opts.menu) this.el.append(this.buildMenu(opts.menu));
    this.body = el('div', { class: 'win-body' + (opts.pad === false ? '' : ' pad') });
    this.el.append(this.body);
    if (!opts.dialog && opts.resizable !== false) {
      this.grip = el('div', { class: 'resize' });
      this.el.append(this.grip);
      this.bindResize();
    }
    this.bindTitle(title);
    this.sys.addEventListener('click', (e) => { e.stopPropagation(); this.systemMenu(); });
    this.sys.addEventListener('dblclick', (e) => { e.stopPropagation(); this.close(); });
    this.el.addEventListener('pointerdown', () => WM.activate(this), true);
  }

  buildMenu(menu) {
    const bar = el('div', { class: 'menubar' });
    for (const m of menu) {
      const item = el('span', { class: 'menu-item', text: m.label });
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        if (item.classList.contains('open')) { Popup.hide(); return; }
        const r = item.getBoundingClientRect();
        Popup.show(r.left, r.bottom, m.items());
        item.classList.add('open');
      });
      bar.append(item);
    }
    return bar;
  }

  bindTitle(title) {
    let drag = null;
    title.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 || (e.target !== title && e.target !== this.titleText)) return;
      if (this.maximized) return;
      drag = { x: e.clientX - this.el.offsetLeft, y: e.clientY - this.el.offsetTop };
      title.setPointerCapture(e.pointerId);
    });
    title.addEventListener('pointermove', (e) => {
      if (!drag) return;
      this.moveTo(e.clientX - drag.x, e.clientY - drag.y);
    });
    const end = () => { if (drag) { drag = null; this.persist(); } };
    title.addEventListener('pointerup', end);
    title.addEventListener('pointercancel', end);
    title.addEventListener('dblclick', (e) => {
      if (!this.opts.dialog && (e.target === title || e.target === this.titleText)) this.maximize();
    });
  }

  bindResize() {
    let rs = null;
    this.grip.addEventListener('pointerdown', (e) => {
      rs = { x: e.clientX, y: e.clientY, w: this.el.offsetWidth, h: this.el.offsetHeight };
      this.grip.setPointerCapture(e.pointerId);
      e.stopPropagation();
    });
    this.grip.addEventListener('pointermove', (e) => {
      if (!rs) return;
      this.el.style.width = Math.max(140, rs.w + e.clientX - rs.x) + 'px';
      this.el.style.height = Math.max(70, rs.h + e.clientY - rs.y) + 'px';
    });
    const end = () => { if (rs) { rs = null; this.persist(); } };
    this.grip.addEventListener('pointerup', end);
    this.grip.addEventListener('pointercancel', end);
  }

  moveTo(x, y) {
    const dw = WM.desk.clientWidth, dh = WM.desk.clientHeight;
    x = Math.max(-this.el.offsetWidth + 60, Math.min(x, dw - 60));
    y = Math.max(0, Math.min(y, dh - 24));
    this.el.style.left = Math.round(x) + 'px';
    this.el.style.top = Math.round(y) + 'px';
  }

  rect() {
    return { x: this.el.offsetLeft, y: this.el.offsetTop, w: this.el.offsetWidth, h: this.el.offsetHeight };
  }

  persist() {
    if (this.opts.persist === false || this.opts.dialog || this.maximized) return;
    store('tz.win.' + this.name, this.rect());
  }

  setTitle(t) { this.titleText.textContent = t; }

  center() {
    const dw = WM.desk.clientWidth, dh = WM.desk.clientHeight;
    this.moveTo((dw - this.el.offsetWidth) / 2, Math.max(0, (dh - this.el.offsetHeight) / 2 - 20));
  }

  raise() { this.el.style.zIndex = ++WM.z; }

  minimize() {
    if (this.minimized) return;
    this.minimized = true;
    this.el.style.display = 'none';
    this.mini = el('div', { class: 'icon mini', title: this.opts.title },
      iconImg(this.opts.icon || 'program'), el('span', { class: 'label', text: this.opts.short || this.opts.title }));
    this.mini.addEventListener('click', (e) => {
      e.stopPropagation();
      Icons.grid.clear();
      document.querySelectorAll('.mini.selected').forEach((m) => m.classList.remove('selected'));
      this.mini.classList.add('selected');
    });
    this.mini.addEventListener('dblclick', (e) => { e.stopPropagation(); this.restore(); });
    this.mini.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      Popup.show(e.clientX, e.clientY, [
        { label: 'Restore', action: () => this.restore() },
        '-',
        { label: 'Close', action: () => this.close() },
      ]);
    });
    WM.minis.append(this.mini);
    WM.layoutMinis();
    if (WM.active === this) WM.activate(null);
  }

  restore() {
    if (this.minimized) {
      this.minimized = false;
      this.mini.remove();
      this.mini = null;
      this.el.style.display = '';
      WM.layoutMinis();
    } else if (this.maximized) {
      this.maximize();
    }
    WM.activate(this);
  }

  maximize() {
    if (this.opts.dialog) return;
    if (this.maximized) {
      this.maximized = false;
      this.el.classList.remove('maximized');
      Object.assign(this.el.style, { left: this.prev.x + 'px', top: this.prev.y + 'px', width: this.prev.w + 'px', height: this.prev.h + 'px' });
      this.maxBtn.textContent = '▲';
    } else {
      this.prev = this.rect();
      this.maximized = true;
      this.el.classList.add('maximized');
      Object.assign(this.el.style, { left: '0px', top: '0px', width: WM.desk.clientWidth + 'px', height: WM.desk.clientHeight + 'px' });
      this.maxBtn.textContent = '⇕';
    }
    WM.activate(this);
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    if (this.mini) this.mini.remove();
    if (this.dim) this.dim.remove();
    this.el.remove();
    WM.wins.delete(this.name);
    WM.layoutMinis();
    if (WM.active === this) WM.activate(WM.top());
    if (this.opts.onClose) this.opts.onClose();
  }

  systemMenu() {
    const r = this.sys.getBoundingClientRect();
    Popup.show(r.left, r.bottom, [
      { label: 'Restore', disabled: !this.maximized, action: () => this.restore() },
      { label: 'Move', disabled: true },
      { label: 'Size', disabled: true },
      { label: 'Minimize', disabled: !!this.opts.dialog, action: () => this.minimize() },
      { label: 'Maximize', disabled: !!this.opts.dialog || this.maximized, action: () => this.maximize() },
      '-',
      { label: 'Close        Alt+F4', action: () => this.close() },
    ]);
  }
}

const WM = {
  wins: new Map(),
  factories: {},
  z: 10,
  active: null,
  desk: null,
  layer: null,
  minis: null,

  init() {
    this.desk = $('#desktop');
    this.layer = $('#windows');
    this.minis = $('#minis');
    this.desk.addEventListener('pointerdown', (e) => {
      if (e.target === this.desk || e.target === $('#icons')) { this.activate(null); this.desk.focus(); }
    });
    addEventListener('resize', () => {
      this.layoutMinis();
      for (const w of this.wins.values()) {
        if (w.maximized) {
          w.el.style.width = this.desk.clientWidth + 'px';
          w.el.style.height = this.desk.clientHeight + 'px';
        } else if (!w.minimized) w.moveTo(w.el.offsetLeft, w.el.offsetTop);
      }
    });
  },

  register(name, factory) { this.factories[name] = factory; },

  // Idempotent: raises (and restores) an existing window, otherwise builds it.
  open(name) {
    const w = this.wins.get(name);
    if (w) { w.restore(); w.raise(); return w; }
    const factory = this.factories[name];
    return factory ? factory() : null;
  },

  create(opts) {
    const existing = this.wins.get(opts.name);
    if (existing) { existing.restore(); return existing; }
    const w = new Win(opts);
    this.wins.set(opts.name, w);
    if (opts.modal) {
      w.dim = el('div', { class: 'modal-dim' });
      w.dim.style.zIndex = ++this.z;
      this.layer.append(w.dim);
    }
    this.layer.append(w.el);
    const saved = opts.dialog || opts.persist === false ? null : load('tz.win.' + opts.name);
    const width = (saved && saved.w) || opts.w || 400;
    const height = (saved && saved.h) || opts.h;
    w.el.style.width = width + 'px';
    w.el.style.height = height ? height + 'px' : 'auto';
    if (saved) w.moveTo(saved.x, saved.y);
    else if (opts.x === undefined || opts.y === undefined) w.center();
    else w.moveTo(opts.x, opts.y);
    this.activate(w);
    return w;
  },

  // Focus a field inside a freshly built window (after its content is appended).
  focus(w, sel) {
    setTimeout(() => { const f = w.body.querySelector(sel); if (f && !w.closed) f.focus(); }, 0);
  },

  activate(w) {
    for (const other of this.wins.values()) other.el.classList.toggle('active', other === w);
    $('#progman').classList.toggle('active', !w);
    this.active = w;
    if (w) {
      w.raise();
      if (w.dim) w.dim.style.zIndex = w.el.style.zIndex - 1;
    }
  },

  top() {
    let best = null;
    for (const w of this.wins.values()) {
      if (w.minimized) continue;
      if (!best || +w.el.style.zIndex > +best.el.style.zIndex) best = w;
    }
    return best;
  },

  layoutMinis() {
    const dh = this.desk.clientHeight;
    let i = 0;
    for (const w of this.wins.values()) if (w.mini) {
      w.mini.style.left = (8 + i * 80) + 'px';
      w.mini.style.top = (dh - 66) + 'px';
      i++;
    }
  },

  cascade() {
    let i = 0;
    for (const w of this.wins.values()) {
      if (w.minimized || w.opts.dialog) continue;
      if (w.maximized) w.maximize();
      w.moveTo(20 + i * 24, 20 + i * 24);
      w.persist();
      w.raise();
      i++;
    }
  },

  tile() {
    const list = [...this.wins.values()].filter((w) => !w.minimized && !w.opts.dialog);
    if (!list.length) return;
    const cols = Math.ceil(Math.sqrt(list.length)), rows = Math.ceil(list.length / cols);
    const cw = Math.floor(this.desk.clientWidth / cols), ch = Math.floor(this.desk.clientHeight / rows);
    list.forEach((w, i) => {
      if (w.maximized) w.maximize();
      w.el.style.width = cw + 'px';
      w.el.style.height = ch + 'px';
      w.moveTo((i % cols) * cw, Math.floor(i / cols) * ch);
      w.persist();
    });
  },
};

// ---------------------------------------------------------------- MsgBox

// Win3.x message box. Resolves with the label of the button pressed (or null when closed).
function msgBox({ title = 'TZ', text = '', icon = '!', buttons = ['OK'], name, modal = true }) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v); } };
    const w = WM.create({
      name: name || 'msg:' + Math.random().toString(36).slice(2),
      title, dialog: true, modal, w: 340, pad: false,
      onClose: () => finish(null),
    });
    const box = el('div', { class: 'msgbox' },
      el('div', { class: 'mb-icon' + (icon === '!' ? ' warn' : ''), text: icon }),
      el('div', { class: 'mb-text', text }));
    const row = el('div', { class: 'buttons', style: 'justify-content:center;padding:6px 10px 10px' });
    buttons.forEach((label, i) => {
      const b = el('button', { text: label, class: i === 0 ? 'default' : '' });
      b.addEventListener('click', () => { finish(label); w.close(); });
      row.append(b);
    });
    w.body.append(box, row);
    w.center();
    w.answered = () => finish(buttons[buttons.length - 1]);
    setTimeout(() => row.querySelector('button').focus(), 0);
  });
}

// ---------------------------------------------------------------- Icons

// Selectable icon grid used by the desktop (absolute, draggable) and group windows (flow).
class IconGrid {
  // container holds the icons; opts.keys (default: container) is the focusable element that takes arrow keys.
  constructor(container, opts) {
    this.c = container;
    this.opts = opts;
    this.focusEl = opts.keys || container;
    this.items = [];
    this.selected = null;
    this.focusEl.addEventListener('keydown', (e) => this.keys(e));
  }

  clear() { this.select(null); }

  select(id) {
    this.selected = id;
    for (const node of this.c.querySelectorAll('.icon')) node.classList.toggle('selected', node.dataset.id === id);
  }

  current() { return this.items.find((i) => i.id === this.selected); }

  setItems(items) {
    this.items = items;
    this.c.querySelectorAll('.icon').forEach((n) => n.remove());
    for (const it of items) {
      const node = el('div', { class: 'icon', 'data-id': it.id, title: it.label },
        iconImg(it.icon), el('span', { class: 'label', text: it.label }));
      node.addEventListener('dblclick', (e) => { e.stopPropagation(); this.opts.onOpen(it); });
      node.addEventListener('contextmenu', (e) => {
        e.preventDefault(); e.stopPropagation();
        this.select(it.id);
        if (this.opts.onContext) this.opts.onContext(it, e);
      });
      if (this.opts.absolute) this.bindDrag(node, it);
      else node.addEventListener('pointerdown', (e) => { e.stopPropagation(); this.select(it.id); this.focusEl.focus(); });
      this.c.append(node);
      it.node = node;
    }
    if (this.selected && !items.some((i) => i.id === this.selected)) this.selected = null;
  }

  bindDrag(node, it) {
    let drag = null;
    node.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      e.stopPropagation();
      this.select(it.id);
      this.focusEl.focus();
      drag = { sx: e.clientX, sy: e.clientY, x: node.offsetLeft, y: node.offsetTop, moved: false };
      node.setPointerCapture(e.pointerId);
    });
    node.addEventListener('pointermove', (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      drag.moved = true;
      node.classList.add('dragging');
      node.style.left = Math.max(0, drag.x + dx) + 'px';
      node.style.top = Math.max(0, drag.y + dy) + 'px';
    });
    const end = () => {
      if (!drag) return;
      node.classList.remove('dragging');
      if (drag.moved && this.opts.onMove) this.opts.onMove(it, node.offsetLeft, node.offsetTop);
      drag = null;
    };
    node.addEventListener('pointerup', end);
    node.addEventListener('pointercancel', end);
  }

  keys(e) {
    if (e.target !== this.focusEl) return;
    const cur = this.current();
    if (e.key === 'Enter' && cur) { e.preventDefault(); this.opts.onOpen(cur); return; }
    if (e.key === 'Delete' && cur && this.opts.onDelete) { e.preventDefault(); this.opts.onDelete(cur); return; }
    const dir = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    if (!dir || !this.items.length) return;
    e.preventDefault();
    if (!cur) { this.select(this.items[0].id); return; }
    const cr = cur.node.getBoundingClientRect();
    let best = null, bestScore = Infinity;
    for (const it of this.items) {
      if (it === cur) continue;
      const r = it.node.getBoundingClientRect();
      const dx = r.left - cr.left, dy = r.top - cr.top;
      const along = dx * dir[0] + dy * dir[1], across = Math.abs(dx * dir[1]) + Math.abs(dy * dir[0]);
      if (along <= 0) continue;
      const score = along + across * 3;
      if (score < bestScore) { bestScore = score; best = it; }
    }
    if (best) { this.select(best.id); best.node.scrollIntoView({ block: 'nearest' }); }
  }
}

const Icons = {
  list: [
    { id: 'start', label: 'Start', icon: 'start' },
    { id: 'chat', label: 'Chat', icon: 'chat' },
    { id: 'search', label: 'Search', icon: 'search' },
    { id: 'browser', label: 'Browser', icon: 'browser' },
    { id: 'files', label: 'Files', icon: 'files' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
    { id: 'clock', label: 'Clock', icon: 'clock' },
  ],
  grid: null,

  init() {
    this.grid = new IconGrid($('#icons'), {
      absolute: true,
      keys: WM.desk,
      onOpen: (it) => WM.open(it.id),
      onMove: (it, x, y) => store('tz.icon.' + it.id, { x, y }),
      onContext: (it, e) => Popup.show(e.clientX, e.clientY, [
        { label: 'Open', action: () => WM.open(it.id) },
      ]),
    });
    this.grid.setItems(this.list);
    this.arrange(false);
  },

  arrange(reset) {
    this.list.forEach((it, i) => {
      const saved = reset ? null : load('tz.icon.' + it.id);
      if (reset) try { localStorage.removeItem('tz.icon.' + it.id); } catch (e) { /* ignore */ }
      it.node.style.left = (saved ? saved.x : 12 + i * 80) + 'px';
      it.node.style.top = (saved ? saved.y : 10) + 'px';
    });
  },
};

// ---------------------------------------------------------------- Boot

const Boot = {
  async run() {
    const box = $('#boot'), pre = $('#boot-text');
    let skipped = false;
    const finish = (now) => {
      if (!box.parentNode) return;
      box.classList.add('fade');
      setTimeout(() => box.remove(), now ? 0 : 300);
    };
    box.addEventListener('click', () => { skipped = true; finish(true); }, { once: true });
    const line = (t) => { pre.textContent += t + '\n'; };
    let st = null;
    try { st = await api.get('state'); } catch (e) { /* offline */ }
    if (skipped) return;
    if (st && typeof st === 'object') {
      S.state = st;
      line('TZ | LOCAL AGENT | ' + String(st.routing || '').toUpperCase());
      line('Model: ' + (st.model || '?') + (st.model_description ? ' — ' + st.model_description : ''));
      for (const row of st.specs || []) {
        if (skipped) return;
        line(row[0] + ': ' + row[1]);
        await wait(40);
      }
      await wait(200);
    } else {
      line('TZ | LOCAL AGENT | offline');
      await wait(800);
    }
    if (skipped) return;
    line('Loading desktop…');
    await wait(250);
    finish(false);
  },
};

function chime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const play = () => {
      const t0 = ctx.currentTime;
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = 'square';
        o.frequency.value = f;
        g.gain.setValueAtTime(0.0001, t0 + i * 0.12);
        g.gain.exponentialRampToValueAtTime(0.08, t0 + i * 0.12 + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + i * 0.12 + 0.11);
        o.connect(g).connect(ctx.destination);
        o.start(t0 + i * 0.12);
        o.stop(t0 + i * 0.12 + 0.12);
      });
    };
    if (ctx.state === 'suspended') addEventListener('pointerdown', () => ctx.resume().then(play), { once: true });
    else play();
  } catch (e) { /* no audio */ }
}

// ---------------------------------------------------------------- Start

const Start = {
  win: null,
  open() { return WM.open('start'); },
  create() {
    const w = WM.create({ name: 'start', title: 'Start', icon: 'start', w: 460, h: 320, x: 110, y: 70 });
    this.win = w;
    this.render();
    WM.focus(w, 'input');
    return w;
  },
  render() {
    const w = this.win;
    if (!w || w.closed) return;
    const st = S.state;
    w.body.textContent = '';
    w.body.append(el('div', { class: 'greeting', text: 'Hello, I\'m ' + ((st && st.label) || 'TZ') + '.' }));
    const table = el('table', { class: 'specs' });
    if (st && st.specs && st.specs.length) {
      for (const [k, v] of st.specs) table.append(el('tr', null, el('td', { text: k }), el('td', { text: v })));
    } else {
      table.append(el('tr', null, el('td', { text: 'Agent' }),
        el('td', { text: st ? (st.model || '') : 'offline — start TZ from the terminal' })));
    }
    w.body.append(el('div', { class: 'grow', style: 'overflow:auto' }, table));
    const input = el('input', { type: 'text', placeholder: 'What can I do for you?' });
    const send = el('button', { text: 'Send', class: 'default' });
    const go = () => { const t = input.value.trim(); if (!t) return; input.value = ''; Chat.send(t); };
    send.addEventListener('click', go);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
    w.body.append(el('div', { class: 'row' }, el('span', { class: 'mono', text: 'Me >' }), input, send));
  },
};
WM.register('start', () => Start.create());

// ---------------------------------------------------------------- Chat

const Chat = {
  win: null, log: null, input: null, sendBtn: null, pager: null,
  sessions: [], sessionId: '', aiLine: null,

  open() { return WM.open('chat'); },

  create() {
    const w = WM.create({ name: 'chat', title: 'Chat', short: 'Chat', icon: 'chat', w: 560, h: 380, x: 300, y: 90 });
    this.win = w;
    const prev = el('button', { text: '◀', title: 'Older session' });
    const next = el('button', { text: '▶', title: 'Newer session' });
    this.pager = el('span', { class: 'pager', text: '–/–' });
    const fresh = el('button', { text: 'New', title: 'Start a new session' });
    prev.addEventListener('click', () => this.page(1));
    next.addEventListener('click', () => this.page(-1));
    fresh.addEventListener('click', () => this.newSession());
    w.body.append(el('div', { class: 'chat-tools' }, prev, this.pager, next, fresh,
      el('span', { class: 'grow' }), el('span', { class: 'hint', text: 'Terminal: same session, same agent' })));
    this.log = el('div', { class: 'chat-log' });
    this.input = el('textarea', { placeholder: 'Enter sends, Shift+Enter for a new line' });
    this.sendBtn = el('button', { text: 'Send', class: 'default' });
    this.sendBtn.addEventListener('click', () => this.submit());
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.submit(); }
    });
    w.body.append(this.log, el('div', { class: 'chat-input' },
      el('span', { class: 'prompt', text: 'Me >' }), this.input, this.sendBtn));
    this.setBusy(S.busy);
    this.loading = this.load();
    WM.focus(w, 'textarea');
    return w;
  },

  line(text, cls) {
    if (!this.log) return null;
    const d = el('div', { class: cls || '', text });
    this.log.append(d);
    this.log.scrollTop = this.log.scrollHeight;
    return d;
  },

  classify(text) {
    if (/^\[(incomplete|tool error)\]/.test(text)) return 'warn';
    if (/^\[(route|model|usage|tool|waiting)\]/.test(text)) return 'dim';
    return '';
  },

  // Saved messages -> log lines. Returns a fragment so the caller can splice it in.
  renderMessages(msgs) {
    const frag = document.createDocumentFragment();
    const add = (text, cls) => frag.append(el('div', { class: cls || '', text }));
    for (const m of msgs || []) {
      const content = typeof m.content === 'string' ? m.content : '';
      if (m.role === 'user') add('Me > ' + content);
      else if (m.role === 'assistant') {
        if (content.startsWith('Tool evidence (data): ')) {
          add('[evidence] ' + content.slice(22, 322) + (content.length > 322 ? '…' : ''), 'dim');
        } else if (content) add('AI > ' + content);
        for (const c of m.tool_calls || []) add('[tool] ' + ((c.function && c.function.name) || c.name || 'tool'), 'dim');
      } else if (m.role === 'tool') add('[tool] ' + (m.tool_name || m.name || 'tool'), 'dim');
    }
    return frag;
  },

  async load() {
    if (!this.win || this.win.closed) return;
    // live lines that arrive while the history is fetched stay; only the old content is replaced
    const stale = [...this.log.children];
    let frag;
    try {
      const s = await api.get('sessions/current');
      this.sessionId = s.id || '';
      frag = this.renderMessages(s.messages);
      this.win.setTitle('Chat — ' + this.sessionId);
    } catch (e) {
      frag = this.renderMessages([]);
      frag.append(el('div', { class: 'dim', text: '[offline] ' + e.message }));
      this.win.setTitle('Chat — offline');
    }
    stale.forEach((n) => n.remove());
    this.log.prepend(frag);
    this.log.scrollTop = this.log.scrollHeight;
    try {
      const list = await api.get('sessions');
      this.sessions = Array.isArray(list) ? list : [];
    } catch (e) { this.sessions = []; }
    this.renderPager();
  },

  index() { return this.sessions.findIndex((s) => s.id === this.sessionId || s.current); },

  renderPager() {
    const n = this.sessions.length, i = this.index();
    this.pager.textContent = n && i >= 0 ? (n - i) + '/' + n : (n ? '?/' + n : '–/–');
  },

  // delta +1 = older (list is newest first), -1 = newer
  async page(delta) {
    const i = this.index() + delta;
    if (!this.sessions.length || i < 0 || i >= this.sessions.length) return;
    try {
      await api.post('sessions/' + encodeURIComponent(this.sessions[i].id) + '/resume');
      await this.load();
    } catch (e) { fail(e); }
  },

  async newSession() {
    try { await api.post('sessions/new'); await this.load(); } catch (e) { fail(e); }
  },

  submit() {
    const t = this.input.value.trim();
    if (!t || S.busy) return;
    this.input.value = '';
    this.send(t);
  },

  async send(text) {
    this.open();
    await this.loading;
    this.line('Me > ' + text);
    this.aiLine = null;
    try {
      await api.post('turn', { text });
    } catch (e) {
      this.line('[error] ' + e.message, 'warn');
      if (e.status === 409) fail(e); else Status.note(e.message);
    }
  },

  setBusy(b) {
    S.busy = b;
    if (!this.win || this.win.closed) return;
    this.sendBtn.disabled = b;
    const base = 'Chat — ' + (this.sessionId || 'offline');
    this.win.setTitle(b ? base + ' — working…' : base);
  },

  onTurnStart(ev) {
    if (!this.win || this.win.closed) this.open();
    if (ev.source === 'terminal') this.line('Me > ' + (ev.text || ''));
    this.aiLine = null;
    this.setBusy(true);
  },
  onLine(ev) {
    if (!this.log) return;
    this.aiLine = null;
    const t = ev.text || '';
    if (t !== '') this.line(t, this.classify(t));
  },
  onStream(ev) {
    if (!this.log) return;
    if (!this.aiLine) this.aiLine = this.line('AI > ');
    this.aiLine.textContent += ev.text || '';
    this.log.scrollTop = this.log.scrollHeight;
  },
  onTurnEnd(ev) {
    this.aiLine = null;
    if (ev.ok === false && ev.error) this.line('[error] ' + ev.error, 'warn');
    this.setBusy(false);
  },
};
WM.register('chat', () => Chat.create());
Events.on('turn_start', (ev) => Chat.onTurnStart(ev));
Events.on('line', (ev) => Chat.onLine(ev));
Events.on('stream', (ev) => Chat.onStream(ev));
Events.on('turn_end', (ev) => Chat.onTurnEnd(ev));
Events.on('session', () => Chat.load());
Events.on('status', (ev) => { if (typeof ev.busy === 'boolean' && ev.busy !== S.busy) Chat.setBusy(ev.busy); });

// ---------------------------------------------------------------- Search (preset group window)

const Search = {
  win: null, grid: null,
  open() { return WM.open('search'); },

  create() {
    const w = WM.create({ name: 'search', title: 'Search', icon: 'search', w: 440, h: 260, x: 200, y: 120, pad: false });
    this.win = w;
    const group = el('div', { class: 'group', tabindex: '0' });
    w.body.append(group);
    this.grid = new IconGrid(group, {
      onOpen: (it) => this.run(it),
      onDelete: (it) => it.data && this.remove(it.data),
      onContext: (it, e) => Popup.show(e.clientX, e.clientY, it.data ? [
        { label: 'Run', action: () => this.run(it) },
        '-',
        { label: 'Delete', action: () => this.remove(it.data) },
      ] : [{ label: 'New preset…', action: () => this.newDialog() }]),
    });
    group.addEventListener('pointerdown', (e) => { if (e.target === group) this.grid.clear(); });
    this.refresh();
    WM.focus(w, '.group');
    return w;
  },

  refresh() {
    if (!this.grid) return;
    const items = (S.config.presets || []).map((p) => ({ id: p.id, label: p.name, icon: p.icon || 'preset', data: p }));
    items.push({ id: '+new', label: '+ New preset', icon: 'preset' });
    this.grid.setItems(items);
  },

  userPresets() { return (S.config.presets || []).filter((p) => !DEFAULT_IDS.includes(p.id)); },

  async run(it) {
    if (!it.data) { this.newDialog(); return; }
    const p = it.data;
    if (p.mode === 'browser') {
      try {
        await api.post('open', { url: 'https://www.google.com/search?q=' + encodeURIComponent(p.phrase) });
        Status.note('Opened in browser: ' + p.name);
      } catch (e) { fail(e); }
    } else {
      Chat.send(p.phrase);
    }
  },

  async save(changes) {
    try {
      const cfg = await api.put('config', changes);
      if (cfg && typeof cfg === 'object') S.config = cfg;
      this.refresh();
      return true;
    } catch (e) { fail(e, false, 'Search'); return false; }
  },

  async remove(p) {
    const a = await msgBox({ title: 'Search', icon: '?', text: 'Delete the preset "' + p.name + '"?', buttons: ['Yes', 'No'] });
    if (a !== 'Yes') return;
    if (DEFAULT_IDS.includes(p.id)) {
      const removed = (S.config.removed || []).filter((id) => id !== p.id);
      removed.push(p.id);
      this.save({ removed });
    } else {
      this.save({ presets: this.userPresets().filter((u) => u.id !== p.id) });
    }
  },

  newDialog() {
    const w = WM.create({ name: 'newpreset', title: 'New Preset', dialog: true, modal: true, w: 360 });
    const name = el('input', { type: 'text' });
    const phrase = el('input', { type: 'text' });
    const modeAsk = el('input', { type: 'radio', name: 'pmode', value: 'ask', checked: 'checked' });
    const modeWeb = el('input', { type: 'radio', name: 'pmode', value: 'browser' });
    const icon = el('select');
    for (const n of ICON_NAMES) icon.append(el('option', { value: n, text: n }));
    const preview = iconImg('preset');
    preview.style.cssText = 'width:32px;height:32px;vertical-align:middle;margin-left:8px;image-rendering:pixelated';
    icon.addEventListener('change', () => { preview.src = iconSrc(icon.value); });
    const ok = el('button', { text: 'OK', class: 'default' });
    const cancel = el('button', { text: 'Cancel' });
    cancel.addEventListener('click', () => w.close());
    ok.addEventListener('click', async () => {
      const n = name.value.trim(), ph = phrase.value.trim();
      if (!n || !ph) { msgBox({ title: 'New Preset', text: 'Name and phrase are both required.' }); return; }
      const id = n.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '-' + Date.now().toString(36);
      const preset = { id, name: n, phrase: ph, mode: modeWeb.checked ? 'browser' : 'ask', icon: icon.value };
      if (await this.save({ presets: [...this.userPresets(), preset] })) w.close();
    });
    for (const f of [name, phrase]) f.addEventListener('keydown', (e) => { if (e.key === 'Enter') ok.click(); });
    w.body.append(
      el('div', { class: 'form-grid' },
        el('label', { text: 'Name:' }), name,
        el('label', { text: 'Phrase:' }), phrase,
        el('label', { text: 'Mode:' }), el('div', null,
          el('label', { class: 'opt' }, modeAsk, 'Ask TZ'),
          el('label', { class: 'opt' }, modeWeb, 'Open in browser')),
        el('label', { text: 'Icon:' }), el('div', null, icon, preview)),
      el('div', { class: 'buttons' }, ok, cancel));
    WM.focus(w, 'input');
    return w;
  },
};
WM.register('search', () => Search.create());

// ---------------------------------------------------------------- Browser

const Browser = {
  open() { return WM.open('browser'); },
  toUrl(text) {
    text = text.trim();
    if (!text) return 'https://www.google.com/';
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(text)) return text;
    if (/\s/.test(text) || !text.includes('.')) return 'https://www.google.com/search?q=' + encodeURIComponent(text);
    return 'https://' + text;
  },
  create() {
    const w = WM.create({ name: 'browser', title: 'Open in browser', dialog: true, w: 400 });
    const input = el('input', { type: 'text', placeholder: 'URL or search terms' });
    const open = el('button', { text: 'Open', class: 'default' });
    const cancel = el('button', { text: 'Cancel' });
    const go = async () => {
      const url = this.toUrl(input.value);
      try { await api.post('open', { url }); Status.note('Opened ' + url); w.close(); }
      catch (e) { fail(e, false, 'Browser'); }
    };
    open.addEventListener('click', go);
    cancel.addEventListener('click', () => w.close());
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
    w.body.append(el('div', { class: 'row' }, el('span', { text: 'Go to:' }), input), el('div', { class: 'buttons' }, open, cancel));
    WM.focus(w, 'input');
    return w;
  },
};
WM.register('browser', () => Browser.create());

// ---------------------------------------------------------------- Files

const Files = {
  open() { return WM.open('files'); },

  // pick: when set, the window is a file picker and clicking a matching file calls pick(path).
  create(opts) {
    opts = opts || {};
    const name = opts.pick ? 'filepick' : 'files';
    const w = WM.create({
      name, title: opts.title || 'File Manager — workspace', short: 'File Manager', icon: 'files',
      w: 560, h: 360, x: 160, y: 100, pad: false, dialog: !!opts.pick,
      menu: opts.pick ? null : [
        { label: 'File', items: () => [{ label: 'Refresh', action: () => this.load(w, w.path) }, '-', { label: 'Exit', action: () => w.close() }] },
        { label: 'Tree', items: () => [{ label: 'Go to workspace root', action: () => this.load(w, '.') }] },
        { label: 'View', items: () => [{ label: 'Name and size', disabled: true }] },
        { label: 'Help', items: () => [{ label: 'About…', action: about }] },
      ],
    });
    w.pick = opts.pick;
    w.filter = opts.filter;
    w.pathBar = el('div', { class: 'fm-path sunken mono', text: 'workspace' });
    w.dirs = el('div', { class: 'fm-pane dirs', tabindex: '0' });
    w.files = el('div', { class: 'fm-pane files', tabindex: '0' });
    w.body.style.padding = '4px';
    w.body.append(w.pathBar, el('div', { class: 'fm-panes' }, w.dirs, w.files));
    if (opts.pick) {
      const cancel = el('button', { text: 'Cancel' });
      cancel.addEventListener('click', () => w.close());
      w.body.append(el('div', { class: 'buttons', style: 'margin:6px 2px 2px' }, cancel));
    }
    this.load(w, '.');
    return w;
  },

  join(dir, name) { return !dir || dir === '.' ? name : dir.replace(/\/+$/, '') + '/' + name; },
  parent(dir) { const i = dir.lastIndexOf('/'); return i < 0 ? '.' : dir.slice(0, i); },

  async load(w, path) {
    w.path = path;
    w.pathBar.textContent = 'workspace' + (path && path !== '.' ? '/' + path : '');
    w.dirs.textContent = '';
    w.files.textContent = '';
    let data;
    try { data = await api.get('files?path=' + encodeURIComponent(path)); }
    catch (e) {
      w.files.append(el('div', { class: 'dim', text: '[offline] ' + e.message }));
      return;
    }
    const entries = (data && data.entries) || [];
    if (path && path !== '.') {
      const up = el('div', { class: 'fm-item dir' }, el('span', { class: 'n', text: '..' }));
      up.addEventListener('dblclick', () => this.load(w, this.parent(path)));
      w.dirs.append(up);
    }
    for (const e of entries.filter((x) => x.dir).sort((a, b) => a.name.localeCompare(b.name))) {
      const row = el('div', { class: 'fm-item dir' }, el('span', { class: 'n', text: e.name }));
      row.addEventListener('click', () => this.selectRow(w, row));
      row.addEventListener('dblclick', () => this.load(w, this.join(path, e.name)));
      w.dirs.append(row);
    }
    for (const e of entries.filter((x) => !x.dir).sort((a, b) => a.name.localeCompare(b.name))) {
      const row = el('div', { class: 'fm-item file' }, el('span', { class: 'n', text: e.name }), el('span', { class: 's', text: fmtSize(e.size || 0) }));
      const dimmed = w.filter && !w.filter.includes(ext(e.name));
      if (dimmed) row.classList.add('dim');
      row.addEventListener('click', () => { this.selectRow(w, row); if (!dimmed) this.openFile(w, this.join(path, e.name), e.name); });
      w.files.append(row);
    }
    if (!entries.length) w.files.append(el('div', { class: 'dim', text: '(empty)' }));
  },

  selectRow(w, row) {
    w.el.querySelectorAll('.fm-item.selected').forEach((r) => r.classList.remove('selected'));
    row.classList.add('selected');
  },

  openFile(w, path, name) {
    const x = ext(name);
    if (w.pick) { w.pick(path); w.close(); return; }
    if (TEXT_EXT.includes(x)) Viewer.text(path, name);
    else if (IMAGE_EXT.includes(x)) Viewer.image(path, name);
    else msgBox({ title: 'File Manager', text: 'No viewer for ' + name + '.' });
  },

  pick(opts) {
    const existing = WM.wins.get('filepick');
    if (existing) existing.close();
    return this.create(opts);
  },
};
WM.register('files', () => Files.create());

const Viewer = {
  async text(path, name) {
    const w = WM.create({ name: 'view:' + path, title: 'View — ' + name, short: name, icon: 'files', w: 600, h: 420, pad: false, persist: false });
    const pre = el('div', { class: 'viewer', text: 'Loading…' });
    w.body.style.padding = '4px';
    w.body.append(pre);
    try { pre.textContent = await api.text('file?path=' + encodeURIComponent(path)); }
    catch (e) { pre.textContent = '[error] ' + e.message; }
  },
  image(path, name) {
    const w = WM.create({ name: 'view:' + path, title: 'View — ' + name, short: name, icon: 'files', w: 520, h: 420, pad: false, persist: false });
    w.body.style.padding = '4px';
    const img = el('img', { src: '../api/file?path=' + encodeURIComponent(path), alt: name });
    img.addEventListener('error', () => { img.replaceWith(el('div', { class: 'dim', text: '[error] could not load ' + name })); });
    w.body.append(el('div', { class: 'viewer' }, img));
  },
};

// ---------------------------------------------------------------- Settings

function applyWallpaper(cfg) {
  const color = cfg.wallpaper || '#008080';
  document.body.style.backgroundColor = color;
  WM.desk.style.backgroundColor = color;
  WM.desk.style.backgroundImage = cfg.wallpaper_image ? 'url("../api/file?path=' + encodeURIComponent(cfg.wallpaper_image) + '")' : 'none';
  WM.desk.style.backgroundSize = 'cover';
  WM.desk.style.backgroundPosition = 'center';
}

const Settings = {
  open() { return WM.open('settings'); },

  create() {
    const w = WM.create({ name: 'settings', title: 'Control Panel — Settings', short: 'Settings', icon: 'settings', w: 470, h: 470, x: 240, y: 40 });
    const cfg = S.config, st = S.state || {};
    const f = {};
    f.color = el('input', { type: 'color', value: /^#[0-9a-f]{6}$/i.test(cfg.wallpaper || '') ? cfg.wallpaper : '#008080' });
    f.image = el('input', { type: 'text', value: cfg.wallpaper_image || '', placeholder: 'workspace path, e.g. pics/wall.png' });
    const swatch = el('span', { class: 'swatch' });
    const browse = el('button', { text: 'Browse…' });
    const preview = () => {
      swatch.style.backgroundColor = f.color.value;
      swatch.style.backgroundImage = f.image.value.trim() ? 'url("../api/file?path=' + encodeURIComponent(f.image.value.trim()) + '")' : 'none';
    };
    f.color.addEventListener('input', preview);
    f.image.addEventListener('input', preview);
    browse.addEventListener('click', () => Files.pick({ title: 'Select wallpaper image', filter: IMAGE_EXT, pick: (p) => { f.image.value = p; preview(); } }));
    preview();

    f.model = el('select');
    f.model.append(el('option', { value: '', text: 'loading…' }));
    const vram = el('span', { class: 'hint' });
    f.auto = el('input', { type: 'radio', name: 'routing', value: 'auto' });
    f.manual = el('input', { type: 'radio', name: 'routing', value: 'manual' });
    (String(st.routing || 'auto').toLowerCase() === 'manual' ? f.manual : f.auto).checked = true;

    f.open = {};
    const openRow = el('div');
    for (const [v, label] of [['ask', 'Ask each time'], ['always', 'Always'], ['never', 'Never']]) {
      f.open[v] = el('input', { type: 'radio', name: 'openui', value: v });
      if ((cfg.open || 'ask') === v) f.open[v].checked = true;
      openRow.append(el('label', { class: 'opt' }, f.open[v], label));
    }
    f.chime = el('input', { type: 'checkbox' });
    f.chime.checked = !!cfg.chime;

    const ok = el('button', { text: 'OK', class: 'default' });
    const apply = el('button', { text: 'Apply' });
    const cancel = el('button', { text: 'Cancel' });
    ok.addEventListener('click', async () => { if (await this.apply(f)) w.close(); });
    apply.addEventListener('click', () => this.apply(f));
    cancel.addEventListener('click', () => w.close());

    const body = el('div', { class: 'settings-body grow' },
      el('fieldset', null, el('legend', { text: 'Desktop' }),
        el('div', { class: 'row', style: 'margin-bottom:6px' }, el('span', { text: 'Wallpaper color:', style: 'width:110px' }), f.color, el('span', { class: 'grow' }), el('span', { text: 'Preview:' }), swatch),
        el('div', { class: 'row' }, el('span', { text: 'Wallpaper image:', style: 'width:110px' }), f.image, browse),
        el('div', { class: 'hint', style: 'margin-top:4px' }, 'Image path is relative to the workspace. Leave empty for a solid color.')),
      el('fieldset', null, el('legend', { text: 'Agent' }),
        el('div', { class: 'row', style: 'margin-bottom:6px' }, el('span', { text: 'Model:', style: 'width:110px' }), f.model, vram),
        el('div', { class: 'row' }, el('span', { text: 'Routing:', style: 'width:110px' }),
          el('label', { class: 'opt' }, f.auto, 'AUTO'), el('label', { class: 'opt', style: 'margin-left:12px' }, f.manual, 'MANUAL')),
        el('div', { class: 'hint', style: 'margin-top:4px' }, 'Apply sends /use <model> or /auto to the agent.')),
      el('fieldset', null, el('legend', { text: 'Startup' }),
        el('div', { class: 'row', style: 'align-items:flex-start' }, el('span', { text: 'Open UI on start:', style: 'width:110px' }), openRow),
        el('div', { class: 'row', style: 'margin-top:6px' }, el('span', { style: 'width:110px' }), el('label', { class: 'opt' }, f.chime, 'Startup chime'))));
    w.body.append(body, el('div', { class: 'buttons' }, ok, apply, cancel));
    this.loadModels(f, vram, st);
    return w;
  },

  async loadModels(f, vram, st) {
    let models = [], total = null;
    try {
      const r = await api.get('models');
      models = Array.isArray(r) ? r : (r && r.models) || [];
      total = r && r.vram_total;
    } catch (e) { /* offline */ }
    f.model.textContent = '';
    const current = st.task_model || st.model || '';
    if (!models.length) f.model.append(el('option', { value: current, text: current ? current + ' (Ollama not reached)' : '(no models)' }));
    if (current && !models.some((m) => m.name === current)) models.unshift({ name: current, size: 0 });
    for (const m of models) {
      const gb = m.size ? ' — ' + (m.size / 1073741824).toFixed(1) + ' GB' : '';
      f.model.append(el('option', { value: m.name, text: m.name + gb }));
    }
    f.model.value = current;
    if (total) vram.textContent = '(' + (total / 1073741824).toFixed(0) + ' GB VRAM)';
  },

  async apply(f) {
    const cfg = S.config, st = S.state || {};
    const changes = {};
    if (f.color.value !== cfg.wallpaper) changes.wallpaper = f.color.value;
    if (f.image.value.trim() !== (cfg.wallpaper_image || '')) changes.wallpaper_image = f.image.value.trim();
    const open = Object.keys(f.open).find((k) => f.open[k].checked) || 'ask';
    if (open !== cfg.open) changes.open = open;
    if (f.chime.checked !== !!cfg.chime) changes.chime = f.chime.checked;
    let ok = true;
    if (Object.keys(changes).length) {
      try {
        const merged = await api.put('config', changes);
        if (merged && typeof merged === 'object') S.config = merged;
        else Object.assign(S.config, changes);
      } catch (e) {
        Object.assign(S.config, changes);
        fail(e, false, 'Settings');
        ok = false;
      }
      applyWallpaper(S.config);
      Search.refresh();
    }
    const routing = String(st.routing || 'auto').toLowerCase();
    const model = f.model.value;
    let cmd = null;
    if (f.manual.checked && model && (routing !== 'manual' || model !== (st.task_model || st.model))) cmd = '/use ' + model;
    else if (f.auto.checked && routing !== 'auto') cmd = '/auto';
    if (cmd) {
      try { await api.post('turn', { text: cmd }); Status.note('Sent ' + cmd); }
      catch (e) { fail(e, false, 'Settings'); ok = false; }
    }
    return ok;
  },
};
WM.register('settings', () => Settings.create());

// ---------------------------------------------------------------- Clock

const Clock = {
  timer: null,
  open() { return WM.open('clock'); },
  create() {
    const w = WM.create({ name: 'clock', title: 'Clock', icon: 'clock', w: 170, h: 96, x: 12, y: Math.max(20, WM.desk.clientHeight - 170), pad: false,
      onClose: () => clearInterval(this.timer) });
    const time = el('div', { class: 'clock-time' });
    const date = el('div', { class: 'clock-date' });
    w.body.append(time, date);
    const tick = () => {
      const d = new Date();
      time.textContent = d.toLocaleTimeString('en-US');
      date.textContent = d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    };
    tick();
    clearInterval(this.timer);
    this.timer = setInterval(tick, 1000);
    return w;
  },
};
WM.register('clock', () => Clock.create());

// ---------------------------------------------------------------- Confirm

const Confirm = {
  async ask(ev) {
    const name = 'confirm:' + ev.id;
    const answer = await msgBox({ name, title: 'TZ', icon: '?', text: ev.question || 'Continue?', buttons: ['Yes', 'No'] });
    if (answer === null) return; // closed by confirm_done
    try { await api.post('confirm', { id: ev.id, answer: answer === 'Yes' }); }
    catch (e) { fail(e, true); }
  },
  done(ev) {
    const w = WM.wins.get('confirm:' + ev.id);
    if (w) w.close();
  },
};
Events.on('confirm', (ev) => Confirm.ask(ev));
Events.on('confirm_done', (ev) => Confirm.done(ev));

// ---------------------------------------------------------------- Program Manager menus / About

function about() {
  const st = S.state;
  msgBox({
    title: 'About Program Manager', icon: 'i',
    text: 'TZ desktop · version ' + ((st && st.version) || '?') + ' · local only\n\n' +
      ((st && st.label) ? st.label + ' · ' + st.model + ' · ' + String(st.routing || '').toUpperCase() : 'agent offline'),
  });
}

const ProgMan = {
  init() {
    const menus = {
      file: () => [
        { label: 'Open', disabled: !Icons.grid.current(), action: () => { const c = Icons.grid.current(); c && WM.open(c.id); } },
        { label: 'New…', disabled: true },
        '-',
        { label: 'Exit Windows…', action: () => msgBox({ title: 'Exit Windows', icon: 'i', text: 'This is a browser tab. Close it, or type /ui close in the terminal.' }) },
      ],
      options: () => [
        { label: 'Auto Arrange', action: () => Icons.arrange(true) },
        { label: 'Reset window positions', action: () => { for (const k of Object.keys(localStorage)) if (k.startsWith('tz.win.')) localStorage.removeItem(k); Status.note('Window positions reset'); } },
        { label: 'Save Settings on Exit', disabled: true },
      ],
      window: () => {
        const items = [
          { label: 'Cascade', action: () => WM.cascade() },
          { label: 'Tile', action: () => WM.tile() },
          '-',
        ];
        let n = 1;
        for (const w of WM.wins.values()) if (!w.opts.dialog) items.push({ label: (n++) + ' ' + w.opts.title, action: () => { w.restore(); w.raise(); } });
        if (n === 1) items.push({ label: '(no windows)', disabled: true });
        return items;
      },
      help: () => [
        { label: 'Contents', action: () => msgBox({ title: 'Help', icon: 'i', text: 'Double-click an icon to open it.\nDrag windows by their title bar; drag the corner to resize.\n▼ minimizes to an icon, ▲ maximizes.\nType in Start or Chat to talk to TZ.' }) },
        '-',
        { label: 'About Program Manager…', action: about },
      ],
    };
    for (const item of document.querySelectorAll('#pm-menubar .menu-item')) {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        if (item.classList.contains('open')) { Popup.hide(); return; }
        const r = item.getBoundingClientRect();
        Popup.show(r.left, r.bottom, menus[item.dataset.menu]());
        item.classList.add('open');
      });
    }
    $('#pm-sysmenu').addEventListener('click', (e) => {
      e.stopPropagation();
      const r = e.currentTarget.getBoundingClientRect();
      Popup.show(r.left, r.bottom, [
        { label: 'Restore', disabled: true }, { label: 'Move', disabled: true }, { label: 'Size', disabled: true },
        { label: 'Minimize', disabled: true }, { label: 'Maximize', disabled: true }, '-',
        { label: 'Close        Alt+F4', action: () => menus.file()[3].action() },
        '-', { label: 'Switch To…', disabled: true },
      ]);
    });
    $('#pm-min').addEventListener('click', () => Status.note('The Program Manager is the desktop.'));
    $('#pm-max').addEventListener('click', () => Status.note('Already maximized.'));

    document.addEventListener('pointerdown', (e) => { if (!e.target.closest('.popup, .menu-item, .sysmenu')) Popup.hide(); }, true);
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (Popup.el) { Popup.hide(); return; }
      const w = WM.active;
      if (w && w.opts.dialog) { if (w.answered) w.answered(); w.close(); }
    });
  },
};

// ---------------------------------------------------------------- StatusStrip

const Status = {
  data: {},
  noteTimer: null,
  update(ev) {
    for (const k of ['model', 'routing', 'label', 'session_id', 'readings']) if (ev[k] !== undefined) this.data[k] = ev[k];
    this.render();
  },
  render() {
    const d = this.data;
    const parts = [d.model, d.routing && String(d.routing).toUpperCase(), d.label, d.session_id].filter(Boolean);
    const left = $('#status-left');
    left.textContent = '';
    if (!S.online) left.append(el('span', { class: 'off', text: '[offline]' }), parts.length ? ' · ' : '');
    left.append(parts.join(' · '));
    if (!this.noteTimer) $('#status-right').textContent = d.readings || '';
  },
  note(text) {
    clearTimeout(this.noteTimer);
    $('#status-right').textContent = text;
    this.noteTimer = setTimeout(() => { this.noteTimer = null; this.render(); }, 4000);
  },
};
Events.on('hello', (ev) => {
  S.state = ev;
  Status.update(ev);
  Start.render();
  loadConfig();
  if (WM.wins.get('chat')) Chat.load();
});
Events.on('status', (ev) => Status.update(ev));

// ---------------------------------------------------------------- boot()

async function loadConfig() {
  try {
    const cfg = await api.get('config');
    if (cfg && typeof cfg === 'object') S.config = Object.assign(S.config, cfg);
  } catch (e) { /* offline: keep defaults */ }
  applyWallpaper(S.config);
  Search.refresh();
}

async function boot() {
  WM.init();
  Icons.init();
  ProgMan.init();
  Status.render();
  // window placement needs a real viewport (embedded browsers can start at 0x0)
  for (let i = 0; i < 120 && (!innerWidth || !innerHeight || !WM.desk.clientHeight); i++) await new Promise(requestAnimationFrame);
  Clock.open();
  WM.desk.focus();

  const cfgLoad = loadConfig();
  await Boot.run();
  if (S.state) Status.update(S.state);
  Events.connect();
  await cfgLoad;
  Start.open();
  if (S.config.chime) chime();
}

addEventListener('load', boot);
