(function () {
  "use strict";

  var T = window.I18N;
  var LEVELS = ["safe", "caution", "danger", "extreme"];
  var WORK_DAY = [5, 21];
  var CITY_TZ = "Asia/Kolkata";
  var MODEL_NAMES = {
    "amazon.nova-lite-v1:0": "Amazon Nova Lite",
    "amazon.nova-micro-v1:0": "Amazon Nova Micro",
    "amazon.nova-pro-v1:0": "Amazon Nova Pro",
  };

  var $ = function (id) { return document.getElementById(id); };

  var state = {
    role: "rider",
    lang: "en",
    city: "delhi",
    date: "2024-06-18",
    showAll: false,
  };
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

  function store(key, value) {
    try { localStorage.setItem("heatshift." + key, value); } catch (e) { /* storage blocked: ignore */ }
  }

  function recall(key) {
    try { return localStorage.getItem("heatshift." + key); } catch (e) { return null; }
  }

  function locale() { return state.lang === "hi" ? "hi-IN" : "en-IN"; }

  function formatDate(iso) {
    var d = new Date(iso + "T12:00:00+05:30");
    return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: "numeric", timeZone: CITY_TZ }).format(d);
  }

  function formatStamp(iso) {
    var d = new Date(iso);
    return new Intl.DateTimeFormat(locale(), {
      day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: CITY_TZ,
    }).format(d) + " IST";
  }

  function cityToday() {
    return new Intl.DateTimeFormat("en-CA", { timeZone: CITY_TZ }).format(new Date());
  }

  function cityHour() {
    return parseInt(new Intl.DateTimeFormat("en-GB", { hour: "2-digit", hourCycle: "h23", timeZone: CITY_TZ }).format(new Date()), 10);
  }

  function windowsText(windows) {
    if (!windows.length) return t("avoid_none");
    var join = state.lang === "hi" ? " और " : ", ";
    return windows.map(function (w) {
      return pad(w[0]) + ":00–" + pad(w[1]) + ":00";
    }).join(join);
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  // ---------- static text ----------

  function applyText() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-t]").forEach(function (node) {
      var v = t(node.getAttribute("data-t"));
      if (typeof v === "string") node.textContent = v;
    });
    document.querySelectorAll(".lang button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-lang") === state.lang));
    });
    $("toggle-hours").textContent = state.showAll ? t("show_work") : t("show_all");
    renderRoles();
    renderCities();
    renderDays();
  }

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

  function currentCity() {
    var cities = cityList();
    return cities[state.city] || cities[Object.keys(cities)[0]];
  }

  function renderDays() {
    var sel = $("day");
    var city = currentCity();
    sel.textContent = "";
    var found = false;
    (city.replay_days || []).forEach(function (d) {
      var o = el("option", "", fill(t("replay"), { label: d["label_" + state.lang] }));
      o.value = d.date;
      if (d.date === state.date) found = true;
      sel.appendChild(o);
    });
    var today = el("option", "", t("today"));
    today.value = "";
    sel.appendChild(today);
    if (state.date === "") found = true;
    if (!found) {  // a custom date from the URL
      var c = el("option", "", state.date);
      c.value = state.date;
      sel.appendChild(c);
    }
    sel.value = state.date;
    var note = $("replay-note");
    note.hidden = state.date === "";
    note.textContent = fill(t("replay_note"), { city: city["name_" + state.lang] });
  }

  function renderRoles() {
    var box = $("roles");
    box.textContent = "";
    var roles = options ? options.roles : {
      construction: { name_en: "Construction worker", name_hi: "निर्माण मज़दूर" },
      rider: { name_en: "Delivery rider", name_hi: "डिलीवरी राइडर" },
      vendor: { name_en: "Street vendor", name_hi: "रेहड़ी-पटरी विक्रेता" },
    };
    ["vendor", "rider", "construction"].forEach(function (key) {
      if (!roles[key]) return;
      var b = el("button", "", roles[key]["name_" + state.lang]);
      b.type = "button";
      b.setAttribute("aria-pressed", String(key === state.role));
      b.addEventListener("click", function () {
        if (state.role === key) return;
        state.role = key;
        store("role", key);
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
    Object.keys(cities).forEach(function (key) {
      var o = el("option", "", cities[key]["name_" + state.lang]);
      o.value = key;
      o.selected = key === state.city;
      sel.appendChild(o);
    });
  }

  // ---------- plan ----------

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

    var q = "city=" + encodeURIComponent(state.city) +
      "&role=" + encodeURIComponent(state.role) +
      "&lang=" + encodeURIComponent(state.lang) +
      (state.date ? "&date=" + encodeURIComponent(state.date) : "");

    fetch("/api/plan?" + q)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (id !== requestId) return;
        plan = data;
        render();
        $("loading").hidden = true;
        $("plan").hidden = false;
        $("plan").removeAttribute("aria-busy");
      })
      .catch(function () {
        if (id !== requestId) return;
        $("loading").hidden = true;
        $("plan").hidden = true;
        $("error").hidden = false;
      });
  }

  function render() {
    var s = plan.summary;
    var lv = s.worst_level;
    var isToday = plan.date === cityToday();
    var nowHour = isToday ? cityHour() : -1;

    // status band
    $("status").setAttribute("data-level", lv);
    $("status-kicker").textContent = fill(t("kicker"), { city: plan.city_name, date: formatDate(plan.date) });
    $("status-level").textContent = t("levels")[lv];
    $("status-peak").textContent = fill(t("peak"), {
      hi: Math.round(s.peak_heat_index_c), time: s.peak_time, temp: Math.round(s.peak_temp_c),
    });

    var strip = $("strip");
    var axis = $("strip-axis");
    strip.textContent = "";
    axis.textContent = "";
    plan.hours.forEach(function (h) {
      if (h.hour < WORK_DAY[0] || h.hour > WORK_DAY[1]) return;
      var c = el("span", "lv-" + h.level + (h.hour === nowHour ? " now" : ""));
      c.title = h.time + " · " + t("levels")[h.level] + " · " + Math.round(h.heat_index_c) + "°C";
      strip.appendChild(c);
      axis.appendChild(el("span", "", h.hour % 3 === 0 ? pad(h.hour) : ""));
    });

    // stats
    $("avoid-label").textContent = t("avoid_label")[plan.role];
    $("avoid-value").textContent = windowsText(s.avoid_windows);
    $("rest-value").textContent = s.max_rest_min ? fill(t("min"), { m: s.max_rest_min }) : t("none");
    $("water-value").textContent = fill(t("every_min"), { m: s.min_water_every_min });

    // advice
    $("message").textContent = plan.message;
    $("message").lang = plan.lang;
    if (plan.message_source.indexOf("bedrock:") === 0) {
      var id = plan.message_source.slice(8);
      $("message-source").textContent = fill(t("src_bedrock"), { model: MODEL_NAMES[id] || id });
    } else {
      $("message-source").textContent = t("src_template");
    }

    renderHours(nowHour);
    renderLegend();
    renderShare();

    // meta
    $("data-source").textContent = plan.data_source + " · " + t("modes")[plan.mode] + " · " + formatDate(plan.date);
    $("updated").textContent = formatStamp(plan.data_fetched_at);
  }

  function renderHours(nowHour) {
    var list = $("hour-list");
    list.textContent = "";
    plan.hours.forEach(function (h) {
      if (!state.showAll && (h.hour < WORK_DAY[0] || h.hour > WORK_DAY[1])) return;

      var li = el("li", "hour" + (h.avoid ? " avoid" : "") + (h.hour === nowHour ? " is-now" : ""));

      var time = el("span", "hour-time", h.time);
      if (h.hour === nowHour) time.appendChild(el("small", "", t("now")));
      li.appendChild(time);

      var bar = el("span", "bar");
      var pct = Math.max(0.1, Math.min(1, (h.heat_index_c - 15) / 40)) * 100;
      var fillEl = el("span", "bar-fill lv-" + h.level, Math.round(h.heat_index_c) + "°");
      fillEl.style.width = pct.toFixed(1) + "%";
      bar.appendChild(fillEl);
      bar.title = fill("{lv} · air {t}°C · RH {rh}%", { lv: t("levels")[h.level], t: h.temp_c, rh: h.rh });
      li.appendChild(bar);

      var action;
      if (h.avoid) action = h.avoid_action === "shade" ? t("do_shade") : t("do_stop");
      else if (h.rest_min) action = fill(t("do_rest"), { m: h.rest_min });
      else action = t("do_work");

      var doEl = el("span", "hour-do");
      doEl.appendChild(el("strong", "", action));
      doEl.appendChild(el("span", "", t("levels")[h.level] + " · " + fill(t("water_short"), { m: h.water_every_min })));
      li.appendChild(doEl);

      list.appendChild(li);
    });
  }

  function renderLegend() {
    var c = plan.cutoffs_c;
    var ranges = t("legend_range");
    var vals = {
      safe: { a: c.caution },
      caution: { a: c.caution, b: c.danger },
      danger: { a: c.danger, b: c.extreme },
      extreme: { a: c.extreme },
    };
    var list = $("legend-list");
    list.textContent = "";
    LEVELS.forEach(function (lv) {
      var li = el("li");
      li.appendChild(el("i", "lv-" + lv));
      var txt = el("span");
      txt.appendChild(el("strong", "", t("levels")[lv]));
      txt.appendChild(document.createTextNode(" " + fill(ranges[lv], vals[lv])));
      li.appendChild(txt);
      list.appendChild(li);
    });
  }

  function renderShare() {
    var text = fill(t("share_text"), {
      role: plan.role_name,
      city: plan.city_name,
      date: formatDate(plan.date),
      message: plan.message,
      url: location.href,
    });
    $("share").href = "https://wa.me/?text=" + encodeURIComponent(text);
  }

  // ---------- listen (read advice aloud) ----------

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

  function readInitialState() {
    var p = new URLSearchParams(location.search);
    var role = p.get("role") || recall("role");
    var lang = p.get("lang") || recall("lang");
    var date = p.get("date");
    if (role === "vendor" || role === "rider" || role === "construction") state.role = role;
    if (lang === "en" || lang === "hi") state.lang = lang;
    if (p.get("city")) state.city = p.get("city");
    if (date === "today") state.date = "";
    else if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) state.date = date;
  }

  function init() {
    readInitialState();
    applyText();

    document.querySelectorAll(".lang button").forEach(function (b) {
      b.addEventListener("click", function () {
        var lang = b.getAttribute("data-lang");
        if (lang === state.lang) return;
        state.lang = lang;
        store("lang", lang);
        applyText();
        load();
      });
    });

    $("day").addEventListener("change", function (e) {
      state.date = e.target.value;
      renderDays();
      load();
    });

    $("city").addEventListener("change", function (e) {
      state.city = e.target.value;
      // Replay dates are per city: jump to the new city's first heatwave day
      var days = currentCity().replay_days || [];
      if (state.date !== "" && days.length) state.date = days[0].date;
      renderDays();
      load();
    });

    $("toggle-hours").addEventListener("click", function () {
      state.showAll = !state.showAll;
      $("toggle-hours").textContent = state.showAll ? t("show_work") : t("show_all");
      if (plan) renderHours(plan.date === cityToday() ? cityHour() : -1);
    });

    $("retry").addEventListener("click", load);

    if (synth && window.SpeechSynthesisUtterance) {
      $("listen").hidden = false;
      $("listen").addEventListener("click", speak);
    }

    fetch("/api/options")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data) { options = data; renderRoles(); renderCities(); renderDays(); }
      })
      .catch(function () { /* built-in defaults are fine */ });

    load();
  }

  init();
})();
