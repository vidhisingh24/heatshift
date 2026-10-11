(function () {
  "use strict";

  var T = window.I18N;
  var LEVELS = ["safe", "caution", "danger", "extreme"];
  var WORK_DAY = [5, 21];
  var CITY_TZ = "Asia/Kolkata";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var ROLE_ORDER = ["vendor", "rider", "construction"];
  var LEVEL_TINT = { safe: "#e9f2ec", caution: "#fbf3e0", danger: "#f9ebe3", extreme: "#f4e6e4" };
  var MODEL_NAMES = {
    "amazon.nova-lite-v1:0": "Amazon Nova Lite",
    "amazon.nova-micro-v1:0": "Amazon Nova Micro",
    "amazon.nova-pro-v1:0": "Amazon Nova Pro",
  };

  var $ = function (id) { return document.getElementById(id); };

  // from/to: optional work hours (-1 = not set). lat/lon: optional, kept only in this browser.
  var state = { role: "rider", lang: "en", city: "delhi", date: "2024-06-18", from: -1, to: -1, lat: null, lon: null };
  var options = null;
  var plan = null;
  var requestId = 0;

  // ---------- helpers ----------

  function fill(str, vars) {
    return String(str).replace(/\{(\w+)\}/g, function (_, k) {
      return vars && vars[k] !== undefined ? vars[k] : "";
    });
  }
  function t(key) { return T[state.lang][key]; }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function svgEl(tag, attrs) {
    var e = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function icon(id, cls) {
    var s = svgEl("svg", { "aria-hidden": "true", "class": cls || "ico" });
    var u = svgEl("use", { href: "#" + id });
    s.appendChild(u);
    return s;
  }
  function levelIcon(level) { return icon("i-" + level, "lv-" + level); }
  function store(key, value) { try { localStorage.setItem("heatshift." + key, value); } catch (e) { /* blocked */ } }
  function recall(key) { try { return localStorage.getItem("heatshift." + key); } catch (e) { return null; } }
  function locale() { return state.lang === "hi" ? "hi-IN" : "en-IN"; }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function hhmm(h) { return pad(h % 24) + ":00"; }

  function formatDate(iso) {
    var d = new Date(iso + "T12:00:00+05:30");
    return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: "numeric", timeZone: CITY_TZ }).format(d);
  }
  function formatStamp(iso) {
    return new Intl.DateTimeFormat(locale(), {
      day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: CITY_TZ,
    }).format(new Date(iso)) + " IST";
  }
  function cityToday() { return new Intl.DateTimeFormat("en-CA", { timeZone: CITY_TZ }).format(new Date()); }
  function cityHour() {
    return parseInt(new Intl.DateTimeFormat("en-GB", { hour: "2-digit", hourCycle: "h23", timeZone: CITY_TZ }).format(new Date()), 10);
  }
  function nowHour() { return plan && plan.date === cityToday() ? cityHour() : -1; }

  function windowsText(windows) {
    if (!windows.length) return t("avoid_none");
    return windows.map(function (w) { return hhmm(w[0]) + "–" + hhmm(w[1]); }).join(state.lang === "hi" ? " और " : ", ");
  }
  function hasShift() { return state.from >= 0 && state.to > state.from; }
  function inShift(h) { return hasShift() && h >= state.from && h < state.to; }
  function groupHours(hrs) {
    var out = [];
    hrs.forEach(function (h) {
      var last = out[out.length - 1];
      if (last && last[1] === h) last[1] = h + 1; else out.push([h, h + 1]);
    });
    return out;
  }
  function saveProfile() {
    store("profile", JSON.stringify({ role: state.role, city: state.city, lang: state.lang, from: state.from, to: state.to }));
  }
  function loadProfile() {
    try {
      var p = JSON.parse(recall("profile") || "null");
      if (p) {
        if (ROLE_ORDER.indexOf(p.role) >= 0) state.role = p.role;
        if (p.lang === "en" || p.lang === "hi") state.lang = p.lang;
        if (p.city) state.city = p.city;
        if (typeof p.from === "number") state.from = p.from;
        if (typeof p.to === "number") state.to = p.to;
      }
      var loc = JSON.parse(recall("loc") || "null");
      if (loc && typeof loc.lat === "number") { state.lat = loc.lat; state.lon = loc.lon; }
      return !!p;
    } catch (e) { return false; }
  }

  function actionText(h) {
    if (h.avoid) return h.avoid_action === "shade" ? t("do_shade") : t("do_stop");
    if (h.rest_min) return fill(t("do_rest"), { m: h.rest_min });
    return t("do_work");
  }

  // ---------- data shown before /api/options arrives ----------

  function cityList() {
    return options ? options.cities : {
      delhi: {
        name_en: "Delhi", name_hi: "दिल्ली",
        replay_days: [
          { date: "2024-06-18", label_en: "18 Jun 2024 (humid)", label_hi: "18 जून 2024 (उमस)" },
          { date: "2024-05-29", label_en: "29 May 2024 (dry, 46°C)", label_hi: "29 मई 2024 (सूखी, 46°C)" },
        ],
      },
    };
  }
  function roleList() {
    return options ? options.roles : {
      vendor: { name_en: "Street vendor", name_hi: "रेहड़ी-पटरी विक्रेता" },
      rider: { name_en: "Delivery rider", name_hi: "डिलीवरी राइडर" },
      construction: { name_en: "Construction worker", name_hi: "निर्माण मज़दूर" },
    };
  }
  function currentCity() {
    var cities = cityList();
    return cities[state.city] || cities[Object.keys(cities)[0]];
  }

  // ---------- static text & controls ----------

  function applyText() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-t]").forEach(function (node) {
      var v = t(node.getAttribute("data-t"));
      if (typeof v === "string") node.textContent = v;
    });
    document.querySelectorAll(".lang button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-lang") === state.lang));
    });
    renderRoles();
    renderCities();
    renderDays();
    renderHourSelects();
    renderSetup();
    document.dispatchEvent(new CustomEvent("hs:lang"));
  }

  function hourOptions(sel, first, last, value) {
    sel.textContent = "";
    var none = el("option", "", t("any_hours"));
    none.value = "-1";
    sel.appendChild(none);
    for (var h = first; h <= last; h++) {
      var o = el("option", "", hhmm(h));
      o.value = String(h);
      sel.appendChild(o);
    }
    sel.value = String(value);
  }

  function renderHourSelects() {
    hourOptions($("from-hour"), 0, 23, state.from);
    hourOptions($("to-hour"), 1, 24, state.to);
    hourOptions($("setup-from"), 0, 23, state.from);
    hourOptions($("setup-to"), 1, 24, state.to);
  }

  // ---------- first-visit setup ----------

  function renderSetup() {
    document.querySelectorAll("[data-setup-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-setup-lang") === state.lang));
    });
    var box = $("setup-roles");
    var roles = roleList();
    box.textContent = "";
    ROLE_ORDER.forEach(function (key) {
      var b = el("button", "big-choice role-choice");
      b.type = "button";
      b.setAttribute("aria-pressed", String(key === state.role));
      b.appendChild(icon("i-" + key));
      b.appendChild(el("span", "", roles[key]["name_" + state.lang]));
      b.addEventListener("click", function () { state.role = key; renderSetup(); });
      box.appendChild(b);
    });
    var sel = $("setup-city");
    sel.textContent = "";
    var cities = cityList();
    Object.keys(cities).sort(function (a, b) { return a === "delhi" ? -1 : b === "delhi" ? 1 : a < b ? -1 : 1; })
      .forEach(function (key) {
        var o = el("option", "", cities[key]["name_" + state.lang]);
        o.value = key;
        sel.appendChild(o);
      });
    sel.value = state.city;
  }

  function showSetup(show) {
    $("setup").hidden = !show;
    $("main").hidden = show;
    $("change-setup").hidden = show;
    if (show) { renderSetup(); window.scrollTo(0, 0); }
  }

  function nearestCity(lat, lon) {
    var cities = cityList(), best = null, bestD = Infinity;
    Object.keys(cities).forEach(function (k) {
      var c = cities[k];
      if (typeof c.lat !== "number") return;
      var d = Math.pow(c.lat - lat, 2) + Math.pow((c.lon - lon) * Math.cos(lat * Math.PI / 180), 2);
      if (d < bestD) { bestD = d; best = k; }
    });
    return best;
  }

  function locate(statusEl, done) {
    if (!navigator.geolocation) { statusEl.textContent = t("location_failed"); return; }
    statusEl.textContent = t("locating");
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = Math.round(pos.coords.latitude * 10000) / 10000;
      state.lon = Math.round(pos.coords.longitude * 10000) / 10000;
      store("loc", JSON.stringify({ lat: state.lat, lon: state.lon }));
      var near = nearestCity(state.lat, state.lon);
      if (near) state.city = near;
      statusEl.textContent = fill(t("location_done"), { city: cityList()[state.city]["name_" + state.lang] });
      if (done) done();
    }, function () {
      statusEl.textContent = t("location_failed");
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  }

  function renderRoles() {
    var box = $("roles");
    var roles = roleList();
    box.textContent = "";
    ROLE_ORDER.forEach(function (key) {
      if (!roles[key]) return;
      var b = el("button", "role");
      b.type = "button";
      b.setAttribute("aria-pressed", String(key === state.role));
      b.appendChild(icon("i-" + key));
      b.appendChild(el("span", "", roles[key]["name_" + state.lang]));
      b.addEventListener("click", function () {
        if (state.role === key) return;
        state.role = key;
        saveProfile();
        renderRoles();
        load();
      });
      box.appendChild(b);
    });
  }

  function renderCities() {
    var sel = $("city");
    var cities = cityList();
    sel.textContent = "";
    Object.keys(cities).sort(function (a, b) { return a === "delhi" ? -1 : b === "delhi" ? 1 : a < b ? -1 : 1; })
      .forEach(function (key) {
        var o = el("option", "", cities[key]["name_" + state.lang]);
        o.value = key;
        o.selected = key === state.city;
        sel.appendChild(o);
      });
  }

  function renderDays() {
    var sel = $("day");
    var city = currentCity();
    sel.textContent = "";
    var found = state.date === "";
    (city.replay_days || []).forEach(function (d) {
      var o = el("option", "", fill(t("replay"), { label: d["label_" + state.lang] }));
      o.value = d.date;
      if (d.date === state.date) found = true;
      sel.appendChild(o);
    });
    var today = el("option", "", t("today"));
    today.value = "";
    sel.appendChild(today);
    if (!found) {
      var c = el("option", "", state.date);
      c.value = state.date;
      sel.appendChild(c);
    }
    sel.value = state.date;
    var note = $("replay-note");
    note.hidden = state.date === "";
    note.textContent = fill(t("replay_note"), { city: city["name_" + state.lang] });
  }

  // ---------- loading ----------

  function syncUrl() {
    var p = new URLSearchParams();
    p.set("role", state.role);
    p.set("lang", state.lang);
    if (state.city !== "delhi") p.set("city", state.city);
    p.set("date", state.date || "today");
    history.replaceState(null, "", "?" + p.toString());
  }

  function load() {
    stopSpeaking();
    syncUrl();
    var id = ++requestId;
    $("loading").hidden = false;
    $("error").hidden = true;
    $("plan").setAttribute("aria-busy", "true");
    var q = "city=" + encodeURIComponent(state.city) + "&role=" + encodeURIComponent(state.role) +
      "&lang=" + encodeURIComponent(state.lang) + (state.date ? "&date=" + encodeURIComponent(state.date) : "");

    fetch("/api/plan?" + q)
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (data) {
        if (id !== requestId) return;
        plan = data;
        $("loading").hidden = true;
        $("plan").hidden = false;
        $("plan").removeAttribute("aria-busy");
        render();
      })
      .catch(function () {
        if (id !== requestId) return;
        $("loading").hidden = true;
        $("plan").hidden = true;
        $("error").hidden = false;
      });
  }

  // ---------- rendering ----------

  function render() {
    renderOverview();
    renderAdvice();
    renderShift();
    renderChart();
    renderTable();
    renderLegend();
    $("data-source").textContent = plan.data_source;
    $("updated").textContent = formatStamp(plan.data_fetched_at);
    $("print-title").textContent = fill(t("print_title"), { role: plan.role_name, city: plan.city_name, date: formatDate(plan.date) });
    document.dispatchEvent(new CustomEvent("hs:plan"));
  }

  function renderOverview() {
    var s = plan.summary;
    var lv = s.worst_level;
    $("meta-line").textContent = fill(t("meta"), { role: plan.role_name, city: plan.city_name, date: formatDate(plan.date) });
    $("mode-badge").textContent = t("modes")[plan.mode];

    var pill = $("level-pill");
    pill.textContent = "";
    pill.setAttribute("data-level", lv);
    pill.appendChild(levelIcon(lv));
    pill.appendChild(el("span", "", t("levels")[lv]));

    $("hero-temp").textContent = Math.round(s.peak_heat_index_c);
    $("hero-caption").textContent = fill(t("hero_caption"), {
      time: s.peak_time, temp: Math.round(s.peak_air_c), rh: s.peak_rh,
    });

    // One-line rule: "Avoid 12:00–16:00. Best: 05:00–08:00, 18:00–22:00."
    var avoid = s.avoid_windows.length ? windowsText(s.avoid_windows) : "";
    var best = s.best_windows.length ? windowsText(s.best_windows) : "";
    $("rule-line").textContent = avoid && best ? fill(t("rule_avoid_best"), { avoid: avoid, best: best })
      : avoid ? fill(t("rule_avoid_only"), { avoid: avoid })
      : fill(t("rule_best_only"), { best: best || "05:00–22:00" });

    // Danger hours inside the worker's own shift
    var warn = $("shift-warning");
    if (hasShift()) {
      var shift = hhmm(state.from) + "–" + hhmm(state.to);
      var bad = plan.hours.filter(function (h) {
        return inShift(h.hour) && LEVELS.indexOf(h.level) >= 2;
      }).map(function (h) { return h.hour; });
      warn.hidden = false;
      warn.classList.toggle("is-ok", !bad.length);
      warn.textContent = bad.length
        ? fill(t("shift_warning"), { shift: shift, n: bad.length, w: windowsText(groupHours(bad)) })
        : fill(t("shift_ok"), { shift: shift });
    } else {
      warn.hidden = true;
    }

    renderDayBar();

    $("avoid-label").textContent = t("avoid_label")[plan.role];
    $("avoid-value").textContent = windowsText(s.avoid_windows);
    $("rest-value").textContent = s.max_rest_min ? fill(t("min"), { m: s.max_rest_min }) : t("none");
    $("water-value").textContent = fill(t("every_min"), { m: s.min_water_every_min });
  }

  function renderDayBar() {
    var bar = $("day-bar");
    var axis = $("day-axis");
    var nh = nowHour();
    bar.textContent = "";
    axis.textContent = "";
    bar.setAttribute("aria-label", t("day_bar_label") + ": " + plan.hours.map(function (h) {
      return h.time + " " + t("levels")[h.level];
    }).join(", "));
    plan.hours.forEach(function (h) {
      var c = el("span", "fill-" + h.level + (h.hour === nh ? " is-now" : "") + (inShift(h.hour) ? " in-shift" : ""));
      c.title = h.time + " · " + t("levels")[h.level] + " · " + Math.round(h.heat_index_c) + "°C";
      if (h.hour === nh) c.appendChild(el("i", "now-tag", t("now")));
      bar.appendChild(c);
    });
    [0, 6, 12, 18, 24].forEach(function (h) {
      var tick = el("span", "", pad(h));
      tick.style.left = (h / 24 * 100) + "%";
      axis.appendChild(tick);
    });
  }

  function renderAdvice() {
    $("message").textContent = plan.message;
    $("message").lang = plan.lang;
    var chip = $("message-chip");
    if (plan.message_source.indexOf("bedrock:") === 0) {
      var id = plan.message_source.slice(8);
      chip.textContent = t("chip_ai");
      chip.classList.add("is-ai");
      $("message-source").textContent = fill(t("src_bedrock"), { model: MODEL_NAMES[id] || id });
    } else {
      chip.textContent = t("chip_template");
      chip.classList.remove("is-ai");
      $("message-source").textContent = t("src_template");
    }
    var text = fill(t("share_text"), {
      role: plan.role_name, city: plan.city_name, date: formatDate(plan.date), message: plan.message, url: location.href,
    });
    $("share").href = "https://wa.me/?text=" + encodeURIComponent(text);
    $("share").className = "btn btn-primary";
  }

  // Group the working day into blocks with the same instruction.
  function segments() {
    var out = [];
    plan.hours.forEach(function (h) {
      if (h.hour < WORK_DAY[0] || h.hour > WORK_DAY[1]) return;
      var key = h.avoid ? h.avoid_action : (h.rest_min ? "rest" + h.rest_min : "work");
      var last = out[out.length - 1];
      if (last && last.key === key && last.end === h.hour) {
        last.end = h.hour + 1;
        if (LEVELS.indexOf(h.level) > LEVELS.indexOf(last.level)) last.level = h.level;
        last.maxHi = Math.max(last.maxHi, h.heat_index_c);
        last.water = Math.min(last.water, h.water_every_min);
      } else {
        out.push({ key: key, start: h.hour, end: h.hour + 1, level: h.level, maxHi: h.heat_index_c,
          water: h.water_every_min, rest: h.rest_min, avoid: h.avoid, action: h.avoid_action });
      }
    });
    return out;
  }

  function renderShift() {
    var segs = segments();
    var span = WORK_DAY[1] + 1 - WORK_DAY[0];
    var bar = $("shift-bar");
    var axis = $("shift-axis");
    var list = $("segments");
    bar.textContent = "";
    axis.textContent = "";
    list.textContent = "";

    segs.forEach(function (s) {
      var part = el("span", s.avoid ? "fill-stop" : "fill-" + s.level);
      part.style.flex = String(s.end - s.start);
      bar.appendChild(part);

      var li = el("li", "segment" + (s.avoid ? " is-stop" : ""));
      li.appendChild(el("span", "segment-time", hhmm(s.start) + "–" + hhmm(s.end)));
      var body = el("div");
      var title = el("p", "segment-title");
      var sw = el("span", "swatch " + (s.avoid ? "fill-stop" : "fill-" + s.level));
      title.appendChild(sw);
      var label = s.avoid ? (s.action === "shade" ? t("seg_shade") : t("seg_stop"))
        : s.rest ? fill(t("seg_rest"), { m: s.rest }) : t("seg_work");
      title.appendChild(document.createTextNode(label));
      body.appendChild(title);
      body.appendChild(el("p", "fine", fill(t("seg_detail"), {
        level: t("levels")[s.level], hi: Math.round(s.maxHi), w: s.water,
      })));
      li.appendChild(body);
      list.appendChild(li);
    });

    [WORK_DAY[0], 9, 13, 17, WORK_DAY[1] + 1].forEach(function (h) {
      var tick = el("span", "", hhmm(h));
      tick.style.left = ((h - WORK_DAY[0]) / span * 100) + "%";
      axis.appendChild(tick);
    });
  }

  // ---------- chart ----------

  function renderChart() {
    var box = $("chart");
    var svg = $("chart-svg");
    var tip = $("tooltip");
    var W = box.clientWidth;
    var H = box.clientHeight;
    if (!W || !H) return;
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    tip.hidden = true;

    var hours = plan.hours;
    var cut = plan.cutoffs_c;
    var m = { l: 34, r: W < 480 ? 12 : 72, t: 22, b: 26 };
    var iw = W - m.l - m.r;
    var ih = H - m.t - m.b;

    var vals = [];
    hours.forEach(function (h) { vals.push(h.heat_index_c, h.temp_c); });
    var lo = Math.floor((Math.min.apply(null, vals) - 2) / 5) * 5;
    var hi = Math.ceil((Math.max.apply(null, vals) + 3) / 5) * 5;
    var n = hours.length;
    var x = function (i) { return m.l + (n === 1 ? iw / 2 : (i / (n - 1)) * iw); };
    var y = function (v) { return m.t + ih - ((v - lo) / (hi - lo)) * ih; };

    // pattern for stop windows
    var defs = svgEl("defs");
    var pat = svgEl("pattern", { id: "stop-hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
    pat.appendChild(svgEl("rect", { width: 6, height: 6, fill: "rgba(23,22,20,0.035)" }));
    pat.appendChild(svgEl("rect", { width: 2, height: 6, fill: "rgba(23,22,20,0.13)" }));
    defs.appendChild(pat);
    svg.appendChild(defs);

    // level bands
    var bands = [
      { lv: "safe", a: -100, b: cut.caution },
      { lv: "caution", a: cut.caution, b: cut.danger },
      { lv: "danger", a: cut.danger, b: cut.extreme },
      { lv: "extreme", a: cut.extreme, b: 200 },
    ];
    var gBands = svgEl("g");
    bands.forEach(function (bd) {
      var a = Math.max(bd.a, lo), b = Math.min(bd.b, hi);
      if (b <= a) return;
      gBands.appendChild(svgEl("rect", { x: m.l, y: y(b), width: iw, height: y(a) - y(b), fill: LEVEL_TINT[bd.lv] }));
      if (m.r > 40 && y(a) - y(b) > 16) {
        var lab = svgEl("text", { x: m.l + iw + 10, y: (y(a) + y(b)) / 2 + 4, "class": "band-label" });
        lab.textContent = t("levels")[bd.lv];
        gBands.appendChild(lab);
      }
    });
    svg.appendChild(gBands);

    // stop windows (any contiguous avoided hours)
    var gStop = svgEl("g");
    var i = 0;
    while (i < n) {
      if (hours[i].avoid) {
        var j = i;
        while (j + 1 < n && hours[j + 1].avoid) j++;
        var x0 = x(i) - (i > 0 ? iw / (n - 1) / 2 : 0);
        var x1 = x(j) + (j < n - 1 ? iw / (n - 1) / 2 : 0);
        gStop.appendChild(svgEl("rect", { x: x0, y: m.t, width: x1 - x0, height: ih, fill: "url(#stop-hatch)" }));
        var sl = svgEl("text", { x: (x0 + x1) / 2, y: m.t - 7, "text-anchor": "middle", "class": "stop-label" });
        sl.textContent = t("series_stop");
        gStop.appendChild(sl);
        i = j + 1;
      } else i++;
    }
    svg.appendChild(gStop);

    // grid + y axis
    var gGrid = svgEl("g", { "class": "grid" });
    var gAxis = svgEl("g", { "class": "axis" });
    for (var v = lo; v <= hi; v += 5) {
      gGrid.appendChild(svgEl("line", { x1: m.l, x2: m.l + iw, y1: y(v), y2: y(v) }));
      var tl = svgEl("text", { x: m.l - 8, y: y(v) + 4, "text-anchor": "end" });
      tl.textContent = v + "°";
      gAxis.appendChild(tl);
    }
    var step = W < 480 ? 6 : 3;
    hours.forEach(function (h, k) {
      if (h.hour % step !== 0) return;
      var xl = svgEl("text", { x: x(k), y: H - 6, "text-anchor": "middle" });
      xl.textContent = pad(h.hour);
      gAxis.appendChild(xl);
    });
    svg.appendChild(gGrid);
    svg.appendChild(gAxis);

    // now marker
    var nh = nowHour();
    if (nh >= 0) {
      var ni = hours.findIndex(function (h) { return h.hour === nh; });
      if (ni >= 0) {
        svg.appendChild(svgEl("line", { x1: x(ni), x2: x(ni), y1: m.t, y2: m.t + ih, stroke: "#171614", "stroke-width": 1 }));
        var nl = svgEl("text", { x: x(ni) + 4, y: m.t + 12, "class": "stop-label" });
        nl.textContent = t("now");
        svg.appendChild(nl);
      }
    }

    // lines
    function path(key) {
      return hours.map(function (h, k) { return (k ? "L" : "M") + x(k).toFixed(1) + " " + y(h[key]).toFixed(1); }).join(" ");
    }
    svg.appendChild(svgEl("path", { d: path("temp_c"), fill: "none", stroke: "#a39d93", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    svg.appendChild(svgEl("path", { d: path("heat_index_c"), fill: "none", stroke: "#171614", "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));

    // peak marker + label
    var pk = 0;
    hours.forEach(function (h, k) { if (h.heat_index_c > hours[pk].heat_index_c) pk = k; });
    svg.appendChild(svgEl("circle", { cx: x(pk), cy: y(hours[pk].heat_index_c), r: 5, fill: "#171614", stroke: "#fff", "stroke-width": 2 }));
    var pl = svgEl("text", { x: Math.min(Math.max(x(pk), m.l + 30), m.l + iw - 30), y: y(hours[pk].heat_index_c) - 12, "text-anchor": "middle", "class": "peak-label" });
    pl.textContent = Math.round(hours[pk].heat_index_c) + "° · " + hours[pk].time;
    svg.appendChild(pl);

    // hover layer
    var cross = svgEl("line", { y1: m.t, y2: m.t + ih, stroke: "#171614", "stroke-width": 1, opacity: 0 });
    var dotHi = svgEl("circle", { r: 4.5, fill: "#171614", stroke: "#fff", "stroke-width": 2, opacity: 0 });
    var dotAir = svgEl("circle", { r: 4, fill: "#a39d93", stroke: "#fff", "stroke-width": 2, opacity: 0 });
    svg.appendChild(cross);
    svg.appendChild(dotAir);
    svg.appendChild(dotHi);
    var hit = svgEl("rect", { x: m.l, y: 0, width: iw, height: H, fill: "transparent" });
    svg.appendChild(hit);

    function show(evt) {
      var rect = svg.getBoundingClientRect();
      var px = evt.clientX - rect.left;
      var k = Math.round(((px - m.l) / iw) * (n - 1));
      k = Math.max(0, Math.min(n - 1, k));
      var h = hours[k];
      cross.setAttribute("x1", x(k)); cross.setAttribute("x2", x(k)); cross.setAttribute("opacity", 0.35);
      dotHi.setAttribute("cx", x(k)); dotHi.setAttribute("cy", y(h.heat_index_c)); dotHi.setAttribute("opacity", 1);
      dotAir.setAttribute("cx", x(k)); dotAir.setAttribute("cy", y(h.temp_c)); dotAir.setAttribute("opacity", 1);

      tip.textContent = "";
      var head = el("div", "tt-time");
      head.appendChild(el("span", "", h.time));
      var lvl = el("span", "lvl");
      lvl.appendChild(levelIcon(h.level));
      lvl.appendChild(el("span", "", t("levels")[h.level]));
      head.appendChild(lvl);
      tip.appendChild(head);
      [[t("tip_feels"), Math.round(h.heat_index_c) + "°C"], [t("tip_air"), h.temp_c + "°C"], [t("tip_rh"), h.rh + "%"]]
        .forEach(function (r) {
          var row = el("div", "tt-row");
          row.appendChild(el("span", "", r[0]));
          row.appendChild(el("b", "", r[1]));
          tip.appendChild(row);
        });
      tip.appendChild(el("div", "tt-do", actionText(h) + " · " + fill(t("water_short"), { m: h.water_every_min })));
      tip.hidden = false;
      var tw = tip.offsetWidth;
      var left = x(k) + 14;
      if (left + tw > W) left = x(k) - tw - 14;
      tip.style.left = Math.max(0, left) + "px";
    }
    function hide() {
      tip.hidden = true;
      [cross, dotHi, dotAir].forEach(function (e) { e.setAttribute("opacity", 0); });
    }
    hit.addEventListener("pointermove", show);
    hit.addEventListener("pointerdown", show);
    hit.addEventListener("pointerleave", hide);

    $("chart-desc").textContent = fill(t("chart_desc"), { hi: Math.round(hours[pk].heat_index_c), time: hours[pk].time });
  }

  function renderTable() {
    var body = $("hours-body");
    var nh = nowHour();
    body.textContent = "";
    plan.hours.forEach(function (h) {
      var tr = el("tr", h.hour === nh ? "is-now" : "");
      tr.appendChild(el("td", "", h.time));
      var lv = el("td");
      var span = el("span", "lvl");
      span.appendChild(levelIcon(h.level));
      span.appendChild(el("span", "", t("levels")[h.level]));
      lv.appendChild(span);
      tr.appendChild(lv);
      tr.appendChild(el("td", "num", Math.round(h.heat_index_c) + "°"));
      tr.appendChild(el("td", "num", h.temp_c + "°"));
      tr.appendChild(el("td", "num", h.rh + "%"));
      tr.appendChild(el("td", "", actionText(h) + " · " + fill(t("water_short"), { m: h.water_every_min })));
      body.appendChild(tr);
    });
  }

  function renderLegend() {
    var c = plan.cutoffs_c;
    var ranges = t("legend_range");
    var vals = {
      safe: { a: c.caution }, caution: { a: c.caution, b: c.danger },
      danger: { a: c.danger, b: c.extreme }, extreme: { a: c.extreme },
    };
    var list = $("legend-list");
    list.textContent = "";
    LEVELS.forEach(function (lv) {
      var li = el("li");
      li.appendChild(levelIcon(lv));
      li.appendChild(el("strong", "", t("levels")[lv]));
      li.appendChild(el("span", "range", fill(ranges[lv], vals[lv])));
      list.appendChild(li);
    });
  }

  // ---------- listen ----------

  var synth = window.speechSynthesis;
  function stopSpeaking() {
    if (synth) synth.cancel();
    $("listen").setAttribute("aria-pressed", "false");
    $("listen-text").textContent = t("listen");
  }
  function speak() {
    if (!synth || !plan) return;
    if (synth.speaking) { stopSpeaking(); return; }
    var u = new SpeechSynthesisUtterance(plan.message);
    u.lang = plan.lang === "hi" ? "hi-IN" : "en-IN";
    var voice = synth.getVoices().filter(function (v) { return v.lang && v.lang.indexOf(plan.lang) === 0; })[0];
    if (voice) u.voice = voice;
    u.rate = 0.95;
    u.onend = u.onerror = stopSpeaking;
    $("listen").setAttribute("aria-pressed", "true");
    $("listen-text").textContent = t("stop");
    synth.speak(u);
  }

  // ---------- init ----------

  // Returns true when the setup screen can be skipped (saved profile, or a shared link with a role).
  function readInitialState() {
    var saved = loadProfile();
    var p = new URLSearchParams(location.search);
    var role = p.get("role");
    var lang = p.get("lang");
    var date = p.get("date");
    if (ROLE_ORDER.indexOf(role) >= 0) state.role = role;
    if (lang === "en" || lang === "hi") state.lang = lang;
    if (p.get("city")) state.city = p.get("city");
    if (date === "today") state.date = "";
    else if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) state.date = date;
    return saved || ROLE_ORDER.indexOf(role) >= 0;
  }

  function init() {
    var skipSetup = readInitialState();
    applyText();

    document.querySelectorAll(".lang button").forEach(function (b) {
      b.addEventListener("click", function () {
        var lang = b.getAttribute("data-lang");
        if (lang === state.lang) return;
        state.lang = lang;
        saveProfile();
        applyText();
        if (!$("main").hidden) load();
      });
    });

    // Setup screen
    document.querySelectorAll("[data-setup-lang]").forEach(function (b) {
      b.addEventListener("click", function () { state.lang = b.getAttribute("data-setup-lang"); applyText(); });
    });
    $("setup-city").addEventListener("change", function (e) { state.city = e.target.value; });
    $("setup-from").addEventListener("change", function (e) { state.from = parseInt(e.target.value, 10); });
    $("setup-to").addEventListener("change", function (e) { state.to = parseInt(e.target.value, 10); });
    $("setup-locate").addEventListener("click", function () {
      locate($("setup-locate-status"), function () { $("setup-city").value = state.city; });
    });
    $("setup-done").addEventListener("click", function () {
      var days = currentCity().replay_days || [];
      if (state.date !== "" && days.length && !days.some(function (d) { return d.date === state.date; })) state.date = days[0].date;
      saveProfile();
      applyText();
      showSetup(false);
      load();
    });
    $("change-setup").addEventListener("click", function () { showSetup(true); });

    // Work hours in the sidebar
    function onHours() {
      state.from = parseInt($("from-hour").value, 10);
      state.to = parseInt($("to-hour").value, 10);
      saveProfile();
      if (plan) { renderOverview(); renderShift(); }
    }
    $("from-hour").addEventListener("change", onHours);
    $("to-hour").addEventListener("change", onHours);
    $("day").addEventListener("change", function (e) { state.date = e.target.value; renderDays(); load(); });
    $("city").addEventListener("change", function (e) {
      state.city = e.target.value;
      var days = currentCity().replay_days || [];
      if (state.date !== "" && days.length) state.date = days[0].date;
      saveProfile();
      renderDays();
      load();
    });
    $("retry").addEventListener("click", load);
    $("print").addEventListener("click", function () { window.print(); });

    // Print the hour table too
    var details = document.querySelector(".table-wrap");
    var wasOpen = false;
    window.addEventListener("beforeprint", function () { wasOpen = details.open; details.open = true; });
    window.addEventListener("afterprint", function () { details.open = wasOpen; });

    if (synth && window.SpeechSynthesisUtterance) {
      $("listen").hidden = false;
      $("listen").addEventListener("click", speak);
    }

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { if (plan) renderChart(); }, 120);
    });

    fetch("/api/options")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { if (data) { options = data; renderRoles(); renderCities(); renderDays(); renderSetup(); } })
      .catch(function () { /* built-in defaults are fine */ });

    if (skipSetup) { showSetup(false); load(); } else { showSetup(true); }
  }

  // Shared with trip.js, places.js and chat.js
  window.HS = {
    state: state,
    plan: function () { return plan; },
    t: t, fill: fill, el: el, icon: icon, levelIcon: levelIcon, hhmm: hhmm, pad: pad,
    cityList: cityList, nowHour: nowHour, locate: locate, LEVELS: LEVELS,
  };

  init();
})();
