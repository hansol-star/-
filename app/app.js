/* 정훈 증권 앱 — 정적 SPA [9/21 리디자인 + 실시간 층]
   두 층을 읽는다:
     ① window.APP_DATA (data.js)  = 분석·룰 정본(보고서 시점) — build_app_data.py
     ② live.json                  = 실시간 시세(클라우드 5~10분 · 로컬 백업) — live_quotes.py
   실시간 층은 **가격만** 바꾼다. 사다리·밴드·게이트는 data.js의 정본 재료에 실시간 가격을 대입한
   '장중 추정'으로만 그리고, 확정은 종가·보고서다. 투자 자문 아님 — 결정은 정훈. */
(function () {
  "use strict";
  var D = window.APP_DATA;
  var root = document.getElementById("app");
  var tabsEl = document.getElementById("tabs");

  // ── 기본 도우미 ──
  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(n) { return n == null || isNaN(n) ? "—" : Number(n).toLocaleString("ko-KR"); }
  function num2(n) { return n == null || isNaN(n) ? "—" : Number(n).toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function won(n) { return n == null || isNaN(n) ? "—" : Number(Math.round(n)).toLocaleString("ko-KR") + "원"; }
  function sign(n) { return n > 0 ? "+" : ""; }
  function price(p, cur) {
    if (p == null) return "—";
    if (cur === "USD") return "$" + Number(p).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return Number(Math.round(p)).toLocaleString("ko-KR") + "원";
  }
  function pct(p, d) { if (p == null || isNaN(p)) return "—"; return (p > 0 ? "+" : "") + Number(p).toFixed(d == null ? 2 : d) + "%"; }
  function cls(p) { return p == null || isNaN(p) || Math.abs(p) < 1e-9 ? "flat" : (p > 0 ? "up" : "down"); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmtShares(v) { if (v == null) return "—"; return v % 1 === 0 ? String(v) : v.toFixed(6).replace(/0+$/, "").replace(/\.$/, ""); }

  function mdInline(s) {
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }
  function mdToHtml(md) {
    var lines = String(md || "").replace(/\r\n/g, "\n").split("\n");
    var out = [], i = 0;
    function flushList(buf, ordered) {
      if (!buf.length) return;
      out.push("<" + (ordered ? "ol" : "ul") + ">" + buf.map(function (x) { return "<li>" + mdInline(esc(x)) + "</li>"; }).join("") + "</" + (ordered ? "ol" : "ul") + ">");
    }
    while (i < lines.length) {
      var t = lines[i].trim();
      if (/^```/.test(t)) {
        var cb = []; i++;
        while (i < lines.length && !/^```/.test(lines[i].trim())) { cb.push(lines[i]); i++; }
        i++; out.push('<pre class="md"><code>' + esc(cb.join("\n")) + "</code></pre>"); continue;
      }
      if (t.indexOf("|") === 0 && i + 1 < lines.length && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1].trim())) {
        var rows = [];
        while (i < lines.length && lines[i].trim().indexOf("|") === 0) { rows.push(lines[i].trim()); i++; }
        rows.splice(1, 1);
        var cells = function (r) { return r.replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); }); };
        var html = '<div class="mdtable"><table><thead><tr>' + cells(rows[0]).map(function (c) { return "<th>" + mdInline(esc(c)) + "</th>"; }).join("") + "</tr></thead><tbody>";
        for (var r = 1; r < rows.length; r++) html += "<tr>" + cells(rows[r]).map(function (c) { return "<td>" + mdInline(esc(c)) + "</td>"; }).join("") + "</tr>";
        out.push(html + "</tbody></table></div>"); continue;
      }
      var hm = t.match(/^(#{1,6})\s+(.*)$/);
      if (hm) { var lv = hm[1].length; out.push("<h" + lv + ' class="md h' + lv + '">' + mdInline(esc(hm[2])) + "</h" + lv + ">"); i++; continue; }
      if (/^([-*_])\1{2,}$/.test(t)) { out.push('<hr class="md">'); i++; continue; }
      if (t.indexOf("> ") === 0 || t === ">") {
        var qb = [];
        while (i < lines.length && (lines[i].trim().indexOf("> ") === 0 || lines[i].trim() === ">")) { qb.push(mdInline(esc(lines[i].trim().replace(/^>\s?/, "")))); i++; }
        out.push("<blockquote>" + qb.join("<br>") + "</blockquote>"); continue;
      }
      if (/^[-*+]\s+/.test(t)) {
        var ub = [];
        while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) { ub.push(lines[i].trim().replace(/^[-*+]\s+/, "")); i++; }
        flushList(ub, false); continue;
      }
      if (/^\d+[.)]\s+/.test(t)) {
        var ob = [];
        while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) { ob.push(lines[i].trim().replace(/^\d+[.)]\s+/, "")); i++; }
        flushList(ob, true); continue;
      }
      if (!t) { i++; continue; }
      var pb = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|\|)/.test(lines[i].trim()) && !/^([-*_])\1{2,}$/.test(lines[i].trim())) { pb.push(lines[i].trim()); i++; }
      if (pb.length) out.push("<p>" + mdInline(esc(pb.join(" "))) + "</p>");
    }
    return out.join("\n");
  }

  // ── 아이콘 (인라인 선 SVG — currentColor) ──
  function svg(p, sw) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.8) + '" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>'; }
  var IC = {
    today: svg('<rect x="3.5" y="4.5" width="17" height="16" rx="3"/><path d="M3.5 9.5h17M8 3v3M16 3v3"/><circle cx="12" cy="15" r="1.8"/>'),
    pf: svg('<path d="M12 3a9 9 0 1 0 9 9h-9z"/><path d="M15 3.5A9 9 0 0 1 20.5 9H15z"/>'),
    rules: svg('<path d="M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>'),
    plan: svg('<path d="M10 6h10M10 12h10M10 18h10"/><path d="M4 6l1.2 1.2L7.5 5M4 12l1.2 1.2L7.5 11M4 18l1.2 1.2L7.5 17"/>'),
    research: svg('<path d="M6 3.5h9l4 4v13H6z"/><path d="M15 3.5v4h4M9 12h7M9 16h5"/>'),
    back: svg('<path d="M15 5l-7 7 7 7"/>', 2.2),
    chev: svg('<path d="M9 5l7 7-7 7"/>', 2),
    sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2.5 12h2M19.5 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    moon: svg('<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>'),
    auto: svg('<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/>'),
    check: svg('<path d="M5 12.5l4.5 4.5L19 7"/>', 3),
    video: svg('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9.5v5l4.5-2.5z"/>'),
    radar: svg('<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19 5a10 10 0 0 1 0 14M5 19A10 10 0 0 1 5 5"/>'),
    guru: svg('<path d="M4 20h16M6 20v-9M10 20v-9M14 20v-9M18 20v-9M3 11l9-6 9 6z"/>'),
    pm: svg('<path d="M5 5h14v10H9.5L5 19z"/><path d="M9 9.5h6"/>'),
    compass: svg('<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>'),
    ledger: svg('<rect x="4" y="3.5" width="16" height="17" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>'),
    archive: svg('<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v10h14V9M10 13h4"/>'),
    doc: svg('<path d="M6 3.5h9l4 4v13H6z"/><path d="M15 3.5v4h4"/>'),
    clock: svg('<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'),
    x: svg('<path d="M6 6l12 12M18 6L6 18"/>', 2.2),
    eye: svg('<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>'),
    alert: svg('<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4.5M12 17.3v.2"/>'),
    dash: svg('<path d="M6 12h12"/>', 2.2)
  };

  // ── 테마 (자동 → 밝게 → 어둡게) ──
  var THEME_KEY = "jh_theme";
  function getTheme() { try { return localStorage.getItem(THEME_KEY) || "auto"; } catch (e) { return "auto"; } }
  function applyTheme(t) { var r = document.documentElement; if (t === "light" || t === "dark") r.setAttribute("data-theme", t); else r.removeAttribute("data-theme"); }
  function cycleTheme() {
    var t = getTheme(), n = t === "auto" ? "light" : t === "light" ? "dark" : "auto";
    try { localStorage.setItem(THEME_KEY, n); } catch (e) {}
    applyTheme(n); var b = document.getElementById("themebtn"); if (b) { b.innerHTML = themeIcon(); b.setAttribute("aria-label", themeLabel()); }
  }
  function themeIcon() { var t = getTheme(); return t === "light" ? IC.sun : t === "dark" ? IC.moon : IC.auto; }
  function themeLabel() { var t = getTheme(); return "화면 테마: " + (t === "light" ? "밝게" : t === "dark" ? "어둡게" : "기기 설정") + " (눌러서 바꾸기)"; }
  applyTheme(getTheme());

  // ── 시간(KST) ──
  function kst(ms) { return new Date((ms == null ? Date.now() : ms) + 9 * 3600e3); }
  function hhmm(ts) { var d = kst(ts * 1000); return pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()); }
  function kstDate(ts) { return kst(ts == null ? null : ts * 1000).toISOString().slice(0, 10); }
  function kstMin() { var d = kst(); return d.getUTCHours() * 60 + d.getUTCMinutes(); }
  function kstDow() { return kst().getUTCDay(); }
  function todayLabel() { var d = kst(); return (d.getUTCMonth() + 1) + "월 " + d.getUTCDate() + "일 (" + "일월화수목금토".charAt(d.getUTCDay()) + ")"; }
  function mdLabel(ts) { var d = kst(ts * 1000); return (d.getUTCMonth() + 1) + "/" + d.getUTCDate(); }
  function buildTs() {
    var m = String(D && D.generated_at || "").match(/(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)/);
    return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4] - 9, +m[5]) / 1000 : 0;
  }

  // ════════════════ 실시간 층 ════════════════
  var LIVE = null, liveErr = false, liveBusy = false, lastFetch = 0;
  function liveOn() { return !!(LIVE && LIVE.quotes && LIVE.ts >= buildTs() - 600); }
  function Q(tk) { return liveOn() ? (LIVE.quotes[tk] || null) : null; }
  function S(tk) { return liveOn() && LIVE.series ? (LIVE.series[tk] || null) : null; }
  function fetchLive() {
    if (liveBusy) return;
    liveBusy = true; setPill();
    fetch("live.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(function (j) {
      liveBusy = false; liveErr = false; lastFetch = Date.now();
      var changed = !LIVE || j.ts !== LIVE.ts;
      LIVE = j;
      if (changed) rerender(); else setPill();
    }).catch(function () { liveBusy = false; liveErr = true; lastFetch = Date.now(); setPill(); });
  }
  function marketOpen() {
    if (!LIVE || !LIVE.market) return false;
    var m = LIVE.market;
    return [m.kr, m.us].some(function (s) { return s === "reg" || s === "pre" || s === "post"; });
  }
  function pillState() {
    if (!LIVE) return liveErr ? ["st-off", "실시간 연결 안 됨"] : ["", "불러오는 중"];
    if (!liveOn()) return ["st-off", "보고서 시세"];
    var age = (Date.now() / 1000 - LIVE.ts) / 60;
    if (liveErr) return ["st-off", "오프라인 · " + hhmm(LIVE.ts)];
    if (!marketOpen()) return ["", "장 마감 · " + hhmm(LIVE.ts)];
    if (age > 15) return ["st-delay", "지연 " + Math.round(age) + "분"];
    return ["st-live", "실시간 · " + hhmm(LIVE.ts)];
  }
  function setPill() {
    var b = document.getElementById("livepill"); if (!b) return;
    var s = pillState();
    b.className = "live-pill " + s[0] + (liveBusy ? " loading" : "");
    b.innerHTML = "<i></i>" + esc(s[1]);
    b.setAttribute("aria-label", s[1] + " — 눌러서 시세 새로고침");
  }
  var SESS = { reg: "정규장", pre: "프리", post: "애프터", closed: "마감" };
  // 정규장 태그는 상세 화면에서만(all) — 목록·스트립에선 프리·애프터처럼 '평소와 다른' 세션만 표시
  function sessTag(q, all) { if (!q || !q.s || q.s === "closed" || (q.s === "reg" && !all)) return ""; return '<span class="sess ' + q.s + '">' + SESS[q.s] + '</span>'; }

  function find(tk) {
    var all = (D.holdings || []).concat(D.watchlist || []);
    for (var i = 0; i < all.length; i++) if (all[i].ticker === tk) return all[i];
    return null;
  }
  function isKR(tk) { return /\.K[SQ]$/.test(tk || ""); }
  function kindOf(tk) { if (isKR(tk)) return "krw"; if (tk === "KRW=X") return "fx"; if ((tk || "").charAt(0) === "^") return "idx"; return "usd"; }
  function fmtP(v, tk) {
    if (v == null || isNaN(v)) return "—";
    var k = kindOf(tk);
    if (k === "krw") return num(Math.round(v)) + "원";
    if (k === "fx") return num2(v) + "원";
    if (k === "idx") return num2(v);
    return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function px(st) { var q = Q(st.ticker); return q && q.p != null ? q.p : st.price; }
  function chg(st) { var q = Q(st.ticker); return q && q.c != null ? q.c : st.change_pct; }
  function fxNow() { var q = Q("KRW=X"); return (q && q.p) || (D.fx && D.fx.usdkrw) || 1400; }

  function holdingsLive() {
    var fx = fxNow(), fx0 = (D.fx && D.fx.usdkrw) || fx;
    var hs = (D.holdings || []).map(function (h) {
      var q = Q(h.ticker), p = q && q.p != null ? q.p : h.price, us = h.region === "us", mult = us ? fx : 1;
      var value = (p || 0) * h.shares * mult;
      var costK = (h.value_krw != null && h.pnl_krw != null) ? h.value_krw - h.pnl_krw : h.cost * h.shares * (us ? fx0 : 1);
      var pc = q && q.pc != null ? q.pc : (h.change_pct != null && h.price ? h.price / (1 + h.change_pct / 100) : null);
      return Object.assign({}, h, {
        lp: p, lc: q && q.c != null ? q.c : h.change_pct, lq: q, lvalue: value, costK: costK,
        lpnl: value - costK, lpnlpct: h.cost ? (p / h.cost - 1) * 100 : null,
        lday: pc != null && p != null ? (p - pc) * h.shares * mult : 0
      });
    });
    var tot = hs.reduce(function (a, h) { return a + h.lvalue; }, 0) || 1;
    hs.forEach(function (h) { h.w = h.lvalue / tot * 100; });
    return hs;
  }
  function totalsLive(hs) {
    var t = D.totals || {}, fx = fxNow();
    var stocks = 0, cost = 0, day = 0, kr = 0, usS = 0;
    var noFx = 0;
    hs.forEach(function (h) { stocks += h.lvalue; cost += h.costK; day += h.lday; if (h.region === "kr") kr += h.lvalue; else usS += h.lvalue; noFx += h.region === "kr" ? h.lpnl : ((h.lp || 0) - h.cost) * h.shares * fx; });
    var cashUK = (t.cash_usd || 0) * fx, assets = stocks + (t.cash_krw || 0) + cashUK;
    return {
      assets: assets, stocks: stocks, pnl: stocks - cost, pnlPct: cost ? (stocks / cost - 1) * 100 : null, pnlNoFx: noFx,
      day: day, dayPct: (stocks - day) ? day / (stocks - day) * 100 : null,
      cashK: t.cash_krw || 0, cashU: t.cash_usd || 0, cashUK: cashUK, fx: fx,
      krW: stocks ? kr / stocks * 100 : null, usdW: assets ? (usS + cashUK) / assets * 100 : null
    };
  }

  // 룰1 낙폭 사다리 — 정본 재료(data.js safety) × 실시간 코스피
  var PIN_TXT = {
    ok: "잠김 — 다음 단계 미도달, 신규 매수 실탄 없음",
    watch: "해금 — 사다리 집행 가능 구간",
    spent: "해금됐지만 상한까지 집행 완료 — 잔여 0원, 다음 단계 도달 시 새 몫",
    freeze: "정지 — 하드플로어 발동(S&P500 폭풍 ≥70%ile), 사다리 전면 정지",
    rule6: "룰6 우선(d207) — 국내주 22% 초과라 사다리는 기록만, 집행 0원",
    unknown: "코스피 시세 미확인"
  };
  // ★[9/21 d205] 미국 트랙 — 달러는 코스피 사다리가 아니라 3회 균등 분할(월 1회)이 다룬다
  function usTrack() { var u = D.us_track || {}; return { u: u, ok: !!u.status && u.status !== "error", allowed: u.allowed_usd || 0 }; }
  var US_SHORT = { due: "미국 회차 도래", waiting: "다음 회차 대기", deferred: "하드플로어 연기", complete: "사이클 완료", no_cycle: "사이클 없음" };
  function usd(v) { return v == null || isNaN(v) ? "—" : "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function ladderLive() {
    var s = D.safety || {}, q = Q("^KS11");
    var k = q && q.p != null ? q.p : s.price;
    // live = 국내 정규장 중(장중 지수로 재계산한 '추정'). 장이 끝났으면 같은 값이 오늘 종가다
    var out = { s: s, k: k, kc: q && q.c != null ? q.c : s.change_pct, q: q, live: !!(q && q.s === "reg"), fresh: !!q, steps: s.steps || [],
      dd: s.drawdown_pct, allowed: s.allowed_krw, cap: s.cap_krw, spent: s.spent_krw || 0, unl: s.unlocked_pct, status: s.status || "unknown" };
    if (!s.peak || !s.steps || k == null) return out;
    var dd = (k / s.peak - 1) * 100, unl = 0;
    s.steps.forEach(function (st) { if (dd <= st.thr) unl += st.alloc_pct; });
    var cap = Math.round((s.base_krw || 0) * unl / 100 * (s.mult || 1));
    var allowed = (s.halted || s.rule6_block) ? 0 : Math.max(0, cap - (s.spent_krw || 0));
    var nxt = null; for (var i = 0; i < s.steps.length; i++) if (dd > s.steps[i].thr) { nxt = s.steps[i]; break; }
    out.dd = dd; out.unl = unl; out.cap = cap; out.allowed = allowed; out.next = nxt;
    out.nextLevel = nxt ? s.peak * (1 + nxt.thr / 100) : null;
    out.status = s.halted ? "freeze" : s.rule6_block ? "rule6" : (unl > 0 && allowed === 0 ? "spent" : unl > 0 ? "watch" : "ok");
    return out;
  }
  function stormPct() { var m = String((D.safety || {}).floor_note || "").match(/([\d.]+)\s*%ile/); return m ? +m[1] : null; }

  // 가격 알림 — 문턱값(level/low/high)에 실시간 가격을 대입
  function alertsLive() {
    return (D.alerts || []).filter(function (a) {
      return (a.level != null || a.low != null) && ["above", "below", "between"].indexOf(a.cond) >= 0 && !/폐기|무효/.test(a.id);
    }).map(function (a) {
      var q = Q(a.ticker), st = find(a.ticker);
      var p = q && q.p != null ? q.p : (a.price != null ? a.price : st && st.price);
      var fired = null, dist = null;
      if (p != null) {
        if (a.cond === "below") { fired = p < a.level; dist = (a.level / p - 1) * 100; }
        else if (a.cond === "above") { fired = p > a.level; dist = (a.level / p - 1) * 100; }
        else { fired = p >= a.low && p <= a.high; dist = p > a.high ? (a.high / p - 1) * 100 : p < a.low ? (a.low / p - 1) * 100 : 0; }
      }
      return Object.assign({}, a, { lp: p, lfired: fired, ldist: dist, lq: q, was: !!a.fired });
    });
  }
  function alertBy(re) { var a = alertsLive(); for (var i = 0; i < a.length; i++) if (re.test(a[i].id)) return a[i]; return null; }
  function cleanId(s) { return String(s || "").replace(/^[^\w가-힣\[\(]+/, "").replace(/\s+/g, " ").trim(); }

  // 국내 가격제한폭 — KRX 호가단위(2023.1.25 개편). 20만~50만원 = 500원(9/21 validate_report 정정과 동일)
  function krTick(p) { return p >= 500000 ? 1000 : p >= 200000 ? 500 : p >= 50000 ? 100 : p >= 20000 ? 50 : p >= 5000 ? 10 : p >= 2000 ? 5 : 1; }
  function krBand(base) {
    var u = base * 1.3, l = base * 0.7, tu = krTick(u), tl = krTick(l);
    return { up: Math.floor(u / tu + 1e-9) * tu, lo: Math.ceil(l / tl - 1e-9) * tl, base: base };
  }
  // ── 국내 거래일 달력 — 주말 + D.events의 '휴장'(추석 등) ──
  var HOL = null;
  function krHolidays() {
    if (HOL) return HOL;
    HOL = {};
    (D.events || []).forEach(function (e) {
      if (e.kind !== "휴장" || !e.date) return;
      for (var d = e.date, i = 0; d <= (e.end || e.date) && i < 20; d = addDay(d, 1), i++) HOL[d] = 1;
    });
    return HOL;
  }
  function addDay(iso, n) { return new Date(Date.parse(iso + "T00:00:00Z") + n * 864e5).toISOString().slice(0, 10); }
  function dayDiff(a, b) { return Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / 864e5); }
  function isKrSession(iso) { var w = new Date(iso + "T00:00:00Z").getUTCDay(); return w >= 1 && w <= 5 && !krHolidays()[iso]; }
  function sessionAfter(iso) { var d = addDay(iso, 1); for (var i = 0; i < 20 && !isKrSession(d); i++) d = addDay(d, 1); return d; }
  // 다음 국내 정규장 — 오늘이 거래일이고 09:00 전이면 오늘
  function nextKrSession() { var t = kstDate(); return isKrSession(t) && kstMin() < 9 * 60 ? t : sessionAfter(t); }
  function md(iso) { var d = new Date(String(iso).slice(0, 10) + "T00:00:00Z"); return (d.getUTCMonth() + 1) + "/" + d.getUTCDate(); }
  function mdw(iso) { return md(iso) + "(" + "일월화수목금토".charAt(new Date(String(iso).slice(0, 10) + "T00:00:00Z").getUTCDay()) + ")"; }
  function relDay(iso) { var n = dayDiff(kstDate(), iso); return n === 0 ? "오늘" : n === 1 ? "내일" : mdw(iso); }

  // 다음(또는 오늘) 정규장 밴드의 기준가 판정 — day = 그 밴드가 적용되는 거래일
  function bandBase(tk) {
    var q = Q(tk), st = find(tk), m = kstMin(), today = kstDate(), nxt = nextKrSession();
    var inSess = isKrSession(today) && m >= 9 * 60 && m < 15 * 60 + 30;
    if (q && q.rc != null && q.rt) {
      var rcToday = kstDate(q.rt) === today;
      if (rcToday && m >= 15 * 60 + 30) return { base: q.rc, day: nxt, when: mdw(nxt), basis: "오늘 종가", final: true };
      if (rcToday && inSess && q.pc != null) return { base: q.pc, day: today, when: "오늘", basis: "전일 종가", final: true, preview: q.p };
      return { base: q.rc, day: nxt, when: nxt === today ? "오늘" : mdw(nxt), basis: mdLabel(q.rt) + " 종가", final: true };
    }
    return st && st.price ? { base: st.price, day: nxt, when: mdw(nxt), basis: "보고서 시세", final: false } : null;
  }
  // 주문 하나의 접수 판정 — 밴드 · 주문가 · (밴드 밖이면) 접수에 필요한 최소 종가
  function bandEval(o) {
    var bb = bandBase(o.ticker);
    if (!bb || !bb.base || o.price == null) return null;
    var band = krBand(bb.base), P = +o.price, ok = P <= band.up && P >= band.lo, need = null;
    var sell = /매도|트림|익절/.test(o.action || o.label || "");
    if (P > band.up) {
      // 상한 = floor(기준×1.3, 호가) ≥ 주문가 를 만족하는 가장 낮은 '실제로 찍힐 수 있는' 종가
      var t0 = krTick(P / 1.3);
      need = Math.ceil(P / 1.3 / t0) * t0;
      while (krBand(need).up < P) need += krTick(need);
    }
    return { bb: bb, band: band, P: P, ok: ok, sell: sell, need: need };
  }

  // 주문 상태 분류 — tasks.json orders.status는 자유 서술이라 규칙으로 묶는다
  //   hold = 보류(접수 대상 아님) · cond = 조건 대기(등록선·트리거 미충족 — 오늘 걸 주문이 아니다)
  //   [9/21 r2] 舊 분류는 '보류'를 대기로 읽어 NAVER 196,400원 매수(6/26 보류)를 오늘 밤 할 일에 '접수 가능'으로 띄웠다
  function orderKind(o) {
    var s = String(o.status || "");
    if (/미체결|미접수|취소|폐기|대체|⚪|❌/.test(s)) return "cxl";
    if (/체결|✅/.test(s)) return "fill";
    if (/결정 완료|🟢/.test(s)) return "done";
    if (/보류/.test(s)) return "hold";
    if (/만료|트리거 대기|조건 미충족|대기 —/.test(s)) return "cond";
    if (/^계획|상시 룰/.test(s)) return "plan";
    return "wait";
  }
  var ORDER_LBL = { plan: "계획", wait: "대기", cond: "조건 대기", hold: "보류", fill: "체결", cxl: "종료", done: "결정" };
  function activeOrders() { return (D.orders || []).filter(function (o) { return /^(plan|wait|cond|hold)$/.test(orderKind(o)); }); }
  function regLine(tk) { var a = alertsLive().filter(function (x) { return x.ticker === tk && /등록선/.test(x.id); }); return a[0] || null; }
  // 오늘 밤 걸 국내 지정가 = '대기(매일 등록·예약)'만. 계획·조건 대기는 같은 종목 등록선이 점등했을 때만 올라온다.
  // all=true(종목 상세)면 계획·조건 대기까지 — '걸 수 있나'를 미리 보여주되 카드 문구가 다르다
  function activeKrOrders(all) {
    var seen = {}, out = [];
    (D.orders || []).filter(function (o) {
      if (!isKR(o.ticker) || o.price == null) return false;
      var k = orderKind(o);
      if (k === "wait") return true;
      if (k === "plan" || k === "cond") { var rl = regLine(o.ticker); return all || !!(rl && rl.lfired); }
      return false;
    }).sort(function (a, b) { return String(b.date || "").localeCompare(String(a.date || "")); })
      .forEach(function (o) { var k = o.ticker + "@" + o.price; if (!seen[k]) { seen[k] = 1; out.push(o); } });
    return out;
  }
  // '등록했어요' — 이 폰에만 저장(거래일별 키라 다음 거래일엔 자동으로 풀린다)
  var LS_REG = "jh_order_reg";
  function regKey(o) { return o.id + "@" + nextKrSession(); }
  function regMap() { try { return JSON.parse(localStorage.getItem(LS_REG) || "{}"); } catch (e) { return {}; } }
  function isReg(o) { return !!regMap()[regKey(o)]; }
  function toggleReg(id) {
    var o = (D.orders || []).filter(function (x) { return x.id === id; })[0]; if (!o) return;
    try { var m = regMap(), k = regKey(o); if (m[k]) delete m[k]; else m[k] = 1; localStorage.setItem(LS_REG, JSON.stringify(m)); } catch (e) {}
  }
  function gatesLive() {
    var g1 = alertBy(/TF 해제 조건①/), g3 = alertBy(/TF 해제 조건③/), ft = D.flow_trend || {};
    var on1 = !!(g1 && g1.lp != null && g1.lp >= g1.level), on2 = ft.direction === "순매수" && (ft.streak || 0) >= 2, on3 = !!(g3 && g3.lp != null && g3.lp < g3.level);
    var kq = Q("^KS11"), last = kq && kq.rt ? kstDate(kq.rt) : null;
    return { g1: g1, g3: g3, ft: ft, on1: on1, on2: on2, on3: on3, n: (on1 ? 1 : 0) + (on2 ? 1 : 0) + (on3 ? 1 : 0),
      ftStale: !!(last && ft.as_of && ft.as_of < last), last: last, buyStreak: ft.direction === "순매수" ? (ft.streak || 0) : 0 };
  }
  function flowPair() { var s = (D.flows || {}).series || []; return s.length >= 2 ? [s[s.length - 2], s[s.length - 1]] : null; }
  function eok(v) { return (v > 0 ? "+" : "") + num(v) + "억"; }
  // 짧은 다음 행동 문구 — 서술형 필드의 첫 마디만(마크다운·이모지 제거)
  function shortTxt(s, n) {
    s = String(s || "").replace(/\*\*/g, "").replace(/[\p{Extended_Pictographic}️]/gu, "").replace(/\s+/g, " ").trim();
    if (!s || s === "—") return "";
    var pre = "", m = s.match(/^(없음|—)\s*(?:[—-]\s*)?/);
    if (m && s.length > m[0].length) { if (m[1] === "없음") pre = "트림 없음 · "; s = s.slice(m[0].length); }
    s = s.replace(/^\((.*)\)$/, "$1");
    // 괄호 밖의 첫 구분자( · — ; . )에서 자른다 — 괄호 안 ' · '에서 자르면 문장이 깨진다
    for (var i = 0, d = 0; i < s.length; i++) {
      var ch = s.charAt(i);
      if (ch === "(" || ch === "（") d++;
      else if ((ch === ")" || ch === "）") && d) d--;
      else if (!d && i > 6 && (s.substr(i, 3) === " · " || s.substr(i, 3) === " — " || ch === ";" || s.substr(i, 2) === ". ")) { s = s.slice(0, i); break; }
    }
    n = n || 40;
    if (s.length > n) { var pi = s.indexOf("("); s = pi > 8 && pi < n ? s.slice(0, pi) : s.slice(0, n - 1) + "…"; }
    s = (pre + s).trim();
    return s.replace(/ ·$/, "");
  }
  function bars5(n) {
    n = n || 0;
    var s = '<span class="bars ' + (n >= 4 ? "hi" : n === 3 ? "mid" : "low") + '" role="img" aria-label="별점 ' + n + '/5">';
    for (var i = 1; i <= 5; i++) s += '<i class="' + (i <= n ? "on" : "") + '"></i>';
    return s + '</span>';
  }
  function tossUrl(tk) { return "https://tossinvest.com/stocks/A" + String(tk).slice(0, 6); }
  function h2s(title, aux, cls2) { return '<div class="h2s' + (cls2 ? " " + cls2 : "") + '"><h2>' + esc(title) + '</h2>' + (aux ? '<span class="aux">' + aux + '</span>' : '') + '</div>'; }

  // ════════════════ 차트 ════════════════
  function sparkSVG(vals, w, h, base) {
    if (!vals || vals.length < 2) return '<svg class="spark" width="' + w + '" height="' + h + '" aria-hidden="true"></svg>';
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (base != null) { lo = Math.min(lo, base); hi = Math.max(hi, base); }
    var r = (hi - lo) || 1, n = vals.length, P = 2;
    function Y(v) { return (P + (1 - (v - lo) / r) * (h - 2 * P)).toFixed(1); }
    var pts = vals.map(function (v, i) { return (i * w / (n - 1)).toFixed(1) + "," + Y(v); }).join(" ");
    var ref = base != null ? base : vals[0];
    var col = vals[n - 1] >= ref ? "var(--up)" : "var(--down)";
    var s = '<svg class="spark" viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '" preserveAspectRatio="none" aria-hidden="true">';
    if (base != null) s += '<line x1="0" x2="' + w + '" y1="' + Y(base) + '" y2="' + Y(base) + '" stroke="var(--mut2)" stroke-width=".8" stroke-dasharray="2 2"/>';
    return s + '<polyline points="' + pts + '" fill="none" stroke="' + col + '" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>';
  }
  // 장중 추이 — 기준선(전일 종가) + 룰 선(D1·게이트 등). slots=정규장 5분봉 개수(진행 중이면 오른쪽이 빈다)
  function areaChart(vals, base, o) {
    o = o || {};
    if (!vals || vals.length < 2) return '<div class="empty sm">추이 데이터 없음</div>';
    var W = 340, H = o.h || 140, PT = 12, PB = 20, n = vals.length, slots = Math.max(n, o.slots || n);
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (base != null) { lo = Math.min(lo, base); hi = Math.max(hi, base); }
    var span = (hi - lo) || hi * 0.01 || 1, off = [];
    (o.lines || []).forEach(function (l) {
      if (l.v >= lo - span * 0.8 && l.v <= hi + span * 0.8) { lo = Math.min(lo, l.v); hi = Math.max(hi, l.v); l.inr = true; } else off.push(l);
    });
    var r = (hi - lo) || 1;
    function X(i) { return i * (W - 4) / (slots - 1) + 2; }
    function Y(v) { return PT + (1 - (v - lo) / r) * (H - PT - PB); }
    var ref = base != null ? base : vals[0], last = vals[n - 1];
    var col = last >= ref ? "var(--up)" : "var(--down)";
    var pts = vals.map(function (v, i) { return X(i).toFixed(1) + "," + Y(v).toFixed(1); });
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" role="img" aria-label="' + esc(o.label || "추이") + '" style="display:block">';
    s += '<path d="M' + pts.join(" L") + ' L' + X(n - 1).toFixed(1) + ',' + (H - PB) + ' L' + X(0).toFixed(1) + ',' + (H - PB) + ' Z" fill="' + col + '" opacity=".07"/>';
    if (base != null) s += '<line x1="0" x2="' + W + '" y1="' + Y(base).toFixed(1) + '" y2="' + Y(base).toFixed(1) + '" stroke="var(--mut2)" stroke-dasharray="3 3" stroke-width="1"/>'
      + '<text x="' + (W - 2) + '" y="' + (Y(base) - 4).toFixed(1) + '" text-anchor="end" font-size="9.5" fill="var(--mut)">전일 ' + esc(o.fmt ? o.fmt(base) : num2(base)) + '</text>';
    (o.lines || []).forEach(function (l) {
      if (!l.inr) return;
      s += '<line x1="0" x2="' + W + '" y1="' + Y(l.v).toFixed(1) + '" y2="' + Y(l.v).toFixed(1) + '" stroke="' + (l.color || "var(--accent)") + '" stroke-width="1" opacity=".8"/>'
        + '<text x="3" y="' + (Y(l.v) - 4).toFixed(1) + '" font-size="9.5" font-weight="600" fill="' + (l.color || "var(--accent)") + '">' + esc(l.label) + '</text>';
    });
    s += '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + col + '" stroke-width="1.8" stroke-linejoin="round"/>';
    s += '<circle cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(last).toFixed(1) + '" r="3.2" fill="' + col + '"/>';
    if (o.left) s += '<text x="2" y="' + (H - 5) + '" font-size="9.5" fill="var(--mut)">' + esc(o.left) + '</text>';
    if (o.right) s += '<text x="' + (W - 2) + '" y="' + (H - 5) + '" text-anchor="end" font-size="9.5" fill="var(--mut)">' + esc(o.right) + '</text>';
    s += '</svg>';
    if (off.length) s += '<div class="xs mut" style="margin-top:4px">' + off.map(function (l) { return esc(l.label) + (l.gap != null ? ' (' + pct(l.gap, 1) + ')' : ''); }).join(" · ") + ' — 차트 범위 밖</div>';
    return s;
  }
  function lineChart(hist, cur) {
    var c = (hist && hist.closes) || [], dts = (hist && hist.dates) || [];
    if (c.length < 2) return '<div class="empty sm">시계열 데이터 없음</div>';
    var last = c[c.length - 1], first = c[0], ch = (last - first) / first * 100;
    var fmt = function (v) { return cur === "USD" ? v.toFixed(2) : num(Math.round(v)); };
    return '<div class="chart-h"><span class="bold num">' + fmt(last) + '</span><span class="sm num ' + cls(ch) + '">' + pct(ch) + ' <span class="mut">(' + c.length + '일)</span></span></div>'
      + areaChart(c, null, { h: 110, left: dts[0], right: dts[dts.length - 1], fmt: fmt, label: "1개월 추이" });
  }
  function flowChart(flows) {
    var ser = (flows && flows.series) || [];
    if (!ser.length) return '<div class="empty sm">수급 데이터 없음</div>';
    var W = 320, H = 150, BL = 22, TOP = 8, vals = [];
    ser.forEach(function (d) { ["foreign", "inst", "indiv"].forEach(function (k) { if (d[k] != null) vals.push(Math.abs(d[k])); }); });
    var maxA = Math.max.apply(null, vals) || 1, zoneH = (H - BL - TOP) / 2, zeroY = TOP + zoneH;
    var gw = W / ser.length, bw = gw * 0.22, colors = { foreign: "var(--c-foreign)", inst: "var(--c-inst)", indiv: "var(--c-indiv)" };
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="display:block" role="img" aria-label="투자자별 순매수">';
    s += '<line x1="0" y1="' + zeroY + '" x2="' + W + '" y2="' + zeroY + '" stroke="var(--c-axis)" stroke-width="1"/>';
    ser.forEach(function (d, gi) {
      var cx = gi * gw + gw / 2;
      ["foreign", "inst", "indiv"].forEach(function (k, ki) {
        var v = d[k], bx = cx + (ki - 1) * (bw + 1.5) - bw / 2;
        if (v == null) return;
        var hh = Math.abs(v) / maxA * zoneH, y = v >= 0 ? zeroY - hh : zeroY;
        s += '<rect x="' + bx.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(hh, 0.5).toFixed(1) + '" fill="' + colors[k] + '" rx="1"/>';
      });
      if (gi % Math.max(1, Math.round(ser.length / 6)) === 0 || gi === ser.length - 1)
        s += '<text x="' + cx.toFixed(1) + '" y="' + (H - 8) + '" fill="var(--c-clabel)" font-size="8" text-anchor="middle">' + esc(d.date.slice(5)) + '</text>';
    });
    s += '</svg><div class="row wrap" style="gap:10px;margin-top:6px;font-size:11.5px">'
      + '<span><span class="lg" style="background:var(--c-foreign)"></span>외국인</span><span><span class="lg" style="background:var(--c-inst)"></span>기관</span>'
      + '<span><span class="lg" style="background:var(--c-indiv)"></span>개인</span><span class="mut" style="margin-left:auto">위 순매수 · 아래 순매도(억원)</span></div>';
    return s;
  }

  // ════════════════ 공용 컴포넌트 ════════════════
  function topbar(o) {
    var h = '<header class="topbar"><div class="tb-row">';
    if (o.back) h += '<a class="tb-back" href="' + o.back + '">' + IC.back + esc(o.backLabel || "뒤로") + '</a>';
    else if (o.brand) h += '<div class="hdr-brand">정훈 증권</div>';
    else h += '<div class="tb-title">' + esc(o.title) + '</div>';
    h += '<div class="tb-actions">' + (o.code ? '<span class="tb-code">' + esc(o.code) + '</span>' : '') + '<button class="live-pill" id="livepill" type="button"></button>'
      + (o.code ? '' : '<button class="iconbtn" id="themebtn" type="button" aria-label="' + esc(themeLabel()) + '">' + themeIcon() + '</button>') + '</div></div></header>';
    if (o.back && o.title) h += '<div class="subtitle">' + esc(o.title) + '</div>';
    if (o.sub) h += '<div class="tb-sub">' + o.sub + '</div>';
    return h;
  }
  function sec(title, count, moreHref, moreLabel) {
    return '<div class="sec"><h2>' + esc(title) + (count != null ? '<span class="cnt">' + count + '</span>' : '') + '</h2>'
      + (moreHref ? '<a class="more" href="' + moreHref + '">' + esc(moreLabel || "전체") + '</a>' : '') + '</div>';
  }
  function foot(extra) {
    var h = '<div class="foot">';
    if (extra) h += extra + '<br>';
    h += '분석 ' + esc(D.as_of || "") + ' · 빌드 ' + esc(D.generated_at || "");
    if (LIVE) h += '<br>실시간 ' + esc(LIVE.generated_at || "") + ' (' + (LIVE.src === "cloud" ? "클라우드" : "로컬") + ')';
    return h + '<br>투자 자문 아님 · 최종 결정은 정훈</div>';
  }

  // 국내 지정가 접수 가능성 카드(밴드)
  function bandCard(o) {
    var tk = o.ticker, st = find(tk), bb = bandBase(tk);
    if (!bb || !bb.base) return "";
    var band = krBand(bb.base), P = o.price, ok = P <= band.up && P >= band.lo;
    var q = Q(tk), cur = q && q.p != null ? q.p : (st && st.price);
    var sell = /매도|트림|익절/.test(o.action || o.label || "");
    var h = '<div class="todo ' + (ok ? "go" : "alert") + '"><div class="h"><div class="flex1"><div class="t">' + esc(st ? st.label : tk) + ' ' + (sell ? "매도" : "매수") + ' '
      + (o.shares != null && !isNaN(o.shares) ? esc(o.shares) + '주 · ' : '') + '<span class="num">' + won(P) + '</span></div>'
      + '<div class="d">' + esc(bb.when) + ' 가격제한 ' + won(band.lo) + ' ~ ' + won(band.up) + ' · 기준 ' + won(bb.base) + '(' + esc(bb.basis) + ')</div></div>'
      + '<span class="pill ' + (ok ? "ok" : "no") + '">' + (ok ? "접수 가능" : "접수 불가") + '</span></div>';
    // 밴드 막대: 하한~상한 + 주문가·현재가
    var lo = Math.min(band.lo, P, cur || P), hi = Math.max(band.up, P, cur || P), r = (hi - lo) || 1;
    function L(v) { return ((v - lo) / r * 100).toFixed(1) + "%"; }
    function E(v) { var f = (v - lo) / r; return f > 0.8 ? " er" : f < 0.2 ? " el" : ""; }  // 가장자리 라벨은 안쪽으로
    h += '<div class="band"><div class="track"><div class="fill" style="left:' + L(band.lo) + ';width:' + ((band.up - band.lo) / r * 100).toFixed(1) + '%"></div>';
    if (cur != null) h += '<div class="mark bot' + E(cur) + '" style="left:' + L(cur) + '"><span>현재 ' + num(Math.round(cur)) + '</span></div>';
    h += '<div class="mark top order' + (ok ? " in" : "") + E(P) + '" style="left:' + L(P) + '"><span>주문 ' + num(P) + '</span></div></div></div>';
    if (!ok && sell && P > band.up) {
      // 상한 = floor(기준×1.3, 호가) ≥ 주문가 를 만족하는 가장 낮은 '실제로 찍힐 수 있는' 종가
      var need = Math.ceil(P / 1.3 / krTick(P / 1.3)) * krTick(P / 1.3);
      while (krBand(need).up < P) need += krTick(need);
      h += '<div class="d">주문가가 상한보다 <b>' + won(P - band.up) + '</b> 높습니다. 종가가 <b class="num">' + won(need) + '</b> 이상(호가단위 ' + num(krTick(need)) + '원)이어야 다음 날 접수됩니다.</div>';
    }
    if (bb.preview != null) {
      var pb = krBand(bb.preview), okN = P <= pb.up && P >= pb.lo;
      h += '<div class="d mut">장중 현재가로 끝나면 다음 거래일 상한 ' + won(pb.up) + ' → ' + (okN ? "접수 가능" : "접수 불가") + ' (추정)</div>';
    }
    // 같은 종목의 등록선·접수 알림
    alertsLive().filter(function (a) { return a.ticker === tk && /등록선|접수|익절|트림/.test(a.id); }).forEach(function (a) {
      h += '<div class="d"><span class="pill ' + (a.lfired ? "warn" : "") + '">' + (a.lfired ? "점등" : "대기") + '</span> ' + esc(cleanId(a.id)) + '</div>';
    });
    return h + '</div>';
  }

  function alertRows(list) {
    if (!list.length) return '<div class="empty sm">가까운 가격 알림이 없어요.</div>';
    var h = '<div class="card" style="padding:4px 15px">';
    list.forEach(function (a) {
      var d = a.ldist, lvl = a.cond === "between" ? fmtP(a.low, a.ticker) + '~' + fmtP(a.high, a.ticker) : fmtP(a.level, a.ticker);
      var close = d == null ? 0 : Math.max(0, 100 - Math.min(100, Math.abs(d) * 10));
      var tag = a.lfired ? (a.was === false ? '<span class="pill no">새로 발동</span>' : '<span class="pill warn">발동 중</span>')
        : a._undone ? '<span class="pill info">해제됨</span>' : '<div class="dist num">' + pct(d, 1) + '</div><div class="s">남은 거리</div>';
      h += '<div class="arow' + (a.lfired ? " fired" : "") + '"><div><div class="t">' + esc(cleanId(a.id)) + '</div>'
        + '<div class="s num">지금 ' + fmtP(a.lp, a.ticker) + ' → 기준 ' + lvl + '</div></div>'
        + '<div class="r">' + tag + '</div>'
        + '<div class="meter"><i style="width:' + (a.lfired ? 100 : close).toFixed(0) + '%"></i></div></div>';
    });
    return h + '</div>';
  }

  function dirPill(d) {
    if (d === "↑") return '<span class="pill no" style="background:var(--bad-soft);color:var(--up)">상방</span>';
    if (d === "↓") return '<span class="pill info">하방</span>';
    return '<span class="pill">중립</span>';
  }

  // 할 일(정본 done=true는 잠금 · 그 외 탭 토글 = 이 폰 임시저장)
  var LS_TASK = "jh_task_done";
  function lsTasks() { try { return JSON.parse(localStorage.getItem(LS_TASK) || "{}"); } catch (e) { return {}; } }
  function lsSetTask(id, v) { try { var m = lsTasks(); if (v) m[id] = 1; else delete m[id]; localStorage.setItem(LS_TASK, JSON.stringify(m)); } catch (e) {} }
  function taskDone(t) { return !!(t.done || lsTasks()[t.id]); }
  function checkRow(t) {
    var d = taskDone(t), lock = !!t.done;
    return '<button type="button" class="check' + (d ? " done" : "") + (lock ? " lock" : " tog") + '" data-id="' + esc(t.id) + '"' + (lock ? ' aria-disabled="true"' : '') + ' aria-pressed="' + d + '">'
      + '<span class="box">' + IC.check + '</span><span class="tx">' + mdInline(esc(t.text)) + '</span>' + (lock ? '<span class="lk">정본</span>' : '') + '</button>';
  }
  function bindChecks() {
    Array.prototype.forEach.call(root.querySelectorAll(".check.tog, .chk.tog"), function (b) {
      b.addEventListener("click", function () { var id = b.getAttribute("data-id"); lsSetTask(id, !lsTasks()[id]); rerender(); });
    });
  }

  // 문자열 레벨 파싱(목표가·트림 서술) — 가격 사다리용. 현재가의 0.3~3.5배 밖은 버린다(오파싱 방지)
  function parsePrices(text, tk, ref) {
    var s = String(text || ""), out = [], re = kindOf(tk) === "krw" ? /([\d]{1,3}(?:,\d{3})+|\d{4,7})\s*원/g : /\$\s?([\d,]+(?:\.\d+)?)/g, m;
    while ((m = re.exec(s))) { var v = +m[1].replace(/,/g, ""); if (v && (!ref || (v > ref * 0.3 && v < ref * 3.5))) out.push({ v: v, i: m.index }); }
    return out;
  }
  function centerOf(text, tk, ref) {
    var s = String(text || ""), i = s.indexOf("중심");
    if (i < 0) return null; var p = parsePrices(s.slice(i), tk, ref); return p.length ? p[0].v : null;
  }

  // ════════════════ 화면: 오늘 (캔버스 Main) ════════════════
  var SESS_KR = { reg: "국내 장중", pre: "국내 프리마켓", post: "국내 애프터마켓" }, SESS_US = { reg: "미국 장중", pre: "미국 프리마켓", post: "미국 애프터마켓" };
  function marketLine() {
    var m = (LIVE && LIVE.market) || {}, t = kstDate(), out = [];
    out.push(SESS_KR[m.kr] || (!isKrSession(t) ? "국내 휴장" : kstMin() < 9 * 60 ? "국내 개장 전" : "국내 장 마감"));
    out.push(SESS_US[m.us] || "미국 장 마감");
    return out.join(" · ");
  }
  function todayLong() { var d = kst(); return (d.getUTCMonth() + 1) + "월 " + d.getUTCDate() + "일 " + "일월화수목금토".charAt(d.getUTCDay()) + "요일"; }
  var LADDER_SHORT = { ok: "다음 단계 미도달", watch: "사다리 해금", spent: "사다리 상한 소진", freeze: "하드플로어 정지", rule6: "룰6 우선 — 기록만", unknown: "시세 미확인" };

  // 걸 주문 카드(접수 가능) · 걸지 말 것 카드(밴드 밖)
  function orderCard(o) {
    var e = bandEval(o); if (!e) return "";
    var st = find(o.ticker), name = st ? st.label : o.ticker, base = e.bb.base, gap = (e.P / base - 1) * 100;
    var held = (D.holdings || []).filter(function (x) { return x.ticker === o.ticker; })[0];
    var verb = /익절/.test(o.action || "") ? "익절" : e.sell ? "트림" : "매수", dl = relDay(e.bb.day);
    if (!e.ok) {
      var vals = [base, e.sell ? e.band.up : e.band.lo, e.P], lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), sp = (hi - lo) || 1;
      lo -= sp * 0.1; hi += sp * 0.1;
      var L = function (v) { return ((v - lo) / (hi - lo) * 100).toFixed(1) + "%"; };
      var h = '<div class="ocard no"><div class="hd"><span class="chip bad">' + IC.x + '걸지 말 것</span><span class="when">접수 거부 예정</span></div>';
      h += '<div class="ttl2">' + esc(name) + ' ' + num(e.P) + '원 ' + verb + ' — ' + dl + '엔 안 들어간다</div>';
      h += '<div><div class="bband"><div class="okz" style="' + (e.sell ? 'left:0;width:' + L(e.band.up) : 'left:' + L(e.band.lo) + ';right:0;border-radius:0 5px 5px 0') + '"></div>'
        + '<div class="base" style="left:' + L(base) + '"></div><div class="cap" style="left:' + L(e.sell ? e.band.up : e.band.lo) + '"></div><div class="odot" style="left:' + L(e.P) + '"></div></div>'
        + '<div class="bband-l num" style="margin-top:8px"><span>종가 ' + num(base) + '</span><span>' + (e.sell ? "상한가 " + num(e.band.up) : "하한가 " + num(e.band.lo)) + '</span><b>' + verb + ' ' + num(e.P) + '</b></div></div>';
      if (e.need) {
        var s2 = sessionAfter(e.bb.day), last = dayDiff(s2, sessionAfter(s2)) > 3;
        h += '<p>가격은 유지한다. ' + dl + ' 종가가 <b class="num">' + won(e.need) + '</b>(' + pct((e.need / base - 1) * 100, 1) + ') 이상이면 ' + mdw(s2) + '분을 건다' + (last ? ' — 연휴 전 마지막 기회.' : '.') + '</p>';
      }
      return h + '<a class="lnk" href="#stock/' + encodeURIComponent(o.ticker) + '">' + esc(name) + ' 판정 보기' + IC.chev + '</a></div>';
    }
    var reg = isReg(o), live = e.bb.when === "오늘" && kstMin() >= 9 * 60;
    var subs = [(o.shares != null ? esc(o.shares) + "주" : ""), "지정가", held && +o.shares >= held.shares ? "전량" : "", st ? "★" + st.stars + (e.sell ? " " + verb : "") : ""].filter(Boolean);
    var h2 = '<div class="ocard' + (reg ? " done" : "") + '"><div class="hd"><span class="chip acc">' + IC.clock + (live ? "지정가 주문 · 국내" : "예약 주문 · 국내") + '</span><span class="when">' + (live ? "오늘 15:30까지" : "마감 " + mdw(e.bb.day) + " 09:00") + '</span></div>';
    h2 += '<div class="body"><div><div class="ttl">' + esc(name) + ' ' + (e.sell ? "매도" : "매수") + '</div><div class="sub">' + subs.join(" · ") + '</div></div>'
      + '<div class="r"><div class="pr num">' + won(e.P) + '</div><div class="sub num">' + (e.bb.final ? "종가 " : "기준 ") + num(base) + ' · ' + pct(gap, 1) + (gap >= 0 ? " 위" : " 아래") + '</div></div></div>';
    h2 += '<div class="ok">' + IC.check + '<span>접수 가능 — ' + dl + ' ' + (e.sell ? "상한가 " + won(e.band.up) + " 안" : "하한가 " + won(e.band.lo) + " 위") + (reg ? " · 이 폰에 등록 표시됨" : "") + '</span></div>';
    if (e.bb.preview != null) {
      var pb = krBand(e.bb.preview), okN = e.P <= pb.up && e.P >= pb.lo;
      h2 += '<div class="ok' + (okN ? "" : " warn") + '">' + (okN ? IC.check : IC.alert) + '<span>지금 가격으로 끝나면 다음 거래일 ' + (okN ? "접수 가능" : "접수 불가") + '(상한 ' + won(pb.up) + ' · 추정)</span></div>';
    }
    h2 += '<div class="btnrow"><button type="button" class="btn-ink" data-reg="' + esc(o.id) + '" aria-pressed="' + reg + '" title="이 폰에만 저장 — 영구 기록은 채팅으로">' + (reg ? "등록 완료 · 되돌리기" : "등록했어요") + '</button>'
      + '<a class="btn-line" href="' + tossUrl(o.ticker) + '" target="_blank" rel="noopener">토스 열기</a></div>';
    return h2 + '</div>';
  }
  function chkRow(t) {
    var d = taskDone(t), lock = !!t.done;
    return '<button type="button" class="chk' + (d ? " done" : "") + (lock ? "" : " tog") + '" data-id="' + esc(t.id) + '" aria-pressed="' + d + '"' + (lock ? ' aria-disabled="true"' : '') + '>'
      + '<span class="bx">' + IC.check + '</span><span class="t">' + mdInline(esc(t.text)) + '</span>' + (lock ? '<span class="s">정본</span>' : '') + '</button>';
  }
  function eventsLive() {
    var t = kstDate();
    return (D.events || []).filter(function (e) { return (e.end || e.date) >= t; }).map(function (e) { return Object.assign({}, e, { du: dayDiff(t, e.date) }); });
  }
  function calRow(e) {
    var d = md(e.date) + " " + "일월화수목금토".charAt(new Date(e.date + "T00:00:00Z").getUTCDay());
    if (e.end && e.end !== e.date) d = md(e.date) + "–" + (e.end.slice(5, 7) === e.date.slice(5, 7) ? +e.end.slice(8) : md(e.end));
    else { var tm = String(e.note || "").match(/^(\d{1,2}:\d{2})\s*KST/); if (tm) d = md(e.date) + " " + tm[1]; }
    var r = e.du <= 0 ? '<span class="r dd">' + ((e.end || e.date) > kstDate() && e.du < 0 ? "진행 중" : "오늘") + '</span>'
      : e.du <= 2 ? '<span class="r dd">D-' + e.du + '</span>' : '<span class="r">' + esc(e.tag || "D-" + e.du) + '</span>';
    var t = e.type === "earnings" ? e.label + " 실적" : e.label;
    return '<div class="cal" title="' + esc(e.note || "") + '"><div class="d num">' + esc(d) + '</div><div class="t">' + esc(t) + (e.confidence && e.confidence !== "확정" ? '<small>' + esc(e.confidence) + '</small>' : '') + '</div>' + r + '</div>';
  }

  // ★[9/21] 토스 미체결 ↔ 계획 대조(order_check.py) — 앱이 잘못 띄운 주문이 토스에 '걸린 채' 남는 걸
  //   앱이 스스로 보여준다. 舊엔 계획표만 보여줘서 NAVER 196,400(폐기 오더)가 접수된 걸 아무도 못 봤다.
  //   🔴는 3일, 🟡는 1일까지만 띄운다(오래된 대조는 지금의 토스 상태가 아니다).
  function orderCheckCards() {
    var oc = D.order_check;
    if (!oc || !oc.checked_at) return "";
    var at = String(oc.checked_at), age = dayDiff(at.slice(0, 10), kstDate());
    if (oc.source === "unavailable") return "";
    if (age > 3) return "";
    var bad = (oc.findings || []).filter(function (f) { return f.level === "red" || (f.level === "yellow" && age <= 1); });
    if (!bad.length) return "";
    var g = {}, keys = [];
    bad.forEach(function (f) {
      var i = f.msg.indexOf(" — "), k = i > 0 ? f.msg.slice(0, i) : f.msg;
      if (!g[k]) { g[k] = { red: false, why: [], tk: f.ticker }; keys.push(k); }
      if (f.level === "red") g[k].red = true;
      if (i > 0) g[k].why.push({ t: f.msg.slice(i + 3), red: f.level === "red" });
    });
    return keys.map(function (k) {
      var x = g[k];
      return '<div class="ocard no"><div class="hd"><span class="chip ' + (x.red ? "bad" : "acc") + '">' + IC.x + (x.red ? "토스에서 취소" : "확인 필요") + '</span><span class="when">토스 대조 ' + esc(md(at)) + ' ' + esc(at.slice(11, 16)) + '</span></div>'
        + '<div class="ttl2">' + esc(k.replace(/ ([\d,.]+) × ([\d.]+)$/, " $1원 × $2주")) + ' — 토스에 걸려 있다</div>'
        + x.why.map(function (w) { return '<div class="ok ' + (w.red ? "no" : "warn") + '">' + IC.x + '<span>' + esc(w.t) + '</span></div>'; }).join("")
        + '<p>주문 취소는 토스 앱에서 직접. 이 앱과 데스크는 주문을 건드리지 않는다.</p></div>';
    }).join("");
  }

  function renderToday() {
    var hs = holdingsLive(), T = totalsLive(hs), L = ladderLive(), G = gatesLive(), s = D.safety || {}, UT = usTrack();
    var r0 = (D.reports || [])[0];
    var h = topbar({ brand: true });
    h += '<div class="hdr-date">' + esc(todayLong()) + ' · ' + esc(marketLine())
      + (r0 ? ' · <a class="acc" href="#report/' + encodeURIComponent(r0.id) + '">v' + esc(r0.version != null ? r0.version : "") + ' 보고서</a>' : '') + '</div>';

    // 자산 카드
    h += '<section class="asset" aria-label="자산 요약"><div class="top"><span>총자산 · ' + (liveOn() ? "실시간 평가 " + hhmm(LIVE.ts) : "보고서 시세") + '</span>'
      + '<b class="num ' + cls(T.day) + '">' + sign(T.day) + num(Math.round(T.day)) + '원 · ' + pct(T.dayPct) + '</b></div>';
    h += '<div class="big num">' + num(Math.round(T.assets)) + '<small>원</small></div>';
    h += '<div class="g3"><div><span class="k">현금</span><span class="v num">' + num(Math.round(T.cashK + T.cashUK)) + '</span><span class="s num">₩' + num(T.cashK) + ' + $' + num2(T.cashU) + '</span></div>'
      + '<div><span class="k">평가손익 · 환 반영</span><span class="v num ' + cls(T.pnl) + '">' + sign(T.pnl) + num(Math.round(T.pnl)) + '</span><span class="s num">' + pct(T.pnlPct, 1) + ' · 환 빼면 ' + sign(T.pnlNoFx) + num(Math.round(T.pnlNoFx)) + '</span></div>'
      + '<div><span class="k">살 수 있는 돈</span><span class="v num acc">' + (UT.ok ? usd(UT.allowed) : won(L.allowed)) + '</span><span class="s">' + (UT.ok ? esc(US_SHORT[UT.u.status] || "") + ' · 국내 ' + won(L.allowed) : esc(LADDER_SHORT[L.status] || "")) + (L.live ? " · 장중 추정" : "") + '</span></div></div></section>';

    // 오늘 밤(지금) 할 일
    var ko = activeKrOrders(), cards = ko.map(function (o) { return { o: o, e: bandEval(o) }; }).filter(function (x) { return x.e; });
    var okC = cards.filter(function (x) { return x.e.ok; }), noC = cards.filter(function (x) { return !x.e.ok; });
    var today = ((D.tasks || {}).today || []), open = today.filter(function (t) { return !taskDone(t); });
    var night = !isKrSession(kstDate()) || kstMin() >= 15 * 60 + 30 || kstMin() < 7 * 60;
    var nReg = okC.filter(function (x) { return isReg(x.o); }).length;
    h += h2s(night ? "오늘 밤 할 일" : "지금 할 일", (okC.length ? "주문 " + okC.length + "건" + (nReg ? "(" + nReg + " 등록)" : "") + " · " : "") + "할 일 " + open.length + "건");
    h += '<div class="stack">';
    h += orderCheckCards();
    okC.forEach(function (x) { h += orderCard(x.o); });
    noC.forEach(function (x) { h += orderCard(x.o); });
    var fp = flowPair();
    if (fp && !G.on2) {
      h += '<div class="ocard"><div class="hd"><span class="chip info">' + IC.eye + '확인</span><span class="when">' + (G.ftStale ? "오늘 수급 대기" : mdw(nextKrSession()) + " 장 마감 후") + '</span></div>'
        + '<div class="ttl2">외인 순매수, 이틀 연속 나오나</div>'
        + '<div class="flowline num"><span class="' + cls(fp[0].foreign) + '">' + md(fp[0].date) + ' ' + eok(fp[0].foreign) + '</span><span class="mut">→</span><span class="' + cls(fp[1].foreign) + '">' + md(fp[1].date) + ' ' + eok(fp[1].foreign) + '</span><span class="mut">· 순매수 스트릭 ' + G.buyStreak + '일</span></div>'
        + '<p>TF 해제 게이트②는 이 스트릭이 2거래일 이어져야 켜진다.' + (G.ftStale ? ' <b class="warn">' + esc(md(G.last)) + ' 수급이 아직 반영되지 않았다.</b>' : '') + '</p></div>';
    }
    if (open.length) h += '<div class="group">' + open.map(chkRow).join("") + '</div>';
    h += '</div><a class="morelink" href="#plan">계획 · 주문 추적 전체' + IC.chev + '</a>';

    // 룰 요약 링크
    h += '<a class="rlink" href="#rules"><div class="lad" aria-hidden="true">' + (L.steps || []).map(function (st) { return '<span class="' + (L.dd != null && L.dd <= st.thr ? "on" : "") + '"></span>'; }).join("") + '</div>'
      + '<div class="tx"><span class="k">룰1 사다리 · 급락 TF</span><span class="v num">코스피 ' + num2(L.k) + ' · 고점 대비 ' + pct(L.dd, 1) + '</span>'
      + '<span class="s">국내 ' + won(L.allowed) + (UT.ok ? ' · 미국 ' + usd(UT.allowed) : '') + ' · 해제 게이트 ' + G.n + '/3 · 하드플로어 ' + (s.halted ? "발동" : "미발동") + '</span></div>' + IC.chev + '</a>';

    // 다가오는 일정
    var ev = eventsLive();
    if (ev.length) h += h2s("다가오는 일정", null, "sm") + '<div class="group">' + ev.slice(0, 6).map(calRow).join("") + '</div>';

    // PM 사견
    var pv = D.pm_view || {};
    if (pv.headline) h += '<a class="pmbox" href="#pmview"><span class="lb">PM 사견 · ' + esc(String(pv.as_of || "").slice(0, 10) === kstDate() ? String(pv.as_of).slice(11, 16) : (pv.updated || "")) + '</span><p class="hl2">' + esc(pv.headline) + '</p>'
      + (pv.summary ? '<p>' + esc(pv.summary) + '</p>' : '') + '</a>';

    // 시장 — 실시간 스트립 + 코스피 장중
    var MK = [["^KS11", "코스피"], ["^KQ11", "코스닥"], ["^GSPC", "S&P 500"], ["^IXIC", "나스닥"], ["^SOX", "필라델피아 반도체"], ["KRW=X", "원/달러"], ["CL=F", "WTI"]];
    h += h2s("시장", liveOn() ? "실시간 " + hhmm(LIVE.ts) : "보고서 시세", "sm") + '<div class="strip" role="list">';
    MK.forEach(function (m) {
      var q = Q(m[0]), idx = (D.indices || []).filter(function (x) { return x.ticker === m[0]; })[0];
      var p = q && q.p != null ? q.p : (idx ? idx.price : (m[0] === "KRW=X" ? D.fx && D.fx.usdkrw : null));
      var c = q && q.c != null ? q.c : (idx ? idx.change_pct : null);
      if (p == null) return;
      var ser = S(m[0]);
      h += '<div class="mk" role="listitem"><div class="n"><span>' + esc(m[1]) + '</span>' + sessTag(q) + '</div><div class="p num">' + (m[0] === "CL=F" ? "$" + num2(p) : fmtP(p, m[0])) + '</div>'
        + '<div class="c num ' + cls(c) + '">' + pct(c) + '</div>' + (ser ? sparkSVG(ser, 108, 24, q ? (q.x ? q.rpc : q.pc) : null) : '') + '</div>';
    });
    h += '</div>';
    var kq = Q("^KS11"), kser = S("^KS11");
    if (kser && kq) {
      var lines = [];
      if (s.peak) (s.steps || []).forEach(function (st) { var v = s.peak * (1 + st.thr / 100); lines.push({ v: v, label: st.label + " " + num(Math.round(v)), color: "var(--accent)", gap: (v / kq.p - 1) * 100 }); });
      if (G.g1) lines.push({ v: G.g1.level, label: "게이트① " + num(G.g1.level), color: "var(--good)", gap: (G.g1.level / kq.p - 1) * 100 });
      h += '<div class="card"><div class="chart-h"><span><b class="num" style="font-size:18px">' + num2(kq.p) + '</b> <span class="num ' + cls(kq.c) + '">' + pct(kq.c) + '</span></span><span class="xs mut">코스피 장중 ' + sessTag(kq) + '</span></div>'
        + areaChart(kser, kq.pc, { slots: 78, lines: lines, left: "09:00", right: "15:30", label: "코스피 장중 추이" }) + '</div>';
    }

    // 가격 알림 — ①보고서 이후 새로 넘어선 것 ②풀린 것 ③아직 안 닿은 것 중 가까운 순(이미 발동 상태는 룰 화면)
    var al = alertsLive().filter(function (a) { return !/TF|룰6|S2/.test(a.id); });
    var fresh = al.filter(function (a) { return a.lfired && !a.was; });
    var undone = al.filter(function (a) { return a.lfired === false && a.was; });
    var pend = al.filter(function (a) { return a.lfired === false && !a.was; }).sort(function (a, b) { return Math.abs(a.ldist) - Math.abs(b.ldist); });
    h += h2s("가격 알림", fresh.length ? '<b class="bad">' + fresh.length + '건 새로 발동</b>' : '<a class="aux" href="#rules">전체 ' + al.length + '</a>', "sm");
    h += alertRows(fresh.concat(undone.map(function (a) { return Object.assign({}, a, { _undone: 1 }); }), pend.slice(0, Math.max(3, 5 - fresh.length - undone.length))));

    // 장 전망 — 오늘·내일
    var ol = D.outlook || [];
    if (ol.length) {
      h += h2s("장 전망", '<a class="aux" href="#plan">이번주·이번달</a>', "sm") + '<div class="card" style="padding:2px 15px">';
      ol.slice(0, 2).forEach(function (o) { h += '<div class="olrow"><div class="h"><b>' + esc(o.tag || o.horizon || "") + '</b>' + dirPill(o.dir) + '</div><div class="tx">' + esc(o.text) + '</div></div>'; });
      h += '</div>';
    }
    h += foot();
    paint(h); bindChecks();
    Array.prototype.forEach.call(root.querySelectorAll("[data-reg]"), function (b) {
      b.addEventListener("click", function () { toggleReg(b.getAttribute("data-reg")); rerender(); });
    });
  }

  // ════════════════ 화면: 포트폴리오 (캔버스 Portfolio) ════════════════
  var pfTab = "hold";
  // 보유 종목의 '다음 행동' 칩 — 국내 지정가가 있으면 접수 판정, 없으면 트림·매수존 서술의 첫 마디
  function holdNext(x) {
    var o = activeKrOrders(true).filter(function (y) { return y.ticker === x.ticker; })[0];
    if (o) {
      var e = bandEval(o), k = orderKind(o), verb = /익절/.test(o.action || "") ? "익절" : e && e.sell ? "트림" : "매수";
      if (e) {
        var g = pct((e.P / (x.lp || e.bb.base) - 1) * 100, 1), rl = regLine(x.ticker);
        if (k !== "wait") return { t: verb + " " + num(e.P) + " · " + g + (rl ? " · 등록선 " + num(rl.level) + (rl.lfired ? " 점등" : "") : " · " + ORDER_LBL[k]), c: rl && rl.lfired ? "acc" : "" };
        if (e.ok) return { t: verb + " " + num(e.P) + " · " + g + " · " + relDay(e.bb.day) + "분 " + (isReg(o) ? "등록 표시됨" : "등록 필요"), c: "acc" };
        return { t: verb + " " + num(e.P) + " · " + relDay(e.bb.day) + " 접수 불가(상한 " + num(e.band.up) + ")", c: "bad" };
      }
    }
    var t = shortTxt(x.trim) || shortTxt(x.buy_zone);
    return t ? { t: t, c: "" } : null;
  }
  function pfRow(x, isHold, nx, tint) {
    var tk = x.ticker, code = isKR(tk) ? tk.slice(0, 6) : tk, q = Q(tk);
    var p = isHold ? x.lp : px(x), c = isHold ? x.lc : chg(x);
    var r = '<a class="gi' + (tint ? " tint" : "") + '" href="#stock/' + encodeURIComponent(tk) + '">';
    r += '<div class="l1"><div class="nm"><b>' + esc(x.label) + '</b>' + (code !== x.label ? '<span class="cd">' + esc(code) + '</span>' : '') + (q && q.x ? sessTag(q) : '') + '</div><div class="px num">' + fmtP(p, tk) + IC.chev + '</div></div>';
    r += '<div class="l2"><span class="lf">' + bars5(x.stars) + '<b class="num">' + (x.score != null ? x.score : "—") + '</b>' + (isHold && x.w != null ? '<span class="num">· 비중 ' + x.w.toFixed(1) + '%</span>' : '') + '</span>'
      + '<span class="rt num"><span class="' + cls(c) + '">' + pct(c) + '</span>' + (isHold ? ' <span class="mut">· 원가</span> <span class="' + cls(x.lpnlpct) + '">' + pct(x.lpnlpct) + '</span>' : '') + '</span></div>';
    if (nx && nx.t) r += '<span class="chip ' + (nx.c || "") + '">' + esc(nx.t) + '</span>';
    return r + '</a>';
  }
  function renderPf() {
    var hs = holdingsLive(), T = totalsLive(hs), L = ladderLive(), UT = usTrack();
    var h = topbar({ title: "포트폴리오", sub: '주식 ' + won(T.stocks) + ' · ' + (liveOn() ? "실시간 " + hhmm(LIVE.ts) + "(국내 애프터·미국 프리 포함)" : "보고서 시세") });
    h += '<div class="seg" role="tablist"><button type="button" role="tab" data-t="hold" aria-selected="' + (pfTab === "hold") + '" class="' + (pfTab === "hold" ? "on" : "") + '">보유 ' + hs.length + '</button>'
      + '<button type="button" role="tab" data-t="watch" aria-selected="' + (pfTab === "watch") + '" class="' + (pfTab === "watch" ? "on" : "") + '">워치 ' + (D.watchlist || []).length + '</button></div>';

    // 매수 우선순위(d191) — ① GOOGL · ②③ 워치 buy_zone 접두
    var ws = (D.watchlist || []).map(function (w) {
      var a = alertsLive().filter(function (x) { return x.ticker === w.ticker && /매수존|눌림|편입/.test(x.id); })[0];
      return Object.assign({}, w, { za: a, zd: a ? a.ldist : null });
    });
    var pri = [], g = (D.holdings || []).filter(function (x) { return x.ticker === "GOOGL"; })[0];
    if (g) pri.push({ n: "①", st: g, z: "비중 18% 상한" });
    ws.forEach(function (w) { var m = String(w.buy_zone || "").match(/^([②③④])\s*(.*)/); if (m) pri.push({ n: m[1], st: w, z: w.za ? (w.za.cond === "between" ? fmtP(w.za.low, w.ticker) + "–" + fmtP(w.za.high, w.ticker) : fmtP(w.za.level, w.ticker) + " 이하") : shortTxt(m[2], 18), d: w.zd }); });
    pri.sort(function (a, b) { return a.n.localeCompare(b.n); });
    function priCard() {
      if (!pri.length) return "";
      var RK = { "①": "1순위", "②": "2순위", "③": "3순위", "④": "4순위" };
      return h2s("미국 매수 순서", "d191 · d205", "sm") + '<div class="wcard" style="margin-top:0"><div class="pri3">' + pri.map(function (p) {
        return '<a href="#stock/' + encodeURIComponent(p.st.ticker) + '"><span class="n">' + p.n + ' ' + RK[p.n] + '</span><b>' + esc(isKR(p.st.ticker) ? p.st.label : p.st.ticker) + '</b><span class="z">' + esc(p.z) + (p.d != null ? ' · ' + pct(p.d, 1) : '') + '</span></a>';
      }).join("") + '</div><p>' + (UT.ok ? (UT.allowed > 0 ? '미국 트랙 이번 회차 ' + usd(UT.allowed) + ' — 매수존 안 종목 → GOOGL 18%까지 → 나머지 VOO.' : '미국 트랙 ' + esc(US_SHORT[UT.u.status] || "") + (UT.u.next_date ? ' — 다음 회차 ' + esc(mdw(UT.u.next_date)) : '') + '.') : (L.allowed > 0 ? '잔여 ' + won(L.allowed) + ' — 이 순서대로.' : '지금은 못 산다.')) + '</p></div>';
    }

    if (pfTab === "hold") {
      var kw = T.krW, r6 = alertBy(/룰6/), st5 = (((D.fx_exposure || {}).percentile || {}).windows || {})["5y"], stt = D.stats || {};
      var byW = hs.slice().sort(function (a, b) { return b.w - a.w; }), top = byW[0], sec2 = byW[1];
      h += '<div class="wcard"><div class="hrow"><h2>지역 배분 · 룰6</h2>' + (kw == null ? '' : kw > 22 ? '<span class="chip bad">국내 목표 상단 +' + (kw - 22).toFixed(1) + '%p 초과</span>' : kw < 18 ? '<span class="chip info">국내 목표 하단 미달</span>' : '<span class="chip good">목표 밴드 안</span>') + '</div>';
      if (kw != null) {
        h += '<div><div class="rbar-t"><span style="left:20%">목표 18–22%</span></div><div class="rbar" role="img" aria-label="국내 ' + kw.toFixed(1) + '% · 미국 ' + (100 - kw).toFixed(1) + '%"><div class="kr" style="width:' + Math.min(100, kw).toFixed(1) + '%"></div><div class="tg" style="left:18%;width:4%"></div></div>'
          + '<div class="rbar-l num"><b>국내 ' + kw.toFixed(1) + '%</b><span>미국 ' + (100 - kw).toFixed(1) + '%</span></div></div>';
      }
      if (r6) h += '<p>조정은 신규 입금·반등 때만. 국내 트림 착수선 코스피 <b class="num">' + num(r6.level) + '</b>(현재 ' + pct((r6.lp / r6.level - 1) * 100, 1) + ') — ' + (r6.lfired ? "착수선 도달, 트림 검토." : "지금은 팔지 않는다.") + '</p>';
      h += '<div class="stat3"><div><div class="k">달러 비중</div><div class="v num">' + (T.usdW != null ? T.usdW.toFixed(1) + "%" : "—") + '</div>' + (st5 ? '<div class="s">5년 ' + st5.percentile + '%ile ' + (st5.percentile < 30 ? "저평가" : st5.percentile > 70 ? "고평가" : "중립") + '</div>' : '') + '</div>'
        + '<div><div class="k">최대 종목</div><div class="v num">' + (top ? esc(top.label) + ' ' + top.w.toFixed(1) + '%' : "—") + '</div>' + (sec2 ? '<div class="s num">2위 ' + esc(sec2.label) + ' ' + sec2.w.toFixed(1) + '%</div>' : '') + '</div>'
        + '<div><div class="k">실효 분산</div><div class="v num">' + (stt.effective_bets != null ? stt.effective_bets + "종목" : "—") + '</div>' + (stt.effective_bets_weight_only != null ? '<div class="s num">상관 기준 · 비중 ' + stt.effective_bets_weight_only + '</div>' : '') + '</div></div></div>';

      var low = hs.filter(function (x) { return (x.stars || 0) <= 2; }).sort(function (a, b) { return b.w - a.w; });
      var core = hs.filter(function (x) { return (x.stars || 0) > 2; }).sort(function (a, b) { return b.w - a.w; });
      var lowW = low.reduce(function (a, x) { return a + x.w; }, 0);
      if (low.length) {
        h += h2s("결정이 필요한 종목", "★2 · 관망 금지 · 비중 " + lowW.toFixed(1) + "%");
        h += '<div class="group">' + low.map(function (x) { return pfRow(x, true, holdNext(x), true); }).join("") + '</div>';
      }
      h += h2s("코어 · 홀드", "비중 순 · " + core.length + "종목");
      h += '<div class="group">' + core.map(function (x) { return pfRow(x, true, holdNext(x)); }).join("") + '</div>';
      h += priCard();

      h += h2s("분석", null, "sm");
      var pf = D.performance;
      if (pf && pf.status === "live") h += '<details class="fold"><summary>운용 성적 · 매매 효과 ' + pct(pf.desk_value_pct, 1).replace("%", "%p") + '</summary><div class="in">' + perfCard(pf) + '</div></details>';
      h += '<details class="fold"><summary>비중 · 테마 · 수익률</summary><div class="in">' + allocCards(hs) + '</div></details>';
      h += '<details class="fold"><summary>통화 익스포저 · 환손익</summary><div class="in">' + fxCard() + '</div></details>';
      h += '<details class="fold"><summary>동조 · 실효 분산</summary><div class="in">' + corrCard() + '</div></details>';
      h += '<a class="hub" href="#trades"><span class="ic">' + IC.ledger + '</span><div><div class="t">체결 원장 · 실현손익</div><div class="s">' + tradesSub() + '</div></div><span class="chev">' + IC.chev + '</span></a>';
    } else {
      h += priCard();
      ws.sort(function (a, b) {
        var da = a.zd == null ? 999 : Math.abs(a.zd), db = b.zd == null ? 999 : Math.abs(b.zd);
        return da - db || (b.stars || 0) - (a.stars || 0) || (b.score || 0) - (a.score || 0);
      });
      h += h2s("매수존까지 가까운 순", ws.length + "종목");
      h += '<div class="group">' + ws.map(function (w) {
        var pre = (String(w.buy_zone || "").match(/^([②③④])/) || [])[1];
        var nx = w.za ? { t: (pre ? pre + " " : "") + (w.za.cond === "between" ? fmtP(w.za.low, w.ticker) + "–" + fmtP(w.za.high, w.ticker) : fmtP(w.za.level, w.ticker) + " 이하") + (w.za.lfired ? " · 진입" : " · " + pct(w.zd, 1)), c: w.za.lfired ? "good" : "acc" }
          : { t: shortTxt(w.buy_zone, 34) || "존 미등록", c: "" };
        return pfRow(w, false, nx);
      }).join("") + '</div>';
    }
    h += foot();
    paint(h);
    Array.prototype.forEach.call(root.querySelectorAll(".seg button"), function (b) {
      b.addEventListener("click", function () { pfTab = b.getAttribute("data-t"); render(); window.scrollTo(0, 0); });
    });
  }
  function tradesSub() {
    var t = D.trades || {};
    if (t.status !== "live") return "원장 데이터 없음";
    var ed = (t.eras || {}).desk || {};
    return "데스크 이후 실현 " + sign(ed.realized_krw) + num(ed.realized_krw) + "원 · " + (ed.n || 0) + "건 · 승률 " + (ed.win_rate != null ? ed.win_rate : "—") + "%";
  }
  function allocCards(hs) {
    var pal = ["#16181D", "#8A5A0E", "#2A5FCB", "#0B6E4B", "#B42331", "#6B5CA5"];
    var total = hs.reduce(function (a, x) { return a + x.lvalue; }, 0) || 1;
    var byW = hs.slice().sort(function (a, b) { return b.lvalue - a.lvalue; }), top = byW.slice(0, 6), rest = byW.slice(6);
    var restW = rest.reduce(function (a, x) { return a + x.lvalue; }, 0), segs = "", leg = "";
    top.forEach(function (x, i) { var w = x.lvalue / total * 100; segs += '<span style="width:' + w.toFixed(1) + '%;background:' + pal[i] + '"></span>'; leg += '<span class="palg"><i style="background:' + pal[i] + '"></i>' + esc(x.label) + " " + w.toFixed(0) + "%</span>"; });
    if (restW > 0) { var wr = restW / total * 100; segs += '<span style="width:' + wr.toFixed(1) + '%;background:var(--mut2)"></span>'; leg += '<span class="palg"><i style="background:var(--mut2)"></i>기타 ' + wr.toFixed(0) + "%</span>"; }
    var h = '<div class="card"><div class="ctitle">보유 비중 <span class="mut xs">(원화 환산)</span></div><div class="stackbar">' + segs + '</div><div class="palegend">' + leg + '</div></div>';
    var secAgg = {};
    hs.forEach(function (x) { var s = x.sector || "기타"; secAgg[s] = (secAgg[s] || 0) + x.lvalue; });
    h += '<div class="card"><div class="ctitle">테마 집중도</div>' + Object.keys(secAgg).sort(function (a, b) { return secAgg[b] - secAgg[a]; }).map(function (k) {
      var w = secAgg[k] / total * 100;
      return '<div class="rdrow"><span class="rdlabel">' + esc(k) + '</span><div class="secbar"><div class="secseg" style="width:' + w.toFixed(0) + '%;background:var(--accent)"></div></div><span class="rdval mut num">' + w.toFixed(0) + '%</span></div>';
    }).join("") + '</div>';
    var byR = hs.slice().sort(function (a, b) { return (b.lpnlpct || 0) - (a.lpnlpct || 0); });
    var maxA = Math.max.apply(null, byR.map(function (x) { return Math.abs(x.lpnlpct || 0); })) || 1;
    h += '<div class="card"><div class="ctitle">원가 대비 수익률</div>' + byR.map(function (x) {
      var up = (x.lpnlpct || 0) >= 0, w = Math.abs(x.lpnlpct || 0) / maxA * 50;
      return '<div class="rdrow"><span class="rdlabel">' + esc(x.label) + '</span><div class="rdbar"><span class="rdseg ' + (up ? "up" : "down") + '" style="' + (up ? "left:50%" : "right:50%") + ';width:' + w.toFixed(1) + '%"></span></div><span class="rdval num ' + cls(x.lpnlpct) + '">' + pct(x.lpnlpct, 1) + '</span></div>';
    }).join("") + '</div>';
    return h;
  }
  // ★[9/21] 운용 성적표(performance.py) — "우리가 매매로 더했나"를 원장 재생으로 잰다.
  //   舊 stats.period_return_pct는 '현재 비중을 과거에 들고 있었다면'의 백캐스트라 매매 효과를 못 본다.
  function perfCard(p) {
    var a = p.actual || {}, hd = p.hold || {}, b = p.benchmarks || {}, t = (p.trades || {}), bs = t.by_side_krw || {};
    var rows = [["우리 실제", a.stocks_twr_pct, "me"], ["가만히 뒀다면", hd.stocks_twr_pct, ""]];
    Object.keys(b).forEach(function (k) { rows.push([k.replace("혼합(시작 국내비중)", "혼합 국내" + (p.start_kr_weight_pct != null ? Math.round(p.start_kr_weight_pct) + "%" : "")), b[k].twr_pct, ""]); });
    var mx = Math.max.apply(null, rows.map(function (r) { return Math.abs(r[1] || 0); })) || 1;
    var h = '<div class="card"><div class="ctitle">시간가중수익률 <span class="mut xs">(' + esc(md(p.from)) + '–' + esc(md(p.to)) + ' · 입출금 영향 제거)</span></div><div class="pbars">';
    rows.forEach(function (r) { h += '<div class="r ' + r[2] + '"><span>' + esc(r[0]) + '</span><span class="t"><i class="' + cls(r[1]) + '" style="width:' + (Math.abs(r[1] || 0) / mx * 100).toFixed(1) + '%"></i></span><b class="num ' + cls(r[1]) + '">' + pct(r[1], 1) + '</b></div>'; });
    h += '</div><div class="fxnote">최대낙폭 실제 ' + pct(a.stocks_mdd_pct, 1) + ' · 가만히 ' + pct(hd.stocks_mdd_pct, 1) + '. 가만히 = ' + esc(md(p.from)) + ' 수량을 그대로 들고 있었다면.</div>';
    h += '<div class="ctitle" style="margin-top:13px">매매가 더하고 뺀 돈 <span class="mut xs">(체결가 → 오늘 종가 · 사후확신)</span></div><div class="fxatt">';
    [["매수", bs.buy], ["매도", bs.sell], ["현금 대기", p.cash ? -p.cash.vs_spx_krw : null]].forEach(function (kv) {
      h += '<div class="fxa"><div class="mut xs">' + esc(kv[0]) + '</div><div class="v num ' + cls(kv[1]) + '">' + (kv[1] == null ? "—" : sign(kv[1]) + num(Math.round(kv[1]))) + '</div></div>';
    });
    h += '</div>';
    var w = (t.worst || []).filter(function (x) { return x.krw < 0; }).slice(0, 3);
    if (w.length) h += '<div class="decs" style="margin-top:10px">' + w.map(function (x) {
      return '<span class="dt num">' + esc(md(x.date)) + '</span><span><b>' + esc(x.label) + ' ' + (x.side === "sell" ? "매도" : "매수") + '</b> ' + (x.side === "sell" ? "이후 " + pct(x.move_pct, 1) + " 더 올랐다" : "이후 " + pct(x.move_pct, 1)) + ' · <b class="num down">' + num(Math.round(x.krw)) + '원</b></span>';
    }).join("") + '</div>';
    return h + '<div class="fxnote">현금 대기 = 현금을 S&P500(원화)에 넣어뒀다면 대비(음수 = 현금이 기회비용). 매도 건수가 적어 판정이 아니라 관찰이다(d142 — 실현 20건에 재검증).</div></div>';
  }

  function fxCard() {
    var x = D.fx_exposure;
    if (!x || x.status !== "live") return '<div class="empty sm">측정값 없음</div>';
    var COL = { USD: "var(--info)", KRW: "var(--ink)" }, segs = "", leg = "";
    (x.buckets || []).forEach(function (b) { segs += '<span style="width:' + b.weight + '%;background:' + (COL[b.currency] || "var(--mut2)") + '"></span>'; leg += '<span class="palg"><i style="background:' + (COL[b.currency] || "var(--mut2)") + '"></i>' + esc(b.currency) + ' ' + b.weight + '%</span>'; });
    var h = '<div class="card"><div class="ctitle">통화 익스포저 <span class="mut xs">(주식+현금 · 보고서 시점)</span></div><div class="stackbar">' + segs + '</div><div class="palegend">' + leg + '</div>';
    var p = x.percentile || {}, w = p.windows || {};
    if (p.status === "live" && w["1y"]) h += '<div class="fxpct">원/달러 ' + num(x.fx_rate) + ' — ' + ["1y", "3y", "5y"].filter(function (k) { return w[k]; }).map(function (k) { return k + ' ' + w[k].percentile + '%ile'; }).join(" · ") + '<br><span class="xs mut">룰6: 판정은 5년 창(30 미만 저평가·70 초과 고평가). 1년 창 단독 인용 금지</span></div>';
    h += '<div class="fxsens">환율 1% 변동 = 총자산 <b class="' + cls(x.sensitivity_1pct_krw) + '">' + sign(x.sensitivity_1pct_krw) + num(x.sensitivity_1pct_krw) + '원</b></div>';
    var a = x.attribution || {};
    h += '<div class="ctitle" style="margin-top:13px">환손익 3분해 <span class="mut xs">(미국주)</span></div><div class="fxatt">';
    [["종목", a.price_krw], ["환율", a.fx_krw], ["교차", a.cross_krw]].forEach(function (kv) { h += '<div class="fxa"><div class="mut xs">' + kv[0] + '</div><div class="v num ' + cls(kv[1]) + '">' + sign(kv[1]) + num(kv[1]) + '</div></div>'; });
    return h + '</div><div class="fxnote">취득환율 ' + num(x.fx_cost_basis) + '원 기준 추정.</div></div>';
  }
  function corrCard() {
    var st = D.stats;
    if (!st || st.status !== "live") return '<div class="empty sm">측정값 없음</div>';
    var lost = st.effective_bets_weight_only ? (1 - st.effective_bets / st.effective_bets_weight_only) * 100 : null;
    var h = '<div class="card"><div class="ctitle">동조 · 실효 분산 <span class="mut xs">(' + st.window + '거래일)</span></div>';
    h += '<div class="enbrow"><div class="enb"><div class="mut xs">보유</div><div class="v num">' + st.holdings + '</div></div><div class="enbar">→</div>'
      + '<div class="enb"><div class="mut xs">비중 기준</div><div class="v num">' + st.effective_bets_weight_only + '</div></div><div class="enbar">→</div>'
      + '<div class="enb hot"><div class="mut xs">상관 기준</div><div class="v num">' + st.effective_bets + '</div></div></div>';
    if (lost != null) h += '<div class="fxsens">분산의 <b class="bad">' + lost.toFixed(0) + '%</b>가 동조로 사라짐 · 포트 변동성 ' + st.portfolio_vol + '% <span class="mut">(상관 무시 ' + st.weighted_vol + '%)</span></div>';
    var b = st.benchmarks || {};
    if (Object.keys(b).length) {
      h += '<div class="ctitle" style="margin-top:12px">벤치마크 베타</div>';
      Object.keys(b).forEach(function (k) { h += '<div class="rdrow"><span class="rdlabel">' + esc(k) + '</span><span class="rdval mut num" style="flex:1;text-align:right">β ' + b[k].beta + ' · ρ ' + b[k].corr + '</span></div>'; });
    }
    if ((st.top_pairs || []).length) {
      h += '<div class="ctitle" style="margin-top:12px">가장 같이 움직이는 쌍</div>';
      st.top_pairs.slice(0, 5).forEach(function (p) {
        var w = Math.max(0, Math.min(100, p.corr * 100));
        h += '<div class="rdrow"><span class="rdlabel">' + esc(p.a) + '·' + esc(p.b) + '</span><div class="secbar"><div class="secseg" style="width:' + w.toFixed(0) + '%;background:' + (p.corr >= 0.7 ? "var(--bad)" : p.corr >= 0.5 ? "var(--warn)" : "var(--good)") + '"></div></div><span class="rdval mut num">' + p.corr.toFixed(2) + '</span></div>';
      });
    }
    return h + '<div class="fxnote">' + esc(st.caveat) + '</div></div>';
  }

  // ════════════════ 화면: 종목 상세 (캔버스 Hyundai) ════════════════
  var detailRange = "d";
  // '이 주문은 들어가나' — 세로 가격 사다리(목표 · 내 주문 · 상한 · 필요 종가 · 기준 종가 · 하한)
  function orderLadder(o, st, cen) {
    var e = bandEval(o); if (!e) return "";
    var base = e.bb.base, k = orderKind(o), verb = /익절/.test(o.action || "") ? "익절" : e.sell ? "트림" : "매수", dl = relDay(e.bb.day);
    var rows = [];
    if (cen && cen > e.P) rows.push({ v: cen, n: "목표 중심(12M)", c: "acc", ic: '<span class="bar acc"></span>' });
    rows.push({ v: e.P, n: "내 " + verb + " 주문 — " + (e.ok ? "밴드 안" : "밴드 밖"), c: e.ok ? "hotok" : "hot", ic: '<span class="odot' + (e.ok ? " in" : "") + '"></span>' });
    rows.push({ v: e.band.up, n: mdw(e.bb.day) + " 상한가", c: "b", ic: '<span class="bar"></span>' });
    if (e.need) rows.push({ v: e.need, n: "등록 가능한 종가", c: "", ic: '<span class="dot"></span>' });
    rows.push({ v: base, n: e.bb.basis, c: "now", ic: '<span class="now"></span>', now: 1 });
    rows.push({ v: e.band.lo, n: mdw(e.bb.day) + " 하한가", c: "", ic: '<span class="bar"></span>' });
    rows.sort(function (a, b) { return b.v - a.v || (a.now ? 1 : -1); });
    var h = '<div class="wcard"><h2>' + esc(dl === "오늘" || dl === "내일" ? dl : mdw(e.bb.day)) + ' 이 주문은 들어가나</h2><div class="hsub">' + esc(mdw(e.bb.day)) + ' 정규장 · 가격제한폭 = ' + esc(e.bb.basis) + ' ±30%</div><div class="vlad">';
    rows.forEach(function (r) { h += '<div class="vl ' + r.c + '"><div class="ic">' + r.ic + '</div><div class="n">' + esc(r.n) + '</div><div class="v num">' + num(r.v) + (r.now ? '' : ' · ' + pct((r.v / base - 1) * 100, 1)) + '</div></div>'; });
    h += '</div>';
    if (k !== "wait") {
      var rl = regLine(o.ticker);
      h += '<p>' + (rl ? '등록선 ' + won(rl.level) + ' — ' + (rl.lfired ? '<b>점등.</b> 다음 거래일분을 걸 차례다.' : '아직 미도달(' + pct(rl.ldist, 1) + '). 지금은 걸 주문이 아니다.') : '상태: ' + esc(ORDER_LBL[k]) + ' — 오늘 밤 할 일에는 올리지 않는다.') + '</p>';
    } else if (e.ok) h += '<p>접수 가능 — ' + esc(dl) + ' 상한가 ' + won(e.band.up) + ' 안.</p>';
    else if (e.need) {
      var s2 = sessionAfter(e.bb.day);
      h += '<p>' + (e.bb.basis === "오늘 종가" ? '오늘 종가가 <b class="num">' + won(e.need - base) + '</b>만 높았어도 걸렸다. ' : '')
        + esc(dl) + ' 종가가 <b class="num">' + won(e.need) + '</b>(' + pct((e.need / base - 1) * 100, 1) + ') 이상이면 ' + mdw(s2) + '분을 걸 수 있다.</p>';
    }
    return h + '</div>';
  }
  // 다음 기회 — 밴드 밖 주문의 거래일 타임라인(거래일 달력 + D.events)
  function nextChances(o, st) {
    var e = bandEval(o); if (!e || e.ok || !e.need || orderKind(o) !== "wait") return "";
    var d1 = e.bb.day, s2 = sessionAfter(d1), s3 = sessionAfter(s2), rows = [];
    rows.push({ on: 1, t: mdw(d1) + " 15:30 · 종가 확인", s: won(e.need) + " 이상이면 " + mdw(s2) + "분 " + num(e.P) + "원 예약" });
    if (dayDiff(s2, s3) > 3) {
      rows.push({ t: mdw(s2) + " · 연휴 전 마지막 등록일", s: "못 걸면 연휴 전 오더 0회" });
      var hol = eventsLive().filter(function (x) { return x.kind === "휴장" && x.date > s2 && x.date < s3; })[0];
      rows.push({ t: (hol ? md(hol.date) + "–" + md(hol.end || hol.date) + " 휴장 · " : "휴장 · ") + mdw(s3) + " 재개", s: "재개 전날 밤 재등록" });
    }
    eventsLive().filter(function (x) { return x.type === "earnings" && x.ticker === o.ticker; }).forEach(function (x) { rows.push({ t: mdw(x.date) + " · 실적", s: "기한부 판단 시점 · " + (x.confidence || "") }); });
    return '<div class="wcard"><h2>다음 기회</h2><div class="tl">' + rows.map(function (r) { return '<div class="tli' + (r.on ? " on" : "") + '"><b>' + esc(r.t) + '</b><span>' + esc(r.s) + '</span></div>'; }).join("") + '</div></div>';
  }
  function rule2Card(st) {
    var r = st.rule2, m = st.margins || [];
    if (!r && !m.length) return "";
    var sc = r ? String(r.score || "") : "", n = parseInt(sc, 10) || 0, fin = /금융/.test(sc), den = fin ? "1" : "3";
    var ck = fin ? (n ? "bad" : "good") : n >= 3 ? "bad" : n === 2 ? "acc" : "good";
    var ct = (fin ? (n ? "마진 훼손 " : "정상 ") : n >= 3 ? "훼손 착수 " : n === 2 ? "감시 상향 " : "정상 ") + n + "/" + den;
    var h = '<div class="wcard"><div class="hrow" style="display:flex;justify-content:space-between;align-items:center;gap:8px"><h2 style="margin:0;font-size:16px">룰2 · 펀더멘털 훼손</h2>' + (r ? '<span class="chip ' + ck + '">' + ct + '</span>' : '') + '</div><div class="mbars">';
    if (m.length) {
      var mx = Math.max.apply(null, m.map(function (x) { return Math.abs(x.m); })) || 1;
      h += '<div class="cols">' + m.map(function (x, i) {
        var last = i === m.length - 1, rise = last && i > 0 && x.m > m[i - 1].m;
        return '<div class="col' + (last ? " last" + (rise ? " ok" : "") : "") + '"><b class="num">' + x.m.toFixed(1) + '%</b><span style="height:' + Math.max(6, Math.abs(x.m) / mx * 72).toFixed(0) + 'px' + (x.m < 0 ? ';opacity:.6' : '') + '"></span><small>' + esc(x.y) + '</small></div>';
      }).join("") + '</div>';
    } else h += '<div class="xs mut">영업마진 시계열 없음</div>';
    h += '<ul>';
    ((r && r.detail) || []).forEach(function (d) {
      if (fin && !/마진/.test(d)) return;
      var met = /^✅/.test(d), tx = d.replace(/^[✅❌]\s*/u, "").replace(/\*\*/g, "");
      h += '<li class="' + (met ? "y" : "n") + '">' + (met ? IC.alert : IC.dash) + '<span>' + esc(tx) + '</span></li>';
    });
    if (fin) h += '<li class="u">' + IC.dash + '<span>FCF · 순부채 — 금융 자회사 연결이라 판정 제외</span></li>';
    h += '</ul></div>';
    if (r && r.verdict) h += '<p>' + esc(String(r.verdict).replace(/^[✅⚠🚨️\s]+/u, "")) + '</p>';
    return h + '</div>';
  }
  function stockDecisions(st) {
    var dc = D.decisions || {}, all = (dc.closed || []).concat(dc.open || []), code = st.ticker.replace(/\.K[SQ]$/, "");
    var hit = all.filter(function (d) {
      var tags = d.tags || [];
      return String(d.topic || "").indexOf(st.label) >= 0 || tags.indexOf(st.label) >= 0 || tags.indexOf(st.ticker) >= 0 || tags.indexOf(code) >= 0;
    }).sort(function (a, b) { return String(b.date || "").localeCompare(String(a.date || "")); }).slice(0, 5);
    if (!hit.length) return "";
    return '<div class="wcard"><h2>이 종목에 대해 내린 결정</h2><div class="decs">' + hit.map(function (d) {
      return '<span class="dt num">' + esc(md(d.date)) + '</span><span><b class="acc">' + esc(d.id) + '</b> ' + esc(shortTxt(d.topic, 70)) + (d.status === "open" ? ' <span class="chip">추적 중</span>' : '') + '</span>';
    }).join("") + '</div><a class="lnk" href="#decisions" style="font-size:13px;font-weight:600;color:var(--accent)">결정 기록 전체</a></div>';
  }
  function renderDetail(tk) {
    var st0 = find(tk);
    if (!st0) { paint(topbar({ back: "#pf", backLabel: "포트폴리오" }) + '<div class="empty">종목을 찾을 수 없어요.</div>'); return; }
    var isHold = st0.region != null, hs = isHold ? holdingsLive() : null;
    var st = isHold ? hs.filter(function (x) { return x.ticker === tk; })[0] : st0;
    var q = Q(tk), p = isHold ? st.lp : px(st), c = isHold ? st.lc : chg(st), cur = st.currency || (isKR(tk) ? "KRW" : "USD");
    var cen = centerOf(st.target, tk, p);
    var h = topbar({ back: "#pf", backLabel: "포트폴리오", code: tk + (isHold ? " · " + fmtShares(st.shares) + "주" : " · 워치") });

    // 헤더 — 이름 · 등급 칩 · 가격 · 3칸
    var low = (st.stars || 0) <= 2;
    h += '<div class="dh"><div class="t"><h1>' + esc(st.label) + '</h1><span class="chip ' + (low ? "bad" : "acc") + '">★' + (st.stars || 0) + (low ? " · 결정 필요" : st.score != null ? " · " + st.score : "") + '</span></div>';
    var dAbs = q && q.pc != null && p != null ? p - q.pc : null;
    h += '<div class="p"><span class="v num">' + fmtP(p, tk) + '</span><span class="c num ' + cls(c) + '">' + pct(c) + (dAbs != null ? ' · ' + (dAbs < 0 ? "-" : "+") + (isKR(tk) ? num(Math.round(Math.abs(dAbs))) : "$" + num2(Math.abs(dAbs))) : '') + '</span>' + sessTag(q, true) + '</div>';
    if (q) {
      var reg = [];
      if (q.x && q.rc != null) reg.push("정규장 종가 " + fmtP(q.rc, tk) + (q.rcc != null ? " (" + pct(q.rcc) + ")" : ""));
      else if (isKR(tk) && q.rc != null && q.p != null && Math.abs(q.p - q.rc) > 1e-9) reg.push("정규장 종가 " + fmtP(q.rc, tk) + " (" + pct(q.pc ? (q.rc / q.pc - 1) * 100 : null) + ")");
      if (q.xp != null) reg.push("시간외 " + fmtP(q.xp, tk) + " (" + pct(q.xc) + ")");
      reg.push((q.t ? mdLabel(q.t) + " " + hhmm(q.t) : "") + " 체결 기준");
      h += '<div class="reg">' + esc(reg.join(" · ")) + '</div>';
    } else h += '<div class="reg">보고서 시세 · ' + esc(D.generated_at || "") + '</div>';
    if (isHold) {
      h += '<div class="g3"><div><span class="k">평단</span><span class="v num">' + price(st.cost, cur) + '</span></div>'
        + '<div><span class="k">평가손익</span><span class="v num ' + cls(st.lpnl) + '">' + sign(st.lpnl) + num(Math.round(st.lpnl)) + '</span><span class="s num ' + cls(st.lpnlpct) + '">' + pct(st.lpnlpct, 1) + '</span></div>'
        + '<div><span class="k">스코어 · 비중</span><span class="v num">' + (st.score != null ? st.score : "—") + ' · ' + st.w.toFixed(1) + '%</span></div></div>';
    } else {
      h += '<div class="g3"><div><span class="k">스코어</span><span class="v num">' + (st.score != null ? st.score : "—") + '</span></div>'
        + '<div><span class="k">목표 중심</span><span class="v num">' + (cen ? fmtP(cen, tk) : "—") + '</span></div>'
        + '<div><span class="k">목표까지</span><span class="v num ' + (cen && p ? cls(cen / p - 1) : "") + '">' + (cen && p ? pct((cen / p - 1) * 100, 1) : "—") + '</span></div></div>';
    }
    h += '</div>';

    // 국내 지정가 — 세로 사다리 + 다음 기회
    if (isKR(tk)) activeKrOrders(true).filter(function (o) { return o.ticker === tk; }).forEach(function (o) { h += orderLadder(o, st, cen) + nextChances(o, st); });

    // 차트 (오늘 / 1개월)
    var ser = S(tk), hasD = !!(ser && q), rng = hasD ? detailRange : "m";
    h += '<div class="card" style="margin-top:14px"><div class="chart-h"><span class="ctitle" style="margin:0">' + (rng === "d" ? (q && q.x ? "마지막 정규장" : "오늘") : "1개월") + '</span>'
      + '<div class="rtoggle" role="group" aria-label="기간">' + (hasD ? '<button type="button" data-r="d" class="' + (rng === "d" ? "on" : "") + '">오늘</button>' : '') + '<button type="button" data-r="m" class="' + (rng === "m" ? "on" : "") + '">1개월</button></div></div>';
    if (rng === "d") {
      var lines = [];
      if (isHold && st.cost) lines.push({ v: st.cost, label: "평단 " + fmtP(st.cost, tk), color: "var(--mut)" });
      h += areaChart(ser, q.x ? q.rpc : q.pc, { slots: 78, lines: lines, fmt: function (v) { return fmtP(v, tk); }, label: st.label + " 장중" });
    } else {
      var spk = st.spark || [];
      h += spk.length > 1 ? areaChart(spk, null, { h: 120, lines: isHold && st.cost ? [{ v: st.cost, label: "평단", color: "var(--mut)" }] : [], label: st.label + " 1개월" }) : '<div class="empty sm">1개월 시계열 없음</div>';
    }
    h += '</div>';

    if (isHold) h += rule2Card(st);
    h += stockDecisions(st);
    var pick = ((D.pm_view || {}).picks || []).filter(function (x) { return x.ticker === tk; })[0];
    if (pick) h += '<div class="pmdark"><span class="lb">PM 한 줄</span><p>' + esc(pick.view) + '</p><small>' + esc((D.pm_view || {}).updated || "") + ' 사견 · 룰과 별개</small></div>';

    // 가격 레벨 — 현재가 대비 모든 레벨
    var lv = [];
    function add(v, label, sub, kind) { if (v == null || isNaN(v)) return; for (var i = 0; i < lv.length; i++) if (Math.abs(lv[i].v / v - 1) < 0.0008 && lv[i].kind !== "now") return; lv.push({ v: v, label: label, sub: sub, kind: kind }); }
    if (p != null) add(p, "현재가", q ? (SESS[q.s] || "") : "보고서 시세", "now");
    if (isHold && st.cost) add(st.cost, "평단", null, "");
    var tgt = parsePrices(st.target, tk, p);
    if (cen) add(cen, "목표 중심", "12개월", "acc");
    if (tgt.length >= 2) { add(Math.min(tgt[0].v, tgt[1].v), "목표 하단", null, "acc"); add(Math.max(tgt[0].v, tgt[1].v), "목표 상단", null, "acc"); }
    var tr = parsePrices(st.trim, tk, p);
    if (tr.length && st.trim && st.trim !== "—") add(tr[0].v, "트림 · 매도", null, "bad");
    alertsLive().filter(function (a) { return a.ticker === tk; }).forEach(function (a) {
      if (a.cond === "between") { add(a.low, cleanId(a.id), "구간 하단", "good"); add(a.high, cleanId(a.id), "구간 상단", "good"); }
      else add(a.level, cleanId(a.id), a.lfired ? "발동" : "알림", a.lfired ? "bad" : "good");
    });
    if (lv.length > 1) {
      lv.sort(function (a, b) { return b.v - a.v; });
      h += h2s("가격 레벨", "현재가 대비", "sm") + '<div class="card"><div class="rail">';
      lv.forEach(function (x) {
        var g = p ? (x.v / p - 1) * 100 : null;
        h += '<div class="rung ' + (x.kind === "now" ? "now" : x.kind) + '"><div class="l"><b>' + esc(x.label) + '</b>' + (x.sub ? '<span class="s">' + esc(x.sub) + '</span>' : '') + '</div>'
          + '<div class="p num">' + fmtP(x.v, tk) + '</div><div class="g num ' + (x.kind === "now" ? "mut" : cls(g)) + '">' + (x.kind === "now" ? "지금" : pct(g, 1)) + '</div></div>';
      });
      h += '</div></div>';
    }

    // 텍스트 정본
    h += '<div class="kv">';
    h += '<div class="b full"><div class="k">목표가</div><div class="v">' + esc(st.target || "—") + '</div></div>';
    if (isHold) h += '<div class="b full"><div class="k">매수존</div><div class="v">' + mdInline(esc(st.buy_zone || "—")) + '</div></div><div class="b full"><div class="k">트림 · 매도</div><div class="v">' + mdInline(esc(st.trim || "—")) + '</div></div>';
    else if (st.buy_zone) h += '<div class="b full"><div class="k">매수존</div><div class="v">' + mdInline(esc(st.buy_zone)) + '</div></div>';
    h += '</div>';
    if (st.comment) h += '<div class="comment">' + mdInline(esc(st.comment)) + '</div>';

    if (st.forecast) {
      h += h2s("가격 예상 레인지", "목표가·매수존과 별개", "sm");
      h += forecastRow("이번주", st.forecast.week, p, cur) + forecastRow("이번달", st.forecast.month, p, cur);
    }

    var gcons = ((D.guru_flows || {}).consensus || {})[tk];
    if (gcons && gcons.holders && gcons.holders.length) {
      var gShort = { berkshire: "버핏", scion: "버리", duquesne: "드러켄밀러", pershing: "애크먼", appaloosa: "테퍼", thirdpoint: "로엡" };
      var aLbl = { NEW: "신규", ADD: "증량", TRIM: "축소", EXIT: "청산", HOLD: "유지" }, aCls = { NEW: "buy", ADD: "buy", TRIM: "sell", EXIT: "sell", HOLD: "hold" };
      h += h2s("대가 흐름 (13F)", '<a class="aux" href="#gurus">전체</a>', "sm") + '<div class="card"><div class="row between"><span class="bold">대가 컨센</span><span class="badge ' + (gcons.net > 0 ? "buy" : gcons.net < 0 ? "sell" : "hold") + '">매수 ' + gcons.buy + ' · 매도 ' + gcons.sell + (gcons.hold ? ' · 유지 ' + gcons.hold : '') + '</span></div><div class="row wrap" style="margin-top:8px">';
      gcons.holders.forEach(function (hd) { h += '<span class="gchip ' + (aCls[hd.action] || "hold") + '">' + esc(gShort[hd.slug] || hd.guru) + ' ' + (aLbl[hd.action] || hd.action) + '</span>'; });
      h += '</div>' + (gcons.buy > 0 && gcons.sell > 0 ? '<div class="xs mut" style="margin-top:6px">대가 분열 — 단일 컨센 없음(과신 견제)</div>' : '') + '</div>';
    }

    var issues = st.issues || [];
    h += h2s("최근 이슈 · 체크포인트", issues.length ? issues.length + "건" : null, "sm");
    if (!issues.length) h += '<div class="empty sm">등록된 이슈가 없어요.</div>';
    issues.forEach(function (is) { h += '<div class="issue"><div class="top"><span class="itag ' + esc(is.tag || "") + '">' + esc(is.tag || "") + '</span><span class="dt">' + esc(is.date || "") + '</span></div><div class="tx">' + mdInline(esc(is.text)) + '</div></div>'; });
    h += foot();
    paint(h);
    Array.prototype.forEach.call(root.querySelectorAll(".rtoggle button"), function (b) {
      b.addEventListener("click", function () { detailRange = b.getAttribute("data-r"); rerender(); });
    });
  }
  function forecastRow(label, f, cpx, cur) {
    if (!f) return "";
    var lo = f.low, hi = f.high, rng = (hi - lo) || 1, posv = cpx == null ? null : Math.max(0, Math.min(100, (cpx - lo) / rng * 100));
    return '<div class="fc"><div class="row between"><span class="fc-lb">' + esc(label) + '</span>' + dirPill(f.dir) + '</div>'
      + '<div class="fc-rng num">' + price(lo, cur) + ' <span class="mut">~</span> ' + price(hi, cur) + '</div><div class="fc-bar">' + (posv != null ? '<div class="fc-now" style="left:' + posv.toFixed(0) + '%"></div>' : '') + '</div>'
      + (cpx != null ? '<div class="fc-cap">현재 ' + price(cpx, cur) + '</div>' : '') + (f.note ? '<div class="fc-note">' + esc(f.note) + '</div>' : '') + '</div>';
  }

  // ★[9/21 d205] 미국 트랙 카드 — 코스피 낙폭과 무관한 달러 3회 균등 분할
  function usTrackCard() {
    var U = usTrack(), u = U.u;
    if (!U.ok) return "";
    var sched = (u.schedule || []).map(function (d, i) {
      var n = i + 1, st = (u.done || []).indexOf(n) >= 0 ? "집행" : (u.pending || []).indexOf(n) >= 0 ? "도래" : "대기";
      return '<span class="chip ' + (st === "집행" ? "good" : st === "도래" ? "acc" : "") + '">' + n + '회 ' + esc(md(d)) + ' · ' + st + '</span>';
    }).join(" ");
    var sp = (u.split || []).map(function (x) { return '<div class="ussplit"><b class="num">' + esc(x.ticker) + ' ' + usd(x.usd) + '</b><span>' + esc(x.why) + '</span></div>'; }).join("");
    return '<div class="money" style="margin-top:12px"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="k0">🇺🇸 미국 트랙 · 이번 회차(달러)</span><span class="chip">3회 분할 · d205</span></div>'
      + '<div class="big num">' + usd(U.allowed) + '</div>'
      + '<div class="g2"><div><span class="k">달러 잔고</span><span class="v num">' + usd(u.usd_cash) + '</span></div><div><span class="k">회차당</span><span class="v num">' + usd(u.per_tranche_usd) + '</span></div></div>'
      + (sched ? '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">' + sched + '</div>' : '')
      + (sp ? '<div style="margin-top:10px;display:flex;flex-direction:column;gap:4px">' + sp + '</div>' : '')
      + '<p>' + esc(u.why || "") + ' 코스피 낙폭과 무관 · S&amp;P 폭풍 70 이상이면 그 회차 연기 · 급등일(+3%)엔 다음 날(룰3).</p></div>';
  }

  // ════════════════ 화면: 룰 · 리스크 (캔버스 Rules) ════════════════
  function renderRules() {
    var L = ladderLive(), s = L.s, hs = holdingsLive(), T = totalsLive(hs), G = gatesLive();
    var h = topbar({ title: "룰 · 리스크", sub: '<span class="chip bad" style="font-size:11px">급락 TF 가동 · 7/13~</span>' });
    h += '<p class="tagline">룰은 계산기다 — 집행은 PM 판단, 결정은 정훈.</p>';

    // 오늘 살 수 있는 돈
    var base = s.base_krw || 0, mult = s.mult || 1;
    var nextCap = L.next ? Math.round(base * (L.unl + L.next.alloc_pct) / 100 * mult) : null, nextLeft = nextCap != null ? Math.max(0, nextCap - L.spent) : null;
    var why = s.halted ? "하드플로어 발동 — 사다리 전면 정지. "
      : L.allowed > 0 ? "상한 안에서 " + won(L.allowed) + " 남았다 — 국내 1주 가격에 닿을 때까지 적립. 룰6 국내 비중이 상단(22%) 위라 둘의 우선순위는 d207 판단 대기. "
      : L.unl > 0 && L.spent > L.cap ? "상한의 " + (L.spent / L.cap).toFixed(1) + "배를 이미 썼다. "
      : L.unl > 0 ? "해금분을 모두 집행했다. " : "해금된 단계가 없다. ";
    if (L.next && !s.halted) why += "새 몫은 코스피가 " + L.next.label + "(" + num(Math.round(L.nextLevel)) + ") 아래로 마감해야 열린다" + (nextLeft != null ? " — 그때 약 " + won(Math.round(nextLeft / 100) * 100) + "." : ".");
    h += '<div class="money"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="k0">🇰🇷 국내 트랙 · 사다리로 살 수 있는 돈(원화)</span><span class="chip">' + (L.live ? "장중 추정" : "종가 기준") + ' · 누적</span></div>'
      + '<div class="big num">' + num(L.allowed) + '<small>원</small></div>'
      + '<div class="g2"><div><span class="k">상한 ' + (L.unl || 0) + '%</span><span class="v num">' + won(L.cap) + '</span></div><div><span class="k">기집행</span><span class="v num">' + won(L.spent) + '</span></div></div>'
      + '<p>' + esc(why) + '</p></div>';
    h += usTrackCard();

    // 룰1 낙폭 사다리
    if (s.peak && L.steps.length) {
      var rows = [];
      L.steps.forEach(function (st) {
        var lvl = s.peak * (1 + st.thr / 100), on = L.dd != null && L.dd <= st.thr;
        rows.push({ v: lvl, h: '<div class="lstep ' + (on ? "on" : "off") + '" title="' + esc(st.why || "") + '"><span class="dt"></span><div class="tx"><span class="n">' + esc(st.label) + ' ' + Math.round(st.thr) + '%</span><span class="s num">' + num(Math.round(lvl)) + ' · 배분 ' + st.alloc_pct + '%</span></div>'
          + '<span class="r">' + (on ? "해금" : "잠김") + (st.executed_krw ? " · 집행 " + num(st.executed_krw) : "") + '</span></div>' });
      });
      rows.push({ v: L.k, now: 1, h: '<div class="lstep now"><span class="dt"></span><div class="tx"><span class="n num">지금 ' + pct(L.dd, 1) + ' · ' + num2(L.k) + '</span><span class="s">' + (L.live ? "장중 · " + (L.q && L.q.t ? hhmm(L.q.t) : "") : L.fresh ? "오늘 종가" : "보고서 종가") + '</span></div>'
        + '<span class="r num">' + (L.next ? L.next.label + "까지 " + Math.abs(L.dd - L.next.thr).toFixed(1) + "%p" : "") + '</span></div>' });
      rows.sort(function (a, b) { return b.v - a.v || (a.now ? 1 : -1); });
      h += h2s("룰1 · 낙폭 사다리", "고점 " + num(Math.round(s.peak)) + (s.peak_date ? " (" + md(s.peak_date) + ")" : ""));
      h += '<div class="group">' + rows.map(function (r) { return r.h; }).join("")
        + '<div class="lstep off"><span class="dt"></span><div class="tx"><span class="n">예비</span><span class="s">배분 ' + (s.reserve_pct || 7) + '% · 회복 확인 전</span></div><span class="r">봉인</span></div></div>';
      h += '<div class="xs mut" style="margin:8px 4px 0">되돌리면 다시 잠긴다(RESET) · 누적 상한이지 목표가 아니다 · 판정 정본 tranche_rules.py</div>';
    }

    // TF 해제 게이트
    var fp = flowPair(), s2 = alertBy(/TF S2/);
    h += h2s("TF 해제 게이트", '<b class="num" style="font-size:17px;color:var(--ink)">' + G.n + '</b> / 3');
    h += '<div class="group gates">';
    h += '<div class="gate' + (G.on1 ? " on" : "") + '"><span class="no">①</span><div><div class="t">코스피 7,500 종가 회복</div><div class="s num">' + (G.g1 ? '현재 ' + num2(G.g1.lp) + (G.g1.lq ? (G.g1.lq.s === "reg" ? ' (장중)' : ' (종가)') : '') : '—') + '</div></div><div class="num bold ' + (G.on1 ? "good" : "") + '">' + (G.g1 && G.g1.ldist != null ? (G.on1 ? "충족" : pct(-G.g1.ldist / (1 + G.g1.ldist / 100), 1)) : "—") + '</div></div>';
    h += '<div class="gate' + (G.on2 ? " on" : "") + '"><span class="no">②</span><div><div class="t">외인 2거래일 연속 순매수</div><div class="s num">' + (fp ? md(fp[0].date) + ' ' + eok(fp[0].foreign) + ' → ' + md(fp[1].date) + ' ' + eok(fp[1].foreign) : esc((G.ft.streak || 0) + "일째 " + (G.ft.direction || ""))) + (G.ftStale ? ' <b class="warn">· ' + esc(md(G.last)) + ' 수급 미반영</b>' : '') + '</div></div><div class="num bold ' + (G.on2 ? "good" : "") + '">' + (G.on2 ? "충족" : G.buyStreak + "일") + '</div></div>';
    h += '<div class="gate' + (G.on3 ? " on" : "") + '"><span class="no">③</span><div><div class="t">WTI $71.5 이하</div><div class="s num">' + (G.g3 ? '현재 $' + num2(G.g3.lp) : '—') + '</div></div><div class="num bold ' + (G.on3 ? "good" : "") + '">' + (G.g3 && G.g3.lp != null ? (G.on3 ? "충족" : pct((G.g3.lp / G.g3.level - 1) * 100, 1)) : "—") + '</div></div>';
    h += '</div><div class="xs mut" style="margin:8px 4px 0">해제 = 셋 동시 충족 + 2거래일 유지. 부분 충족은 액션이 아니다(§5).' + (s2 ? ' 악화선 S2 = 코스피 ' + num(s2.level) + ' (' + pct(s2.ldist, 1) + ')' : '') + '</div>';

    // 하드플로어
    var sp = stormPct();
    h += '<div class="wcard" style="margin-top:22px"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><h2 style="margin:0;font-size:16px">하드플로어 · 글로벌 확산</h2><span class="chip ' + (s.halted ? "bad" : "good") + '">' + (s.halted ? "발동 · 사다리 정지" : "미발동") + '</span></div>';
    if (sp != null) h += '<div><div class="bband-l" style="margin-bottom:6px"><span>S&amp;P500 폭풍 <b class="num" style="color:var(--ink)">' + sp + '%ile</b></span><span>발동선 70</span></div><div class="gauge" style="margin:0"><div class="fill" style="width:' + sp + '%;background:' + (sp >= 70 ? "var(--bad)" : "var(--good)") + '"></div><div class="thr" style="left:70%"><span></span></div></div></div>';
    h += '<p>사다리의 전제는 \'국내 구조 사건\'이다. 미국이 같이 흔들리면(≥70) 사다리 전면 정지. 정본 vol_gauge.py(RV20).</p></div>';

    // 포트 리스크 · 룰6 · 수급 · 알림
    h += riskBlock();
    var r6 = alertBy(/룰6/);
    h += h2s("룰6 · 국내 비중", null, "sm");
    h += '<div class="wcard" style="margin-top:0"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><b>국내 주식 ' + (T.krW != null ? T.krW.toFixed(1) : "—") + '% · 목표 18–22%</b><span class="chip ' + (T.krW > 22 ? "bad" : "good") + '">' + (T.krW > 22 ? "상단 초과" : "밴드 안") + '</span></div>'
      + '<p>신규 입금은 100% 미국 배분 · 국내 트림은 코스피 ' + (r6 ? num(r6.level) : "7,747") + '(고점 -15%) 회복 시에만 — 지금 ' + (r6 && r6.ldist != null ? pct(r6.ldist, 1) : "—") + ' 남음 · 저점 매도 금지</p></div>';
    var ft = G.ft;
    h += h2s("코스피 투자자별 순매수", null, "sm") + '<div class="card">' + flowChart(D.flows) + (ft && !ft.error && ft.as_of ? '<div class="xs mut" style="margin-top:6px">외인 추세(' + esc(ft.as_of) + '): ' + esc((ft.streak || 0) + "일 연속 " + (ft.direction || "")) + ' · 전환단계 ' + esc(ft.stage || "") + '</div>' : '') + '</div>';
    var all = alertsLive().sort(function (a, b) { return (b.lfired ? 1 : 0) - (a.lfired ? 1 : 0) || Math.abs(a.ldist || 0) - Math.abs(b.ldist || 0); });
    h += h2s("가격 알림 전체", all.length + "건", "sm") + '<details class="fold"><summary>발동 ' + all.filter(function (a) { return a.lfired; }).length + '건 · 대기 ' + all.filter(function (a) { return a.lfired === false; }).length + '건 — 지금 가격 대입</summary><div class="in">' + alertRows(all) + '</div></details>';
    h += '<a class="hub" href="#decisions"><span class="ic">' + IC.compass + '</span><div><div class="t">결정 · 전략 아젠다</div><div class="s">열린 질문 ' + ((D.decisions || {}).open_count || 0) + '건 · 왜 그렇게 결정했나</div></div><span class="chev">' + IC.chev + '</span></a>';
    h += foot("룰을 바꾸지 않는다 — 이 화면은 정본 룰에 지금 가격을 대입해 보여줄 뿐이다");
    paint(h);
  }
  function riskBlock() {
    var r = D.risk;
    if (!r || r.status !== "live") return "";
    var col = r.score >= 60 ? "var(--bad)" : r.score >= 35 ? "var(--warn)" : "var(--good)";
    var h = sec("포트폴리오 리스크") + '<div class="card"><div class="rkhead"><div><span class="rknum num" style="color:' + col + '">' + r.score + '</span><span class="rkmax">/100</span></div><span class="rklv" style="background:' + col + ';color:var(--bg)">' + esc(r.level) + '</span></div>';
    h += '<div class="rkbar"><div class="rkfill" style="width:' + r.score + '%;background:' + col + '"></div></div>';
    (r.axes || []).slice().sort(function (a, b) { return (b.contribution || -1) - (a.contribution || -1); }).forEach(function (a) {
      if (a.value == null) { h += '<div class="rdrow"><span class="rdlabel">' + esc(a.label) + '</span><div class="secbar"></div><span class="rdval mut">미측정</span></div>'; return; }
      var seg = a.value >= 66 ? "var(--bad)" : a.value >= 33 ? "var(--warn)" : "var(--good)";
      h += '<div class="rdrow"><span class="rdlabel">' + esc(a.label) + '</span><div class="secbar"><div class="secseg" style="width:' + a.value + '%;background:' + seg + '"></div></div><span class="rdval mut num">' + a.value + '</span></div>';
    });
    var f = r.facts || {};
    h += '<div class="rkfacts">최대 ' + esc(f.top || "—") + ' ' + f.top_weight + '% · ' + esc(f.top_sector || "—") + ' ' + f.top_sector_weight + '% · 달러 ' + f.usd_weight + '% · ⭐2이하 ' + f.low_star_weight + '% · 현금 ' + f.cash_weight + '%'
      + (f.effective_bets ? '<br><b>실효 분산 ' + f.effective_bets + '종목</b> (비중만 보면 ' + f.effective_bets_weight_only + ') · 포트 변동성 ' + f.portfolio_vol + '%' : '') + '</div></div>';
    (r.insights || []).forEach(function (i) {
      h += '<div class="alert ins ' + esc(i.level) + '"><div class="row between"><span class="aid">' + esc(i.title) + '</span><span class="badge ' + esc(i.level) + '">' + ({ danger: "위험", warning: "주의", info: "안내", positive: "긍정" }[i.level] || "") + '</span></div><div class="act">' + mdInline(esc(i.detail)) + '</div></div>';
    });
    return h;
  }

  // ════════════════ 화면: 계획 ════════════════
  function renderPlan() {
    var h = topbar({ title: "계획", sub: "갱신 " + esc(D.tasks_updated || "") + " · 체크는 이 폰 임시 · 영구 반영은 채팅으로 “했어”" });
    if (D.today_note) h += '<div class="hl">' + esc(D.today_note) + '</div>';
    var ko = activeKrOrders();
    if (ko.length) { h += sec("국내 지정가 · 접수 가능성", ko.length); ko.forEach(function (o) { h += bandCard(o); }); }
    var tasks = D.tasks || {};
    [["오늘", tasks.today], ["이번주", tasks.week], ["이번달", tasks.month]].forEach(function (g) {
      var arr = g[1] || [], d = arr.filter(taskDone).length;
      h += sec(g[0] + " 할 일", d + "/" + arr.length);
      h += arr.length ? '<div class="checklist">' + arr.slice().sort(function (a, b) { return (taskDone(a) ? 1 : 0) - (taskDone(b) ? 1 : 0); }).map(checkRow).join("") + '</div>' : '<div class="empty sm">등록된 할 일이 없어요.</div>';
    });
    h += sec("장 전망");
    h += '<div class="card" style="padding:2px 15px">' + (D.outlook || []).map(function (o) { return '<div class="olrow"><div class="h"><b>' + esc(o.tag || o.horizon || "") + '</b>' + dirPill(o.dir) + '</div><div class="tx">' + esc(o.text) + '</div></div>'; }).join("") + '</div>';
    if ((D.index_forecast || []).length) {
      h += sec("지수 예상 레인지");
      (D.index_forecast || []).forEach(function (f) {
        var tkm = { "코스피": "^KS11", "코스닥": "^KQ11", "S&P500": "^GSPC", "나스닥": "^IXIC" }[f.name], q = tkm ? Q(tkm) : null;
        var rng = (f.high - f.low) || 1, pos = function (v) { return Math.max(0, Math.min(100, (v - f.low) / rng * 100)).toFixed(0); };
        h += '<div class="fc"><div class="row between"><span class="fc-lb">' + esc(f.name) + '</span>' + dirPill(f.dir) + '</div><div class="fc-rng num">' + num(f.low) + ' <span class="mut">~ 기준 ' + num(f.base) + ' ~</span> ' + num(f.high) + '</div><div class="fc-bar">'
          + (f.ref != null ? '<div class="fc-now ref" style="left:' + pos(f.ref) + '%"></div>' : '') + (q && q.p != null ? '<div class="fc-now" style="left:' + pos(q.p) + '%"></div>' : '') + '</div>'
          + '<div class="fc-cap num">기준 ' + num2(f.ref) + (q && q.p != null ? ' · 지금 <b class="' + cls(q.c) + '">' + num2(q.p) + '</b>' : '') + '</div>' + (f.note ? '<div class="fc-note">' + esc(f.note) + '</div>' : '') + '</div>';
      });
    }
    var act = activeOrders(), closed = (D.orders || []).filter(function (o) { return act.indexOf(o) < 0; });
    h += sec("주문 추적 · 진행 중", act.length);
    act.forEach(function (o) { h += orderRow(o); });
    h += '<details class="fold"><summary>지난 주문 ' + closed.length + '건</summary><div class="in">' + closed.map(orderRow).join("") + '</div></details>';
    h += foot();
    paint(h); bindChecks();
  }
  function orderRow(o) {
    var k = orderKind(o), cur = isKR(o.ticker) ? "KRW" : "USD";
    var meta = [o.price != null ? price(o.price, cur) : "", o.shares != null ? (isNaN(o.shares) ? esc(o.shares) : fmtShares(+o.shares) + "주") : ""].filter(Boolean).join(" · ");
    var longSt = String(o.status || "").length > 12;
    return '<div class="ord ' + k + '"><div class="row between" style="gap:8px"><span class="o-nm">' + esc(o.label || o.action || "") + '</span><span class="o-st ' + (k === "done" ? "fill" : k) + '">' + ORDER_LBL[k] + '</span></div>'
      + '<div class="o-meta">' + esc(o.action || "") + (meta ? ' · ' + meta : '') + (o.date ? ' <span class="mut">· ' + esc(o.date) + '</span>' : '') + '</div>'
      + (longSt ? '<div class="o-note">' + mdInline(esc(o.status)) + '</div>' : '') + (o.note ? '<div class="o-note">' + mdInline(esc(o.note)) + '</div>' : '') + '</div>';
  }

  // ════════════════ 화면: 리서치 허브 ════════════════
  function renderResearch() {
    var hu = D.hunter || {}, sc = hu.scorecard || {}, fd = D.feeds || {}, gf = D.guru_flows || {}, pv = D.pm_view || {}, dec = D.decisions || {};
    var r0 = (D.reports || [])[0] || {};
    var h = topbar({ title: "리서치", sub: "보고서 · 채널 · 대가 · 결정 기록" });
    function hub(href, ic, t, s) { return '<a class="hub" href="' + href + '"><span class="ic">' + ic + '</span><div class="flex1"><div class="t">' + esc(t) + '</div><div class="s clamp2">' + s + '</div></div><span class="chev">' + IC.chev + '</span></a>'; }
    h += hub("#reports", IC.doc, "일일 보고서 " + (D.reports || []).length, esc(r0.title || ""));
    h += hub("#pmview", IC.pm, "PM 사견", esc(pv.headline || "") + (pv.updated ? " · " + esc(pv.updated) : ""));
    h += hub("#hunter", IC.video, "경제사냥꾼", (sc.accuracy_pct != null ? "채널 정확도 " + sc.accuracy_pct + "% (채점 " + (sc.scored || sc.total) + "건) · " : "") + esc(hu.headline || ""));
    var chn = Object.keys(fd.channels || {}).map(function (k) { return (fd.channels[k] || {}).name || k; }).join(" · ");
    h += hub("#feeds", IC.radar, "외부 리서치", esc(chn || "채널 데이터 없음"));
    h += hub("#gurus", IC.guru, "대가 흐름 · 13F", esc((gf.as_of_quarter ? gf.as_of_quarter + " 분기 · " : "") + Object.keys(gf.gurus || {}).length + "인 · 지연 확증 렌즈"));
    h += hub("#decisions", IC.compass, "결정 · 전략 아젠다", "열린 질문 " + (dec.open_count || 0) + "건 · 전체 " + (dec.total || 0) + "건");
    h += hub("#trades", IC.ledger, "체결 원장 · 실현손익", esc(tradesSub()));
    h += hub("#archive", IC.archive, "영상 아카이브", (D.hunter_archive || []).length + "편 · 종목으로 필터");
    h += sec("시장 1개월");
    h += '<div class="card"><div class="ctitle">코스피</div>' + lineChart(D.kospi_history, "KRW") + '</div>';
    h += '<div class="card"><div class="ctitle">원/달러</div>' + lineChart(D.fx_history, "KRW") + '</div>';
    h += foot();
    paint(h);
  }

  // ════════════════ 하위 화면 (리서치·원장) ════════════════
  function subTop(back, backLabel, title, sub) { return topbar({ back: back, backLabel: backLabel, title: title, sub: sub }); }

  function renderTrades() {
    var t = D.trades || {};
    var h = subTop("#pf", "포트폴리오", "체결 원장 · 실현손익", "원장(trades.jsonl)이 정본 · 수량·평단·실현손익은 재생된 파생물");
    if (t.status !== "live") { paint(h + '<div class="empty">원장 데이터가 없습니다.</div>'); return; }
    if (t.reconcile_ok === false) h += '<div class="alert ins danger"><div class="aid">체결 원장 대사 실패</div><div class="act">' + esc((t.reconcile || []).map(function (r) { return r.label + "(" + r.detail + ")"; }).join(" · ")) + '</div></div>';
    else if (t.reconcile_ok) h += '<div class="hl" style="background:var(--good-soft)">원장 재생 = portfolio.json (전 종목 일치)</div>';
    var eras = t.eras || {}, ep = eras.pre || {}, ed = eras.desk || {};
    h += '<section class="stmt"><div class="lbl">누계 실현손익 (확보 구간 합)</div><div class="big num">' + sign(t.realized_krw) + num(t.realized_krw) + '<small>원</small></div>'
      + '<div class="grid3"><div><div class="k">데스크 이전</div><div class="v num ' + cls(ep.realized_krw) + '">' + sign(ep.realized_krw) + num(ep.realized_krw) + '</div><div class="s">' + (ep.n || 0) + '건 · 승률 ' + ep.win_rate + '%</div></div>'
      + '<div><div class="k">데스크 이후</div><div class="v num ' + cls(ed.realized_krw) + '">' + sign(ed.realized_krw) + num(ed.realized_krw) + '</div><div class="s">' + (ed.n || 0) + '건 · 승률 ' + ed.win_rate + '%</div></div>'
      + '<div><div class="k">체결</div><div class="v num">' + t.fills + '건</div><div class="s">+청산 ' + (t.closed_pre_desk || 0) + '</div></div></div></section>';
    var cov = t.coverage || {};
    if (cov.complete === false) h += '<div class="alert ins warning"><div class="aid">계좌 전체 실적이 아닙니다</div><div class="act">청산기록 확보 구간 ' + esc(cov.closed_from || "?") + ' ~ ' + esc(cov.closed_to || "?") + ' · 토스 조회범위 ' + esc(cov.toss_range || "") + '<br>' + (cov.gaps || []).map(esc).join('<br>') + '</div></div>';
    if (t.fx_estimated) h += '<div class="fxnote" style="margin-bottom:10px">일부 매도는 체결 시점 환율이 원장에 없어 현재 환율로 환산한 추정치입니다.</div>';
    h += sec("확정 손익", "매도 " + t.sells + "건");
    (t.sells_detail || []).forEach(function (d) {
      h += '<div class="trk"><div class="row between"><span class="bold">' + esc(d.label) + '</span><span class="num bold ' + cls(d.realized_krw) + '">' + sign(d.realized_krw) + num(d.realized_krw) + '원 <span class="sm">(' + pct(d.return_pct) + ')</span></span></div>'
        + '<div class="tx mut">' + esc(d.date) + ' · ' + (d.shares ? fmtShares(d.shares) + '주 @ ' + price(d.price, d.currency) : '주수·단가 미기록(청산 요약)') + (d.cost_basis ? ' · 원가 ' + price(d.cost_basis, d.currency) : '') + (d.era === "pre" ? ' · 데스크 이전' : '') + (d.fx_estimated ? ' · 추정환율' : '') + '</div>'
        + (d.note ? '<div class="tx">' + esc(d.note) + '</div>' : '') + '</div>';
    });
    h += sec("체결 이력", t.fills + "건");
    (t.recent || []).forEach(function (r) {
      var buy = r.side === "buy";
      h += '<div class="trk"><div class="row between"><span><span class="badge ' + (buy ? "buy" : "sell") + '">' + (buy ? "매수" : "매도") + '</span> <b>' + esc(r.label) + '</b></span><span class="dt">' + esc(r.date) + '</span></div>'
        + '<div class="tx mut num">' + fmtShares(r.shares) + '주 @ ' + price(r.price, r.currency) + '</div>' + (r.note ? '<div class="tx">' + esc(r.note) + '</div>' : '') + (r.source ? '<div class="tx src">출처 ' + esc(r.source) + '</div>' : '') + '</div>';
    });
    h += foot("체결 기입은 토스 확인 후에만 · 대사는 매 빌드 자동");
    paint(h);
  }

  function setupCards(sus, prefix) {
    var h = "";
    (sus || []).forEach(function (su) {
      var conds = Array.isArray(su.conditions) ? su.conditions : [], met = conds.filter(function (c) { return c.met; }).length;
      h += '<div class="card"><div class="row between" style="gap:8px"><span class="bold">' + esc(su.label || su.id) + '</span><span class="badge ' + (su.status === "발동" ? "warning" : su.status === "임박" ? "info" : "") + '">' + esc(su.status || "") + (conds.length ? ' ' + met + '/' + conds.length : '') + '</span></div>';
      if (su.thesis) h += '<div class="tx sm mut" style="margin-top:4px">' + esc(su.thesis) + '</div>';
      if (conds.length) { h += '<div style="margin-top:6px">'; conds.forEach(function (c) { h += '<div class="tx sm" style="margin-top:3px">' + (c.met ? '<b class="good">충족</b> ' : '<b class="mut">미충족</b> ') + esc(c.text) + '</div>'; }); h += '</div>'; }
      else if (typeof su.conditions === "string") h += '<div class="tx sm" style="margin-top:6px">' + esc(su.conditions) + '</div>';
      if (su.action) h += '<div class="tx sm" style="margin-top:6px"><b>액션:</b> ' + esc(su.action) + '</div>';
      if (su.note) h += '<div class="xs mut" style="margin-top:4px">' + esc(su.note) + '</div>';
      h += '</div>';
    });
    return h;
  }
  function tickerChips(tks, link) {
    if (!tks || !tks.length) return "";
    return '<div class="row wrap" style="margin-top:7px">' + tks.map(function (tk) { var st = find(tk); return st && link ? '<a class="tchip" href="#stock/' + encodeURIComponent(tk) + '">' + esc(st.label) + '</a>' : '<span class="tchip">' + esc(st ? st.label : tk) + '</span>'; }).join("") + '</div>';
  }
  function trackRows(tr) {
    return (tr || []).map(function (r) {
      return '<div class="trk"><div class="row between"><span class="dt">' + esc(r.date) + '</span>' + (r.verdict ? '<span class="itag ' + esc(r.verdict) + '">' + esc(r.verdict) + '</span>' : '') + '</div>'
        + (r.claim || r.actual ? '<div class="tx sm"><b>주장:</b> ' + esc(r.claim) + '</div><div class="tx sm mut"><b>실제:</b> ' + esc(r.actual) + '</div>' : (r.note ? '<div class="tx sm">' + esc(r.note) + '</div>' : '')) + '</div>';
    }).join("");
  }

  function renderHunter() {
    var hu = D.hunter || {};
    var h = subTop("#research", "리서치", "경제사냥꾼", esc(hu.source || "") + " · 갱신 " + esc(hu.updated || ""));
    if (!hu.latest_videos) { paint(h + '<div class="empty">경제사냥꾼 데이터가 없어요.</div>'); return; }
    if (hu.headline) h += '<div class="hl">' + esc(hu.headline) + '</div>';
    if (hu.channel_note) h += '<div class="comment sm">' + esc(hu.channel_note) + '</div>';
    var sc = hu.scorecard;
    if (sc && sc.total) {
      var bk = sc.buckets || {}, scored = sc.scored != null ? sc.scored : sc.total;
      var segs = [["정확", "var(--good)", bk["정확"]], ["근사", "color-mix(in srgb, var(--good) 55%, var(--surface))", bk["근사"]], ["시점", "var(--info)", bk["시점"]], ["미확인", "var(--warn)", bk["미확인"]], ["정정", "var(--bad)", bk["정정"]], ["과장", "color-mix(in srgb, var(--bad) 50%, var(--warn))", bk["과장"]], ["일반", "var(--mut2)", bk["일반"]], ["미채점", "var(--surface3)", bk["미채점"]]];
      h += '<div class="scard"><div class="row between"><span class="sck">채널 정확도 <span class="mut xs">(채점 ' + scored + '건)</span></span><span class="scacc num">' + sc.accuracy_pct + '%</span></div><div class="scbar">';
      segs.forEach(function (s) { if (s[2]) h += '<span class="scseg" style="flex:' + s[2] + ';background:' + s[1] + '"></span>'; });
      h += '</div><div class="row wrap sclegend">';
      segs.forEach(function (s) { if (s[2]) h += '<span><span class="lg" style="background:' + s[1] + '"></span>' + s[0] + ' ' + s[2] + '</span>'; });
      h += '</div><div class="xs mut" style="margin-top:7px;line-height:1.6">방향성 채택 · 숫자는 교차검증 전제. 분모 = 판정 확정분만(일반·미채점 제외). 총 ' + sc.total + '건 중 검증 커버리지 ' + (sc.coverage_pct != null ? sc.coverage_pct + '%' : '—') + '. 표본이 무작위가 아니다(주말·저녁 업로드 누락) — 채널 전체 적중률로 일반화하지 말 것.</div></div>';
    }
    if ((D.hunter_archive || []).length) h += '<a class="hub" href="#archive"><span class="ic">' + IC.archive + '</span><div><div class="t">전체 영상 아카이브</div><div class="s">' + D.hunter_archive.length + '편</div></div><span class="chev">' + IC.chev + '</span></a>';
    if ((hu.setups || []).length) h += sec("조건 트래커", hu.setups.length) + setupCards(hu.setups);
    var vids = hu.latest_videos || [];
    h += sec("최신 영상 분석", vids.length);
    vids.forEach(function (v, idx) {
      h += '<a class="vid" href="#video/' + encodeURIComponent(v.id || String(idx)) + '" style="display:block"><div class="top"><span class="itag ' + esc(v.tag || "") + '">' + esc(v.tag || "") + '</span><span class="dt">' + esc(v.date || "") + '</span><span class="vmore">자세히</span></div>'
        + '<div class="vtitle">' + esc(v.title) + '</div><div class="tx clamp">' + esc(v.summary || v.note || "") + '</div>' + tickerChips(v.tickers, false) + '</a>';
    });
    if ((hu.track_record || []).length) h += sec("채널 트랙레코드") + trackRows(hu.track_record);
    if ((hu.themes || []).length) h += sec("반복 논지 · 테마") + hu.themes.map(function (x) { return '<div class="theme">' + esc(x) + '</div>'; }).join("");
    h += foot("방향성은 채택, 수치는 교차검증");
    paint(h);
  }

  function renderFeeds() {
    var fd = D.feeds || {}, chs = fd.channels || {}, keys = Object.keys(chs);
    var h = subTop("#research", "리서치", "외부 리서치", "수페TV·지식인사이드 · " + esc(fd.source || "") + (fd.updated ? " · 갱신 " + esc(fd.updated) : ""));
    h += '<div class="comment sm">경제사냥꾼과 별개로 추적하는 외부 채널. 트랙레코드·정확도 통계는 섞지 않음(정본 분리). 방향성은 참고, 수치는 교차검증 전제.</div>';
    if (!keys.length) { paint(h + '<div class="empty">외부 채널 데이터가 없어요.</div>'); return; }
    keys.forEach(function (k) {
      var ch = chs[k] || {};
      h += sec(ch.name || k);
      if (ch.headline) h += '<div class="hl">' + esc(ch.headline) + '</div>';
      if (ch.channel_note) h += '<div class="comment sm">' + esc(ch.channel_note) + '</div>';
      h += setupCards(ch.setups);
      (ch.latest_videos || []).forEach(function (v, idx) {
        h += '<a class="vid" style="display:block" href="#fvid/' + encodeURIComponent(k) + '/' + encodeURIComponent(v.id || String(idx)) + '"><div class="top"><span class="itag ' + esc(v.tag || "") + '">' + esc(v.tag || v.verdict || "") + '</span><span class="dt">' + esc(v.date || "") + '</span><span class="vmore">자세히</span></div>'
          + '<div class="vtitle">' + esc(v.title || "") + '</div>' + (v.guest ? '<div class="guest">' + esc(v.guest) + '</div>' : '') + '<div class="tx clamp">' + esc(v.summary || v.note || "") + '</div>' + tickerChips(v.tickers, false) + '</a>';
      });
      if ((ch.themes || []).length) h += '<div class="bold sm" style="margin:12px 0 6px">반복 논지 · 테마</div>' + ch.themes.map(function (x) { return '<div class="theme">' + esc(x) + '</div>'; }).join("");
      if ((ch.track_record || []).length) h += '<div class="bold sm" style="margin:12px 0 6px">트랙레코드</div>' + trackRows(ch.track_record);
    });
    h += foot("경제사냥꾼과 트랙레코드 분리");
    paint(h);
  }

  function renderGurus() {
    var gf = D.guru_flows || {}, gurus = gf.gurus || {}, keys = Object.keys(gurus);
    var h = subTop("#research", "리서치", "대가 흐름 · 13F", esc(gf.source || "SEC EDGAR 13F") + (gf.as_of_quarter ? " · " + esc(gf.as_of_quarter) + " 분기" : "") + (gf.updated ? " · 갱신 " + esc(gf.updated) : ""));
    h += '<div class="comment sm">대가의 13F 보유변동과 <b>그 이유</b>를 우리 관점에서 참고. 분기말 후 약 45일 지연된 <b>확증 렌즈</b>이지 매수 트리거가 아니다(단일출처 매수 금지).</div>';
    if (!keys.length) { paint(h + '<div class="empty">대가 데이터가 없어요.</div>'); return; }
    function fmtUsd(v) { v = v || 0; return v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : v >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M' : '$' + num(v); }
    var actLbl = { NEW: "신규", ADD: "증량", TRIM: "축소", EXIT: "청산", HOLD: "유지" }, actCls = { NEW: "buy", ADD: "buy", TRIM: "sell", EXIT: "sell", HOLD: "hold" };
    var guruShort = { berkshire: "버핏", scion: "버리", duquesne: "드러켄밀러", pershing: "애크먼", appaloosa: "테퍼", thirdpoint: "로엡" };
    function traj(g, tk) {
      var t = g.trajectory || {}, byQ = {};
      Object.keys(t).forEach(function (c) { if (t[c].ticker !== tk) return; (t[c].series || []).forEach(function (s) { byQ[s.quarter] = (byQ[s.quarter] || 0) + (s.pct || 0); }); });
      return Object.keys(byQ).sort().map(function (q) { return byQ[q]; });
    }
    var cons = gf.consensus || {}, ckeys = Object.keys(cons).sort(function (a, b) { return (cons[b].holders.length - cons[a].holders.length) || (Math.abs(cons[b].net) - Math.abs(cons[a].net)); });
    if (ckeys.length) {
      h += sec("우리 포트 × 대가") + '<div class="xs mut" style="margin:-4px 2px 8px">매수·매도 진영이 갈리면 대가도 확신 못 하는 것 = 과신 금지</div>';
      ckeys.forEach(function (tk) {
        var c = cons[tk], st = find(tk);
        h += '<div class="card"><div class="row between"><a class="bold" href="#stock/' + encodeURIComponent(tk) + '">' + esc(tk) + (st ? ' · ' + esc(st.label) : '') + '</a><span class="badge ' + (c.net > 0 ? "buy" : c.net < 0 ? "sell" : "hold") + '">매수 ' + c.buy + ' · 매도 ' + c.sell + (c.hold ? ' · 유지 ' + c.hold : '') + '</span></div><div class="row wrap" style="margin-top:7px">';
        c.holders.forEach(function (hd) { h += '<span class="gchip ' + (actCls[hd.action] || "hold") + '">' + esc(guruShort[hd.slug] || hd.guru) + ' ' + (actLbl[hd.action] || hd.action) + '</span>'; });
        h += '</div></div>';
      });
    }
    keys.forEach(function (k) {
      var g = gurus[k] || {};
      h += sec(g.name || k);
      if (g.error) { h += '<div class="empty sm">수집 오류: ' + esc(g.error) + '</div>'; return; }
      h += '<div class="xs mut" style="margin:-4px 2px 8px">' + esc(g.quarter || "") + ' 기준 · 포트 ' + fmtUsd(g.portfolio_value_usd) + ' · ' + (g.positions || 0) + '종목 · 공시 ' + esc(g.filing_date || "") + '</div>';
      if (g.narrative) h += '<div class="hl">' + esc(g.narrative) + '</div>';
      (g.themes || []).forEach(function (x) { h += '<div class="theme">' + esc(x) + '</div>'; });
      (g.overlap_with_holdings || []).forEach(function (o) {
        var st = find(o.ticker), dp = o.shares_delta_pct != null ? ' ' + sign(o.shares_delta_pct) + o.shares_delta_pct + '%' : '';
        h += '<div class="card"><div class="row between"><a class="bold" href="#stock/' + encodeURIComponent(o.ticker) + '">' + esc(o.ticker) + (st ? ' · ' + esc(st.label) : '') + '</a><span class="badge ' + (actCls[o.action] || '') + '">' + (actLbl[o.action] || o.action) + dp + '</span></div>'
          + '<div class="row between" style="margin-top:4px"><span class="xs mut">' + esc(o.issuer || "") + ' · ' + fmtUsd(o.value_to) + '</span>' + sparkSVG(traj(g, o.ticker), 100, 26) + '</div>'
          + (o.our_takeaway ? '<div class="tx sm" style="margin-top:5px">' + esc(o.our_takeaway) + '</div>' : '') + '</div>';
      });
      var tops = g.top_positions || [];
      if (tops.length) {
        h += '<details class="fold"><summary>상위 보유 Top 10</summary><div class="in">';
        tops.slice(0, 10).forEach(function (r) {
          h += '<div class="gbar"><div class="row between"><span class="sm' + (r.ticker ? ' bold' : '') + '">' + esc(r.issuer || "") + (r.ticker ? ' <span class="tchip">' + esc(r.ticker) + '</span>' : '') + '</span><span class="xs mut num">' + (r.pct || 0).toFixed(1) + '% · ' + fmtUsd(r.value_usd) + '</span></div>'
            + '<div class="gtrack"><div class="gfill' + (r.ticker ? ' mine' : '') + '" style="width:' + Math.max(2, Math.min(100, r.pct || 0)) + '%"></div></div></div>';
        });
        h += '</div></details>';
      }
      var moves = g.moves || [], ann = moves.filter(function (m) { return m.rationale; }), shown = ann.length ? ann : moves.slice(0, 12);
      if (shown.length) {
        h += '<details class="fold"><summary>분기 변동 · 왜 (vs ' + esc(g.prev_quarter || "") + ')</summary><div class="in">';
        shown.forEach(function (m) {
          var dp = m.shares_delta_pct != null ? ' ' + sign(m.shares_delta_pct) + m.shares_delta_pct + '%' : '';
          h += '<div class="card"><div class="row between" style="gap:8px"><span class="bold">' + esc(m.issuer || "") + (m.ticker ? ' <span class="tchip">' + esc(m.ticker) + '</span>' : '') + '</span><span class="badge ' + (actCls[m.action] || '') + '">' + (actLbl[m.action] || m.action) + dp + '</span></div>'
            + (m.rationale ? '<div class="tx sm" style="margin-top:4px"><b>왜:</b> ' + esc(m.rationale) + (m.tag ? ' <span class="itag ' + esc(m.tag) + '">' + esc(m.tag) + '</span>' : '') + '</div>' : '')
            + (m.our_takeaway ? '<div class="tx sm mut" style="margin-top:3px">' + esc(m.our_takeaway) + '</div>' : '') + '</div>';
        });
        h += '</div></details>';
      }
      if ((g.sources || []).length) h += '<div class="xs mut" style="margin-top:6px">출처 ' + esc(g.sources.join(" · ")) + '</div>';
    });
    h += foot("SEC EDGAR 13F + 외신·sell-side 이유분석 · 지연 확증 렌즈");
    paint(h);
  }

  function videoBody(v, related) {
    var h = '<div class="vhead"><div class="top"><span class="itag ' + esc(v.tag || "") + '">' + esc(v.tag || "") + '</span>' + (v.verdict ? '<span class="badge">' + esc(v.verdict) + '</span>' : '') + '<span class="dt">' + esc(v.date || "") + '</span></div>'
      + '<div class="vhtitle">' + esc(v.title || "") + '</div>' + (v.guest ? '<div class="guest">' + esc(v.guest) + '</div>' : '') + (v.link ? '<br><a class="vlink" href="' + esc(v.link) + '" target="_blank" rel="noopener">영상 보기</a>' : '') + '</div>';
    h += sec("요약") + '<div class="comment">' + esc(v.summary || v.note || "—") + '</div>';
    if ((v.points || []).length) h += sec("핵심 포인트") + '<div class="vpoints">' + v.points.map(function (p) { return '<div class="vpoint">' + esc(p) + '</div>'; }).join("") + '</div>';
    if (v.mentions) h += sec("언급 내용") + '<div class="comment sm">' + esc(v.mentions) + '</div>';
    if ((v.tickers || []).length) h += sec("언급 종목") + tickerChips(v.tickers, true);
    if ((v.references || []).length) h += sec("참고 · 출처") + '<div class="row wrap">' + v.references.map(function (r) { return '<span class="refchip">' + esc(r) + '</span>'; }).join("") + '</div>';
    if ((v.caveats || []).length) h += sec("주의 · 교차검증") + v.caveats.map(function (c) { return '<div class="caveat">' + esc(c) + '</div>'; }).join("");
    if (related && related.length) h += sec("검증 이력") + trackRows(related);
    return h;
  }
  function renderVideo(id) {
    var hu = D.hunter || {}, vids = hu.latest_videos || [], v = null;
    for (var i = 0; i < vids.length; i++) if ((vids[i].id || String(i)) === id) { v = vids[i]; break; }
    var h = subTop("#hunter", "경제사냥꾼");
    if (!v) { paint(h + '<div class="empty">영상을 찾을 수 없어요.</div>'); return; }
    var related = (hu.track_record || []).filter(function (rec) { var c = rec.claim || ""; return (v.tickers || []).some(function (tk) { var st = find(tk); return st && c.indexOf(st.label) !== -1; }); });
    paint(h + videoBody(v, related) + foot("방향성은 채택, 수치는 교차검증"));
  }
  function renderFeedVideo(param) {
    var slash = param.indexOf("/"), key = decodeURIComponent(slash >= 0 ? param.slice(0, slash) : param), id = slash >= 0 ? decodeURIComponent(param.slice(slash + 1)) : "";
    var ch = ((D.feeds && D.feeds.channels) || {})[key] || {}, vids = ch.latest_videos || [], v = null;
    for (var i = 0; i < vids.length; i++) if ((vids[i].id || String(i)) === id) { v = vids[i]; break; }
    var h = subTop("#feeds", "외부 리서치");
    if (!v) { paint(h + '<div class="empty">영상을 찾을 수 없어요.</div>'); return; }
    paint(h + '<div class="xs mut" style="margin-bottom:4px">' + esc(ch.name || key) + '</div>' + videoBody(v) + foot("경제사냥꾼과 트랙레코드 분리"));
  }

  function renderPMView() {
    var pv = D.pm_view || {}, items = pv.items || [];
    var h = subTop("#research", "리서치", "PM 사견", "룰을 잠시 내려놓고 본 독립 시선 · 갱신 " + esc(pv.updated || ""));
    if (pv.headline) h += '<div class="hl">' + esc(pv.headline) + '</div>';
    if (pv.philosophy) h += '<div class="comment sm">' + esc(pv.philosophy) + '</div>';
    if (!items.length) { paint(h + '<div class="empty">아직 등록된 사견이 없어요.</div>'); return; }
    h += sec("독립 의견", items.length);
    items.forEach(function (it) {
      var sc = it.stance === "강세" ? "up" : it.stance === "신중" ? "down" : "";
      h += '<div class="pmcard"><div class="row wrap" style="align-items:center">' + (it.stance ? '<span class="pmtag ' + sc + '">' + esc(it.stance) + '</span>' : '') + (it.align ? '<span class="pmtag">룰 ' + esc(it.align) + '</span>' : '') + (it.conviction ? '<span class="xs mut">확신 ' + esc(it.conviction) + '</span>' : '')
        + '<span class="xs mut" style="margin-left:auto">' + esc(it.topic || "") + ' · ' + esc(it.date || "") + '</span></div><div class="pmtitle">' + esc(it.title || "") + '</div><div class="md-body">' + mdToHtml(it.view || "") + '</div>'
        + (it.rule_note ? '<div class="pmrule"><b>룰 vs 내 시선 — </b>' + esc(it.rule_note) + '</div>' : '') + '</div>';
    });
    paint(h + foot("포트 운용은 룰이 우선 · 이 칸은 다른 시선 보조용"));
  }

  function renderDecisions() {
    var d = D.decisions || {}, op = d.open || [], cl = d.closed || [];
    var h = subTop("#research", "리서치", "결정 · 전략 아젠다", "왜 그렇게 결정했나 + 큰그림 열린 질문 · master §9·§10의 폰 뷰");
    if (!op.length && !cl.length) { paint(h + '<div class="empty">결정 메모리가 없어요.</div>'); return; }
    function card(it, open) {
      return '<div class="pmcard"><div class="row" style="gap:6px"><span class="pmtag ' + (open ? "open" : "") + '">' + (open ? "열림" : "결정") + '</span><span class="xs mut" style="margin-left:auto">' + esc(it.date || "") + '</span></div>'
        + '<div class="pmtitle">' + esc(it.topic || "") + '</div>' + (it.decision ? '<div class="md-body sm">' + mdInline(esc(it.decision)) + '</div>' : '')
        + (it.rationale ? '<div class="comment sm" style="margin-top:8px"><b>근거 — </b>' + mdInline(esc(it.rationale)) + '</div>' : '') + (it.rejected ? '<div class="comment sm mut"><b>기각·대안 — </b>' + mdInline(esc(it.rejected)) + '</div>' : '')
        + ((it.tags || []).length ? '<div class="row wrap" style="margin-top:6px">' + it.tags.map(function (t) { return '<span class="tag">' + esc(t) + '</span>'; }).join("") + '</div>' : '')
        + (it.refs ? '<div class="xs mut" style="margin-top:5px">' + esc(it.refs) + '</div>' : '') + '</div>';
    }
    if (op.length) h += sec("열린 전략 아젠다", op.length) + op.map(function (it) { return card(it, true); }).join("");
    if (cl.length) h += sec("최근 결정", cl.length) + cl.map(function (it) { return card(it, false); }).join("");
    paint(h + foot("정본 docs/master.md §9·§10 + data/app/decisions.jsonl"));
  }

  var reportFilter = "전체";
  function renderReports() {
    var all = D.reports || [];
    var h = subTop("#research", "리서치", "일일 보고서", all.length + "개 · 최신순");
    if (!all.length) { paint(h + '<div class="empty">보고서가 없어요.</div>'); return; }
    var kinds = ["전체"]; all.forEach(function (r) { if (kinds.indexOf(r.kind) === -1) kinds.push(r.kind); });
    h += '<div class="filters">' + kinds.map(function (k) { var n = k === "전체" ? all.length : all.filter(function (r) { return r.kind === k; }).length; return '<button type="button" class="fchip' + (k === reportFilter ? " on" : "") + '" data-k="' + esc(k) + '" aria-pressed="' + (k === reportFilter) + '">' + esc(k) + ' ' + n + '</button>'; }).join("") + '</div>';
    var reps = reportFilter === "전체" ? all : all.filter(function (r) { return r.kind === reportFilter; }), last = null;
    reps.forEach(function (r) {
      if (r.date && r.date !== last) { h += '<div class="rdate">' + esc(r.date) + '</div>'; last = r.date; }
      h += '<a class="rep" href="#report/' + encodeURIComponent(r.id) + '"><div class="flex1"><span class="tag">' + esc(r.kind || "") + '</span> ' + (r.version != null ? '<span class="tag vtag">v' + esc(r.version) + '</span>' : '')
        + '<div class="nm">' + esc(r.title) + '</div>' + (r.preview ? '<div class="rprev">' + esc(r.preview) + '</div>' : '') + '</div><span class="chev">' + IC.chev + '</span></a>';
    });
    paint(h + foot("docs/reports/ 원문 그대로"));
    Array.prototype.forEach.call(root.querySelectorAll(".fchip"), function (b) { b.addEventListener("click", function () { reportFilter = b.getAttribute("data-k"); render(); window.scrollTo(0, 0); }); });
  }

  var lazyBodies = {};
  // 최신 3편 외 본문은 app/r/<id>.js — fetch가 아니라 <script>(file:// 에서도 열리게)
  function loadReportBody(id, cb) {
    if (lazyBodies[id] != null) { cb(lazyBodies[id]); return; }
    var s = document.createElement("script");
    s.src = "r/" + encodeURIComponent(id) + ".js";
    s.onload = function () { var got = window.__REPORT_BODY__; window.__REPORT_BODY__ = null; if (got && got.id === id && got.content) { lazyBodies[id] = got.content; cb(got.content); } else cb(null); if (s.parentNode) s.parentNode.removeChild(s); };
    s.onerror = function () { cb(null); if (s.parentNode) s.parentNode.removeChild(s); };
    document.head.appendChild(s);
  }
  function renderReport(id) {
    var reps = D.reports || [], r = null;
    for (var i = 0; i < reps.length; i++) if (reps[i].id === id) { r = reps[i]; break; }
    var top = subTop("#reports", "보고서 목록");
    if (!r) { paint(top + '<div class="empty">보고서를 찾을 수 없어요.</div>'); return; }
    var head = top + '<div class="rphead"><div class="row" style="gap:6px"><span class="tag">' + esc(r.kind || "") + '</span>' + (r.version != null ? '<span class="tag vtag">v' + esc(r.version) + '</span>' : '') + (r.date ? '<span class="dt">' + esc(r.date) + '</span>' : '') + '</div>'
      + '<div class="rptitle">' + esc(r.title) + '</div><div class="rpfile">' + esc(r.file) + '</div></div>';
    function draw(body, note) {
      var b = String(body || "").replace(/^﻿?\s*#\s+.*(\r?\n|$)/, "");
      paint(head + (note ? '<div class="empty">' + esc(note) + '</div>' : '<div class="md-body">' + mdToHtml(b) + '</div>') + foot());
    }
    if (r.content) { draw(r.content); return; }
    draw("", "본문 불러오는 중…");
    loadReportBody(r.id, function (body) { if (location.hash.replace(/^#/, "") !== "report/" + encodeURIComponent(id) && location.hash.replace(/^#/, "") !== "report/" + id) return; if (body) draw(body); else draw("", "본문을 불러오지 못했어요. 오프라인이면 온라인에서 한 번 열어 주세요 — 그다음부터는 오프라인에서도 보여요."); });
  }

  var archFilter = "전체";
  function verdictClass(v) { v = v || ""; if (v.indexOf("정정") >= 0 || v.indexOf("오류") >= 0) return "정정"; if (v.indexOf("미확인") >= 0) return "미확인"; if (v.indexOf("과장") >= 0) return "과장"; return "검증"; }
  function renderArchive() {
    var all = D.hunter_archive || [];
    var h = subTop("#hunter", "경제사냥꾼", "전체 영상 아카이브", all.length + "편 · 첫 영상부터 · 종목으로 필터");
    if (!all.length) { paint(h + '<div class="empty">아카이브 데이터가 없어요.</div>'); return; }
    var cnt = {}; all.forEach(function (v) { (v.tickers || []).forEach(function (tk) { cnt[tk] = (cnt[tk] || 0) + 1; }); });
    var chips = ["전체"].concat(Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; }));
    h += '<div class="filters">' + chips.map(function (k) { var st = find(k), lab = k === "전체" ? "전체 " + all.length : (st ? st.label : k) + " " + cnt[k]; return '<button type="button" class="fchip' + (k === archFilter ? " on" : "") + '" data-k="' + esc(k) + '" aria-pressed="' + (k === archFilter) + '">' + esc(lab) + '</button>'; }).join("") + '</div>';
    var rows = archFilter === "전체" ? all : all.filter(function (v) { return (v.tickers || []).indexOf(archFilter) >= 0; }), last = null;
    rows.forEach(function (v) {
      if (v.date !== last) { h += '<div class="rdate">' + esc(v.date) + '</div>'; last = v.date; }
      h += '<div class="avid"><div class="row between" style="gap:8px;align-items:flex-start"><span class="avtitle">' + esc(v.title) + '</span><span class="itag ' + verdictClass(v.verdict) + '">' + esc(v.verdict || "") + '</span></div>'
        + (v.theme ? '<div class="atheme">' + esc(v.theme) + '</div>' : '') + '<div class="atx">' + esc(v.takeaway || "") + '</div>' + tickerChips(v.tickers, true) + '</div>';
    });
    paint(h + foot("방향성 채택 · 수치는 교차검증"));
    Array.prototype.forEach.call(root.querySelectorAll(".fchip"), function (b) { b.addEventListener("click", function () { archFilter = b.getAttribute("data-k"); render(); window.scrollTo(0, 0); }); });
  }

  // ════════════════ 라우팅 · 탭 ════════════════
  // [9/21 r2] 캔버스 = 4탭. 계획은 오늘 화면에서 들어가고 탭은 오늘에 불이 들어온다
  var TABS = [["", "오늘", "today"], ["pf", "포트폴리오", "pf"], ["rules", "룰·리스크", "rules"], ["research", "리서치", "research"]];
  function hashNow() { return location.hash.replace(/^#/, ""); }
  function tabOf(h) {
    if (!h) return "";
    if (h === "pf" || h.indexOf("stock/") === 0 || h === "trades") return "pf";
    if (h === "rules") return "rules";
    if (h === "plan") return "";
    return "research";
  }
  function drawTabs() {
    if (!tabsEl) return;
    var cur = tabOf(hashNow());
    tabsEl.innerHTML = '<div class="tabs-in">' + TABS.map(function (t) {
      var on = t[0] === cur;
      return '<a class="tab' + (on ? " on" : "") + '" href="#' + t[0] + '"' + (on ? ' aria-current="page"' : '') + '>' + IC[t[2]] + '<span>' + t[1] + '</span></a>';
    }).join("") + '</div>';
  }
  function paint(h) {
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
    setPill();
    var lp = document.getElementById("livepill"); if (lp) lp.addEventListener("click", function () { fetchLive(); });
    var tb = document.getElementById("themebtn"); if (tb) tb.addEventListener("click", cycleTheme);
    onScroll();
  }
  function render() {
    var h = hashNow();
    if (h.indexOf("stock/") === 0) renderDetail(decodeURIComponent(h.slice(6)));
    else if (h === "pf") renderPf();
    else if (h === "rules") renderRules();
    else if (h === "plan") renderPlan();
    else if (h === "research") renderResearch();
    else if (h.indexOf("report/") === 0) renderReport(decodeURIComponent(h.slice(7)));
    else if (h === "reports") renderReports();
    else if (h.indexOf("video/") === 0) renderVideo(decodeURIComponent(h.slice(6)));
    else if (h.indexOf("fvid/") === 0) renderFeedVideo(h.slice(5));
    else if (h === "feeds") renderFeeds();
    else if (h === "gurus") renderGurus();
    else if (h === "archive") renderArchive();
    else if (h === "hunter") renderHunter();
    else if (h === "pmview") renderPMView();
    else if (h === "decisions") renderDecisions();
    else if (h === "trades") renderTrades();
    else renderToday();
    drawTabs();
  }
  // 실시간 갱신 — 가격이 쓰이는 화면만 다시 그린다(보고서 읽는 중엔 알약만 갱신)
  function rerender() {
    var h = hashNow();
    var livePage = !h || h === "pf" || h === "rules" || h === "plan" || h.indexOf("stock/") === 0;
    if (!livePage) { setPill(); return; }
    var y = window.scrollY || 0;
    var openFolds = Array.prototype.map.call(root.querySelectorAll("details.fold"), function (d) { return d.open; });
    render();
    Array.prototype.forEach.call(root.querySelectorAll("details.fold"), function (d, i) { if (openFolds[i]) d.open = true; });
    window.scrollTo(0, y);
  }
  function onScroll() { var t = root.querySelector(".topbar"); if (t) t.classList.toggle("scrolled", (window.scrollY || 0) > 4); }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("hashchange", function () { render(); window.scrollTo(0, 0); });

  if (!D) { root.innerHTML = '<div class="empty">데이터(data.js)가 없어요. build_app_data.py를 먼저 실행하세요.</div>'; return; }
  render();
  fetchLive();
  // 화면이 보일 때만 60초마다 — live.json은 5~10분마다 바뀌므로 이 이상 자주 볼 이유가 없다
  setInterval(function () { if (document.visibilityState === "visible") fetchLive(); else setPill(); }, 60000);
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible" && Date.now() - lastFetch > 20000) fetchLive(); });
  window.addEventListener("online", function () { fetchLive(); });
})();
