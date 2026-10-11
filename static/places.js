// Nearby water and rest spots from OpenStreetMap (via /api/places). Location stays in this browser.
(function () {
  "use strict";
  var HS = window.HS;
  var $ = function (id) { return document.getElementById(id); };
  var LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  var LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  var map = null;
  var last = null;   // {lat, lon, data}

  var TXT = {
    en: {
      title: "Find water and shade near me",
      intro: "Water and rest suggestions from OpenStreetMap. Opening hours are not verified; ask politely.",
      near_me: "Find water / shade near me",
      city_centre: "Use city centre",
      locating: "Finding your location…",
      searching: "Searching within 1 km…",
      denied: "Location not available. Showing the city centre instead.",
      insecure: "Your browser only shares location on secure (https) links, so this shows the city centre.",
      error: "Place search is unavailable right now. Try again in a minute.",
      found: "{n} places within 1 km of {where}.",
      you: "your location",
      centre: "the city centre",
      sample: "Live map data unavailable; showing saved OpenStreetMap data for central Delhi.",
      none: "Nothing found nearby in this category.",
      break_title: "10-minute break",
      break_sub: "The three closest spots to cool down, drink and rest.",
      groups: { drink: "Drink water", buy: "Buy water / ORS", shade: "Sit in shade / AC" },
      kinds: {
        drinking_water: "Drinking water", fountain: "Drinking fountain", shop: "Shop", kiosk: "Kiosk",
        supermarket: "Supermarket", pharmacy: "Pharmacy (ORS)", cafe: "Café", food: "Eatery",
        worship: "Place of worship", community: "Community centre", mall: "Mall", bus: "Bus station",
      },
      unnamed: "Unnamed",
      walk: "{m} m · {w} min walk",
      open_map: "Open in Maps",
    },
    hi: {
      title: "पास में पानी और छाँव ढूँढें",
      intro: "पानी और आराम की जगहें OpenStreetMap से। खुलने का समय जाँचा नहीं गया है; विनम्रता से पूछें।",
      near_me: "मेरे पास पानी / छाँव ढूँढें",
      city_centre: "शहर का केंद्र इस्तेमाल करें",
      locating: "आपकी लोकेशन ढूँढ रहे हैं…",
      searching: "1 किमी के अंदर ढूँढ रहे हैं…",
      denied: "लोकेशन नहीं मिली। शहर का केंद्र दिखा रहे हैं।",
      insecure: "आपका ब्राउज़र लोकेशन सिर्फ़ सुरक्षित (https) लिंक पर देता है, इसलिए शहर का केंद्र दिखा रहे हैं।",
      error: "अभी जगहें नहीं मिल पा रहीं। एक मिनट बाद फिर कोशिश करें।",
      found: "{where} से 1 किमी के अंदर {n} जगहें।",
      you: "आपकी लोकेशन",
      centre: "शहर के केंद्र",
      sample: "लाइव मैप डेटा नहीं मिला; मध्य दिल्ली का सहेजा हुआ OpenStreetMap डेटा दिखा रहे हैं।",
      none: "इस श्रेणी में पास में कुछ नहीं मिला।",
      break_title: "10 मिनट का ब्रेक",
      break_sub: "ठंडक, पानी और आराम के लिए सबसे पास की तीन जगहें।",
      groups: { drink: "पानी पिएँ", buy: "पानी / ORS खरीदें", shade: "छाँव / AC में बैठें" },
      kinds: {
        drinking_water: "पीने का पानी", fountain: "पानी का नल", shop: "दुकान", kiosk: "खोखा",
        supermarket: "सुपरमार्केट", pharmacy: "दवा की दुकान (ORS)", cafe: "कैफ़े", food: "खाने की दुकान",
        worship: "पूजा स्थल", community: "सामुदायिक केंद्र", mall: "मॉल", bus: "बस अड्डा",
      },
      unnamed: "बिना नाम",
      walk: "{m} मी · {w} मिनट पैदल",
      open_map: "मैप में खोलें",
    },
  };
  var CAT_ICON = { drink: "i-drop", buy: "i-vendor", shade: "i-pause" };

  function tx(k) { return TXT[HS.state.lang][k]; }

  function applyText() {
    document.querySelectorAll("[data-tp]").forEach(function (n) { n.textContent = tx(n.getAttribute("data-tp")); });
    if (last) render(last);
  }

  function placeItem(p) {
    var li = HS.el("li", "place");
    var ic = HS.el("span", "place-ico cat-" + p.category);
    ic.appendChild(HS.icon(CAT_ICON[p.category]));
    li.appendChild(ic);
    var body = HS.el("div", "place-body");
    var name = (HS.state.lang === "hi" && p.name_hi) ? p.name_hi : (p.name || tx("unnamed"));
    body.appendChild(HS.el("p", "place-name", name));
    body.appendChild(HS.el("p", "fine", tx("kinds")[p.kind] + " · " + HS.fill(tx("walk"), { m: p.distance_m, w: p.walk_min })));
    li.appendChild(body);
    var a = HS.el("a", "place-link", tx("open_map"));
    // geo: opens the phone's map app on Android; desktop gets OpenStreetMap
    a.href = /Android/i.test(navigator.userAgent) ? p.geo_url : p.map_url;
    a.target = "_blank"; a.rel = "noopener";
    li.appendChild(a);
    return li;
  }

  function render(res) {
    last = res;
    var d = res.data;
    var box = $("places-result");
    box.textContent = "";
    $("places-status").textContent = HS.fill(tx("found"), { n: d.count, where: res.mine ? tx("you") : tx("centre") }) +
      (d.source === "sample" ? " " + tx("sample") : "");

    if (d["break"].length) {
      var br = HS.el("div", "break-box");
      br.appendChild(HS.el("p", "break-title", tx("break_title")));
      br.appendChild(HS.el("p", "fine", tx("break_sub")));
      var ol = HS.el("ul", "place-list");
      d["break"].forEach(function (p) { ol.appendChild(placeItem(p)); });
      br.appendChild(ol);
      box.appendChild(br);
    }

    var mapEl = HS.el("div", "places-map");
    mapEl.id = "places-map";
    box.appendChild(mapEl);

    ["drink", "buy", "shade"].forEach(function (c) {
      var sec = HS.el("div", "place-group");
      sec.appendChild(HS.el("h3", "", tx("groups")[c]));
      if (!d.groups[c].length) sec.appendChild(HS.el("p", "fine", tx("none")));
      else {
        var ul = HS.el("ul", "place-list");
        d.groups[c].slice(0, 5).forEach(function (p) { ul.appendChild(placeItem(p)); });
        sec.appendChild(ul);
      }
      box.appendChild(sec);
    });

    var att = HS.el("p", "fine");
    att.appendChild(document.createTextNode("© "));
    var a = HS.el("a", "", "OpenStreetMap contributors");
    a.href = "https://www.openstreetmap.org/copyright"; a.target = "_blank"; a.rel = "noopener";
    att.appendChild(a);
    box.appendChild(att);

    drawMap(res);
  }

  // Small map, loaded only when there are results (the list is the main thing).
  function drawMap(res) {
    loadLeaflet(function () {
      var el = $("places-map");
      if (!el || !window.L) return;
      if (map) { map.remove(); map = null; }
      map = L.map(el, { scrollWheelZoom: false, attributionControl: true }).setView([res.lat, res.lon], 15);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
      }).addTo(map);
      L.circleMarker([res.lat, res.lon], { radius: 7, color: "#fff", weight: 2, fillColor: "#171614", fillOpacity: 1 }).addTo(map);
      var colors = { drink: "#2f8552", buy: "#c4561f", shade: "#4a4640" };
      ["drink", "buy", "shade"].forEach(function (c) {
        res.data.groups[c].forEach(function (p) {
          L.circleMarker([p.lat, p.lon], { radius: 6, color: "#fff", weight: 2, fillColor: colors[c], fillOpacity: 1 })
            .bindTooltip((p.name || tx("unnamed")) + " · " + tx("kinds")[p.kind]).addTo(map);
        });
      });
    });
  }

  function loadLeaflet(cb) {
    if (window.L) return cb();
    if (!document.querySelector("link[data-leaflet]")) {
      var css = document.createElement("link");
      css.rel = "stylesheet"; css.href = LEAFLET_CSS; css.setAttribute("data-leaflet", "");
      document.head.appendChild(css);
    }
    var s = document.createElement("script");
    s.src = LEAFLET_JS;
    s.onload = cb;
    s.onerror = function () { var el = $("places-map"); if (el) el.remove(); };  // list still works
    document.head.appendChild(s);
  }

  function search(lat, lon, mine) {
    $("places-status").textContent = tx("searching");
    fetch("/api/places?lat=" + lat + "&lon=" + lon + "&radius=1000")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) { render({ lat: lat, lon: lon, mine: mine, data: data }); })
      .catch(function () { $("places-status").textContent = tx("error"); });
  }

  function centre() {
    var c = HS.cityList()[HS.state.city];
    if (c && typeof c.lat === "number") search(c.lat, c.lon, false);
  }

  $("places-near").addEventListener("click", function () {
    var st = HS.state;
    if (typeof st.lat === "number") return search(st.lat, st.lon, true);
    // Browsers only share location with https pages
    if (!window.isSecureContext) { $("places-status").textContent = tx("insecure"); return centre(); }
    if (!navigator.geolocation) { $("places-status").textContent = tx("denied"); return centre(); }
    $("places-status").textContent = tx("locating");
    navigator.geolocation.getCurrentPosition(function (pos) {
      st.lat = Math.round(pos.coords.latitude * 10000) / 10000;
      st.lon = Math.round(pos.coords.longitude * 10000) / 10000;
      try { localStorage.setItem("heatshift.loc", JSON.stringify({ lat: st.lat, lon: st.lon })); } catch (e) { /* ignore */ }
      search(st.lat, st.lon, true);
    }, function () {
      $("places-status").textContent = tx("denied");
      centre();
    }, { timeout: 10000, maximumAge: 600000 });
  });
  $("places-centre").addEventListener("click", centre);
  document.addEventListener("hs:lang", applyText);
  applyText();

  // Shared with chat.js
  HS.places = { search: search };
})();
