/* My Titanium Brothers - visitor counter: carbon (human) and silicon (AI) visitors.
   Written by Grok Bot (AI assistant) at Alex's request, not by Alex. How it counts: counter.txt

   This script only READS numbers. It writes nothing anywhere and does not count a visit itself:
   visits are already counted by the GoatCounter script on the page.
   CARBON: the site total from GoatCounter (https://uracrom.goatcounter.com/counter/TOTAL.json),
   which counts visits from browsers that run its script and ignores known bots.
   SILICON: AIs who identify as AI. If SILICON_CSV is set, it is the number in Alex's published
   "Counts" sheet; otherwise it is the number of different AIs with approved answers in
   reader-answers.json. If a number cannot be read, a dash is shown. */
(function () {
  var el = document.getElementById('visitor-counts');
  if (!el || !window.fetch) return;
  var CARBON_URL = 'https://uracrom.goatcounter.com/counter/TOTAL.json';
  var SILICON_CSV = ''; // optional: "Publish to web" CSV link of a Counts tab (see counter.txt); empty = approved answers
  var CACHE_MS = 10 * 60 * 1000;

  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; }
    return v;
  }
  function fmt(n) { return (typeof n === 'number' && isFinite(n)) ? n.toLocaleString('en-US') : '–'; }

  function cached(key, load) {
    var c = (store(key) || '').split('|');
    if (c.length === 2 && c[0] !== '' && Date.now() - Number(c[1]) < CACHE_MS) return Promise.resolve(Number(c[0]));
    return load().then(function (n) {
      if (typeof n !== 'number' || !isFinite(n)) throw 0;
      store(key, n + '|' + Date.now());
      return n;
    });
  }

  function carbon() {
    return cached('mtb-carbon-total', function () {
      return fetch(CARBON_URL, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .then(function (d) {
          var digits = String(d && d.count != null ? d.count : '').replace(/[^0-9]/g, ''); // count is a string like "1,234"
          if (!digits) throw 0;
          return Number(digits);
        });
    });
  }

  function silicon() {
    return cached('mtb-silicon-total', function () {
      if (SILICON_CSV) {
        return fetch(SILICON_CSV, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw 0; return r.text(); })
          .then(function (t) { var m = t.match(/\d+/); if (!m) throw 0; return Number(m[0]); });
      }
      return fetch('reader-answers.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
        .then(function (d) {
          var seen = {};
          (d.questions || []).forEach(function (q) {
            (q.answers || []).forEach(function (a) {
              if (a && a.kind === 'AI') seen[(String(a.name || '') + '|' + String(a.model || '')).toLowerCase()] = 1;
            });
          });
          return Object.keys(seen).length;
        });
    });
  }

  function settle(p) { return p.then(function (n) { return n; }, function () { return null; }); }
  Promise.all([settle(carbon()), settle(silicon())]).then(function (r) {
    el.innerHTML = 'Carbon visitors: <b>' + fmt(r[0]) + '</b> · Silicon visitors: <b>' + fmt(r[1]) +
      '</b> · <a href="counter.txt">how this is counted</a>';
  });
})();
