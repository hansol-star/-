/* 정훈 증권 포트폴리오 앱 — 정적 SPA. window.APP_DATA(data.js) 하나만 읽는다. */
(function () {
  "use strict";
  var D = window.APP_DATA;
  var root = document.getElementById("app");

  // ── helpers ──
  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(n) { return n == null ? "—" : Number(n).toLocaleString("ko-KR"); }
  function won(n) { return n == null ? "—" : Number(n).toLocaleString("ko-KR") + "원"; }
  function price(p, cur) {
    if (p == null) return "—";
    if (cur === "USD") return "$" + Number(p).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return Number(p).toLocaleString("ko-KR") + "원";
  }
  function pct(p) { if (p == null) return "—"; return (p >= 0 ? "+" : "") + Number(p).toFixed(2) + "%"; }
  function cls(p) { return p == null ? "" : (p >= 0 ? "up" : "down"); }
  function stars(n) { n = n || 0; return "★★★★★".slice(0, n) + "☆☆☆☆☆".slice(0, 5 - n); }

  // ── routing (hash) ──
  function route() {
    var h = location.hash.replace(/^#/, "");
    if (h.indexOf("stock/") === 0) renderDetail(decodeURIComponent(h.slice(6)));
    else renderHome();
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", route);

  function find(tk) {
    var all = (D.holdings || []).concat(D.watchlist || []);
    for (var i = 0; i < all.length; i++) if (all[i].ticker === tk) return all[i];
    return null;
  }

  // ── HOME ──
  function renderHome() {
    var t = D.totals || {}, s = D.safety || {};
    var pinTxt = { ok: "정상 — 안전핀 이격 충분", watch: "주의 — 2차 트랜치 구간(8,000 부근)", freeze: "⚠ 동결 — 안전핀 하회, 잔여 트랜치 전면 동결", unknown: "코스피 시세 미확인" };
    var firedAlerts = (D.alerts || []).filter(function (a) { return a.fired; });
    var events = (D.alerts || []).filter(function (a) { return a.cond === "event" || a.cond === "signal"; });

    var h = "";
    h += '<header><div class="title">정훈 증권 · 포트폴리오</div>';
    h += '<div class="sub">' + esc(D.as_of || "") + ' · 갱신 ' + esc(D.generated_at || "") + (D.offline ? " · 오프라인" : "") + '</div></header>';

    // hero
    h += '<div class="hero"><div class="lbl">총 자산</div>';
    h += '<div class="big">' + won(t.assets_krw) + '</div>';
    h += '<div class="row" style="gap:12px"><span class="' + cls(t.day_change_krw) + ' bold">당일 ' + (t.day_change_krw >= 0 ? "+" : "") + num(t.day_change_krw) + '원 (' + pct(t.day_change_pct) + ')</span></div>';
    h += '<div class="chips">';
    h += '<div class="chip"><div class="mut">평가손익</div><div class="v ' + cls(t.total_pnl_krw) + '">' + (t.total_pnl_krw >= 0 ? "+" : "") + num(t.total_pnl_krw) + '원<br><span class="sm">' + pct(t.total_pnl_pct) + '</span></div></div>';
    h += '<div class="chip"><div class="mut">현금</div><div class="v">' + num(t.cash_krw) + '원</div></div>';
    h += '<div class="chip"><div class="mut">환율</div><div class="v">₩' + num(D.fx && D.fx.usdkrw) + '</div></div>';
    h += '</div></div>';

    // safety pin
    h += '<div class="pin ' + (s.status || "unknown") + '"><div><div class="xs">코스피 매수 안전핀 ' + num(s.pin) + '</div><div>' + esc(pinTxt[s.status] || "") + '</div></div>';
    h += '<div class="pv">' + num(s.price) + ' <span class="sm ' + cls(s.change_pct) + '">' + pct(s.change_pct) + '</span></div></div>';

    // fired triggers
    if (firedAlerts.length) {
      h += '<div class="sec"><h2>🔔 발동 트리거 (' + firedAlerts.length + ')</h2></div>';
      firedAlerts.forEach(function (a) {
        h += '<div class="alert fired"><div class="row between"><span class="aid">' + esc(a.id) + '</span><span class="badge">발동</span></div><div class="act">' + esc(a.action) + '</div></div>';
      });
    }

    // indices
    h += '<div class="sec"><h2>지수</h2></div><div class="row wrap" style="gap:8px">';
    (D.indices || []).forEach(function (i) {
      h += '<div class="chip" style="flex:1;min-width:30%"><div class="mut sm">' + esc(i.label) + '</div><div class="v">' + num(i.price) + '<br><span class="sm ' + cls(i.change_pct) + '">' + pct(i.change_pct) + '</span></div></div>';
    });
    h += '</div>';

    // holdings
    h += '<div class="sec"><h2>보유 ' + (D.holdings || []).length + '종목</h2></div><div class="list">';
    (D.holdings || []).forEach(function (st) { h += itemRow(st, true); });
    h += '</div>';

    // watchlist
    if ((D.watchlist || []).length) {
      h += '<div class="sec"><h2>워치리스트</h2></div><div class="list">';
      (D.watchlist || []).forEach(function (st) { h += itemRow(st, false); });
      h += '</div>';
    }

    // events / schedule
    if (events.length) {
      h += '<div class="sec"><h2>이벤트 · 시그널</h2></div>';
      events.forEach(function (a) {
        h += '<div class="alert"><div class="row between"><span class="aid">' + esc(a.id) + '</span><span class="badge evt">' + esc(a.when || "") + '</span></div><div class="act">' + esc(a.action) + '</div></div>';
      });
    }

    h += '<div class="foot">정훈 증권 — 1인 프라이빗 리서치 데스크<br>' + esc(D.source_report || "") + '<br>투자 자문 아님 · 모든 레벨은 분석 참고 · 최종 결정은 정훈.</div>';

    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  function itemRow(st, isHolding) {
    var pnl = isHolding ? st.pnl_pct : null;
    var line = '<div class="item" onclick="location.hash=\'stock/' + encodeURIComponent(st.ticker) + '\'">';
    line += '<span class="dot ' + (st.outlook || "hold") + '"></span>';
    line += '<div class="flex1"><div class="nm">' + esc(st.label) + '</div>';
    line += '<div class="row" style="gap:8px;margin-top:1px"><span class="stars">' + stars(st.stars) + '</span><span class="tk">' + esc(st.ticker) + '</span></div></div>';
    line += '<div class="right"><div class="px">' + price(st.price, st.currency) + '</div>';
    line += '<div class="sm ' + cls(st.change_pct) + '">' + pct(st.change_pct);
    if (isHolding && pnl != null) line += ' <span class="mut">·</span> <span class="' + cls(pnl) + '">' + pct(pnl) + '</span>';
    line += '</div></div></div>';
    return line;
  }

  // ── DETAIL ──
  function renderDetail(tk) {
    var st = find(tk);
    if (!st) { root.innerHTML = '<header><a class="back" href="#">← 뒤로</a></header><div class="empty">종목을 찾을 수 없어요.</div>'; return; }
    var isHolding = st.region != null;

    var h = '<header><a class="back" href="#">← 포트폴리오</a></header>';
    h += '<div class="dhero"><div class="row between"><div class="nm">' + esc(st.label) + '</div><div class="stars" style="font-size:14px">' + stars(st.stars) + '</div></div>';
    h += '<div class="tk mut sm">' + esc(st.ticker) + '</div>';
    h += '<div class="dprice">' + price(st.price, st.currency) + ' <span class="' + cls(st.change_pct) + '" style="font-size:16px">' + pct(st.change_pct) + '</span></div></div>';

    h += '<div class="kv">';
    if (isHolding) {
      h += box("평가손익", '<span class="' + cls(st.pnl_krw) + '">' + (st.pnl_krw >= 0 ? "+" : "") + num(st.pnl_krw) + '원 (' + pct(st.pnl_pct) + ')</span>');
      h += box("평가금액", num(st.value_krw) + '원');
      h += box("보유수량", num(st.shares) + '주');
      h += box("평단", price(st.cost, st.currency));
    }
    h += box("목표가", esc(st.target || "—"));
    if (isHolding) {
      h += box("매수존", esc(st.buy_zone || "—"));
      h += boxFull("트림/매도", esc(st.trim || "—"));
    }
    h += '</div>';

    if (st.comment) h += '<div class="comment">' + esc(st.comment) + '</div>';

    var issues = st.issues || [];
    h += '<div class="sec"><h2>최근 이슈 · 체크포인트</h2></div>';
    if (!issues.length) h += '<div class="empty">등록된 이슈가 없어요.</div>';
    issues.forEach(function (is) {
      h += '<div class="issue"><div class="top"><span class="itag ' + esc(is.tag || "") + '">' + esc(is.tag || "") + '</span><span class="dt">' + esc(is.date || "") + '</span></div><div class="tx">' + esc(is.text) + '</div></div>';
    });

    h += '<div class="foot">투자 자문 아님 · 분석 참고 · 최종 결정은 정훈.</div>';

    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }
  function box(k, v) { return '<div class="b"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>'; }
  function boxFull(k, v) { return '<div class="b full"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>'; }

  if (!D) { root.innerHTML = '<div class="empty">데이터(data.js)가 없어요. build_app_data.py를 먼저 실행하세요.</div>'; return; }
  route();
})();
