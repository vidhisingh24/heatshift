// Heat-safety chat: POST /api/chat (Strands agent on Amazon Bedrock, template fallback).
// Nothing is stored on the server; the conversation lives only on this page.
(function () {
  "use strict";
  var HS = window.HS;
  var $ = function (id) { return document.getElementById(id); };
  var busy = false;

  var TXT = {
    en: {
      title: "Ask about heat and your work",
      powered: "Amazon Bedrock · Strands Agents",
      placeholder: "Type your question, e.g. I have to deliver at 2 PM. What should I do?",
      send: "Send",
      hello: "Ask me when to go out, where to find water, or what to do in the heat. I answer from today's plan.",
      chips: ["I must go at 2 PM", "Where can I drink water?", "Is it safe now?"],
      thinking: "Checking today's plan…",
      ai: "AI (Amazon Bedrock)",
      template: "Standard answer",
      error: "Could not answer right now. Please try again.",
      limited: "Too many questions. Wait a minute and try again.",
      emergency: "Emergency",
    },
    hi: {
      title: "गर्मी और अपने काम के बारे में पूछें",
      powered: "Amazon Bedrock · Strands Agents",
      placeholder: "अपना सवाल लिखें, जैसे: मुझे 2 बजे डिलीवरी करनी है, क्या करूँ?",
      send: "भेजें",
      hello: "पूछें कब बाहर जाना है, पानी कहाँ मिलेगा, या गर्मी में क्या करें। मैं आज की योजना से जवाब देता हूँ।",
      chips: ["मुझे 2 बजे जाना है", "पानी कहाँ पी सकता हूँ?", "क्या अभी जाना सुरक्षित है?"],
      thinking: "आज की योजना देख रहे हैं…",
      ai: "AI (Amazon Bedrock)",
      template: "सामान्य जवाब",
      error: "अभी जवाब नहीं मिल पाया। फिर कोशिश करें।",
      limited: "बहुत सारे सवाल। एक मिनट रुककर फिर पूछें।",
      emergency: "आपातकाल",
    },
  };
  function tx(k) { return TXT[HS.state.lang][k]; }

  function bubble(who, text, meta) {
    var row = HS.el("div", "msg msg-" + who);
    var b = HS.el("div", "bubble");
    text.split("\n").forEach(function (line, i) {
      if (i) b.appendChild(document.createElement("br"));
      b.appendChild(document.createTextNode(line));
    });
    row.appendChild(b);
    if (meta) row.appendChild(HS.el("span", "msg-meta" + (meta.cls ? " " + meta.cls : ""), meta.text));
    $("chat-log").appendChild(row);
    $("chat-log").scrollTop = $("chat-log").scrollHeight;
    return row;
  }

  function applyText() {
    document.querySelectorAll("[data-tc]").forEach(function (n) { n.textContent = tx(n.getAttribute("data-tc")); });
    $("chat-input").placeholder = tx("placeholder");
    var chips = $("chat-chips");
    chips.textContent = "";
    tx("chips").forEach(function (c) {
      var b = HS.el("button", "chip", c);
      b.type = "button";
      b.addEventListener("click", function () { send(c); });
      chips.appendChild(b);
    });
    if (!$("chat-log").querySelector(".msg-user")) {
      $("chat-log").textContent = "";
      bubble("bot", tx("hello"));
    }
  }

  function send(text) {
    text = (text || "").trim().slice(0, 500);
    if (!text || busy) return;
    busy = true;
    $("chat-send").disabled = true;
    bubble("user", text);
    $("chat-input").value = "";
    $("chat-count").textContent = "0/500";
    var wait = bubble("bot", tx("thinking"), null);
    wait.classList.add("is-wait");

    var st = HS.state;
    var body = { message: text, role: st.role, city: st.city, lang: st.lang, date: st.date || null };
    if (typeof st.lat === "number") { body.lat = st.lat; body.lon = st.lon; }

    fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) {
        if (r.status === 429) throw new Error("limited");
        if (!r.ok) throw new Error("http");
        return r.json();
      })
      .then(function (d) {
        wait.remove();
        var ai = d.message_source.indexOf("bedrock:") === 0;
        var meta = d.emergency ? { text: tx("emergency"), cls: "is-emergency" }
          : { text: ai ? tx("ai") : tx("template"), cls: ai ? "is-ai" : "" };
        var row = bubble("bot", d.answer, meta);
        if (d.emergency) row.classList.add("msg-emergency");
      })
      .catch(function (e) {
        wait.remove();
        bubble("bot", e.message === "limited" ? tx("limited") : tx("error"));
      })
      .then(function () { busy = false; $("chat-send").disabled = false; });
  }

  $("chat-form").addEventListener("submit", function (e) { e.preventDefault(); send($("chat-input").value); });
  $("chat-input").addEventListener("input", function (e) { $("chat-count").textContent = e.target.value.length + "/500"; });
  $("chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("chat-input").value); }
  });
  document.addEventListener("hs:lang", applyText);
  applyText();
})();
