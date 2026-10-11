// "I can't avoid this time" safe-trip mode. Calls /api/trip (deterministic, no AI).
(function () {
  "use strict";
  var HS = window.HS;
  var $ = function (id) { return document.getElementById(id); };

  var TXT = {
    en: {
      title: "I can't avoid this time",
      go_at: "I have to go out at",
      for: "for",
      check: "Check my trip",
      hours: ["30 min", "1 hour", "2 hours", "3 hours", "4 hours"],
      risk: "{start}–{end} · {level} · feels up to {hi}°C",
      alt_title: "Safer time today",
      no_alt: "No cooler time of the same length today. Follow the checklist closely.",
      checklist: "Before and during the trip",
      sources: "Based on NCDC and NDMA heat guidance",
      error: "Could not check this trip. Try again.",
    },
    hi: {
      title: "मुझे इसी समय जाना है",
      go_at: "मुझे बाहर जाना है",
      for: "कितनी देर",
      check: "मेरी यात्रा जाँचें",
      hours: ["30 मिनट", "1 घंटा", "2 घंटे", "3 घंटे", "4 घंटे"],
      risk: "{start}–{end} · {level} · महसूस तापमान {hi}°C तक",
      alt_title: "आज का सुरक्षित समय",
      no_alt: "आज इतनी ही देर का कोई ठंडा समय नहीं है। सूची का ध्यान से पालन करें।",
      checklist: "जाने से पहले और रास्ते में",
      sources: "NCDC और NDMA की गर्मी से जुड़ी सलाह पर आधारित",
      error: "यात्रा जाँच नहीं हो पाई। फिर कोशिश करें।",
    },
  };
  var HOUR_VALUES = ["0.5", "1", "2", "3", "4"];

  function tx(k) { return TXT[HS.state.lang][k]; }

  function applyText() {
    document.querySelectorAll("[data-tr]").forEach(function (n) { n.textContent = tx(n.getAttribute("data-tr")); });
    var start = $("trip-start");
    var keep = start.value || "14";
    start.textContent = "";
    for (var h = 5; h <= 22; h++) {
      var o = HS.el("option", "", HS.hhmm(h));
      o.value = String(h);
      start.appendChild(o);
    }
    start.value = keep;
    var hrs = $("trip-hours");
    var keepH = hrs.value || "1";
    hrs.textContent = "";
    HOUR_VALUES.forEach(function (v, i) {
      var o = HS.el("option", "", tx("hours")[i]);
      o.value = v;
      hrs.appendChild(o);
    });
    hrs.value = keepH;
    $("trip-result").textContent = "";
  }

  function render(d) {
    var box = $("trip-result");
    box.textContent = "";
    var t = HS.t;

    var head = HS.el("div", "trip-risk");
    var pill = HS.el("span", "level-pill");
    pill.setAttribute("data-level", d.risk_level);
    pill.appendChild(HS.levelIcon(d.risk_level));
    pill.appendChild(HS.el("span", "", t("levels")[d.risk_level]));
    head.appendChild(pill);
    head.appendChild(HS.el("span", "trip-window", HS.fill(tx("risk"), {
      start: d.start, end: d.end, level: t("levels")[d.risk_level], hi: Math.round(d.max_feels_c),
    })));
    box.appendChild(head);

    var alt = HS.el("div", "trip-alt" + (d.alternative ? "" : " is-none"));
    alt.appendChild(HS.el("p", "trip-alt-title", tx("alt_title")));
    alt.appendChild(HS.el("p", "", d.alternative ? d.alternative.text : tx("no_alt")));
    box.appendChild(alt);

    box.appendChild(HS.el("h3", "trip-sub", tx("checklist")));
    var ul = HS.el("ul", "checklist");
    d.checklist.forEach(function (item) { ul.appendChild(HS.el("li", "", item)); });
    box.appendChild(ul);

    var s = d.stop_signs;
    var stop = HS.el("div", "stop-box" + (d.show_stop_signs_prominently ? " is-prominent" : ""));
    stop.setAttribute("role", "alert");
    var warn = HS.el("div", "stop-part");
    warn.appendChild(HS.el("p", "stop-title", s.warning_title));
    warn.appendChild(HS.el("p", "", s.warning));
    warn.appendChild(HS.el("p", "stop-do", s.warning_do));
    stop.appendChild(warn);
    var em = HS.el("div", "stop-part stop-emergency");
    em.appendChild(HS.el("p", "stop-title", s.emergency_title));
    em.appendChild(HS.el("p", "", s.emergency));
    em.appendChild(HS.el("p", "stop-do", s.emergency_do));
    var call = HS.el("p", "call-row");
    [["108", "tel:108"], ["112", "tel:112"]].forEach(function (n) {
      var a = HS.el("a", "call-btn", n[0]);
      a.href = n[1];
      call.appendChild(a);
    });
    em.appendChild(call);
    stop.appendChild(em);
    box.appendChild(stop);

    var src = HS.el("p", "fine trip-sources", tx("sources") + ": ");
    d.sources.forEach(function (sObj, i) {
      var a = HS.el("a", "", sObj.name);
      a.href = sObj.url; a.target = "_blank"; a.rel = "noopener";
      if (i) src.appendChild(document.createTextNode(" · "));
      src.appendChild(a);
    });
    box.appendChild(src);
  }

  function check(evt) {
    if (evt) evt.preventDefault();
    var st = HS.state;
    var q = "city=" + encodeURIComponent(st.city) + "&role=" + encodeURIComponent(st.role) +
      "&lang=" + st.lang + (st.date ? "&date=" + st.date : "") +
      "&start=" + $("trip-start").value + "&hours=" + $("trip-hours").value;
    $("trip-result").textContent = "";
    $("trip-result").appendChild(HS.el("p", "fine", HS.t("loading")));
    fetch("/api/trip?" + q)
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(render)
      .catch(function () { $("trip-result").textContent = tx("error"); });
  }

  $("trip-form").addEventListener("submit", check);
  document.addEventListener("hs:lang", applyText);
  document.addEventListener("hs:plan", function () {
    // Re-run an open result when job, day or language changes
    if ($("trip-result").childElementCount) check();
  });
  applyText();

  // Shared with chat.js
  HS.trip = { check: check };
})();
