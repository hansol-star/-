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
  // 0~100 정량 스코어 배지 (null=ETF 등 채점 제외 → 표시 안 함). 색: 85+강세·55+중립·그외 약세
  function scoreBadge(s) {
    if (s == null) return "";
    var t = s >= 85 ? "up" : (s >= 55 ? "" : "down");
    return '<span class="score ' + t + '">' + s + '</span>';
  }

  // 인라인 마크다운 (**굵게**, *기울임*, `코드`, [텍스트](링크)) — 입력은 이미 esc된 상태
  function mdInline(s) {
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }

  // 블록 마크다운 → HTML. 헤딩·표(GFM)·리스트·인용·구분선·문단 지원.
  function mdToHtml(md) {
    var lines = String(md || "").replace(/\r\n/g, "\n").split("\n");
    var out = [], i = 0;
    function flushList(buf, ordered) {
      if (!buf.length) return;
      out.push("<" + (ordered ? "ol" : "ul") + ">" + buf.map(function (x) { return "<li>" + mdInline(esc(x)) + "</li>"; }).join("") + "</" + (ordered ? "ol" : "ul") + ">");
    }
    while (i < lines.length) {
      var ln = lines[i];
      var t = ln.trim();
      // 펜스 코드블록 ``` … ``` (STATE SNAPSHOT·핵심 액션 등)
      if (/^```/.test(t)) {
        var cb = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i].trim())) { cb.push(lines[i]); i++; }
        i++; // 닫는 ``` 소비
        out.push('<pre class="md"><code>' + esc(cb.join("\n")) + "</code></pre>");
        continue;
      }
      // 표: |...| 헤더 + |---| 구분 + 본문
      if (t.indexOf("|") === 0 && i + 1 < lines.length && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1].trim())) {
        var rows = [];
        while (i < lines.length && lines[i].trim().indexOf("|") === 0) { rows.push(lines[i].trim()); i++; }
        var sep = rows.splice(1, 1); // 구분선 제거
        var cells = function (r) { return r.replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); }); };
        var html = '<div class="mdtable"><table>';
        html += "<thead><tr>" + cells(rows[0]).map(function (c) { return "<th>" + mdInline(esc(c)) + "</th>"; }).join("") + "</tr></thead><tbody>";
        for (var r = 1; r < rows.length; r++) html += "<tr>" + cells(rows[r]).map(function (c) { return "<td>" + mdInline(esc(c)) + "</td>"; }).join("") + "</tr>";
        html += "</tbody></table></div>";
        out.push(html);
        continue;
      }
      // 헤딩
      var hm = t.match(/^(#{1,6})\s+(.*)$/);
      if (hm) { var lv = hm[1].length; out.push("<h" + lv + ' class="md h' + lv + '">' + mdInline(esc(hm[2])) + "</h" + lv + ">"); i++; continue; }
      // 구분선
      if (/^([-*_])\1{2,}$/.test(t)) { out.push('<hr class="md">'); i++; continue; }
      // 인용 (연속 > 줄을 한 블록으로)
      if (t.indexOf("> ") === 0 || t === ">") {
        var qb = [];
        while (i < lines.length && (lines[i].trim().indexOf("> ") === 0 || lines[i].trim() === ">")) {
          qb.push(mdInline(esc(lines[i].trim().replace(/^>\s?/, "")))); i++;
        }
        out.push("<blockquote>" + qb.join("<br>") + "</blockquote>"); continue;
      }
      // 순서 없는 리스트
      if (/^[-*+]\s+/.test(t)) {
        var ub = [];
        while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) { ub.push(lines[i].trim().replace(/^[-*+]\s+/, "")); i++; }
        flushList(ub, false); continue;
      }
      // 순서 있는 리스트
      if (/^\d+[.)]\s+/.test(t)) {
        var ob = [];
        while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) { ob.push(lines[i].trim().replace(/^\d+[.)]\s+/, "")); i++; }
        flushList(ob, true); continue;
      }
      // 빈 줄
      if (!t) { i++; continue; }
      // 문단 (연속 텍스트 줄 묶기)
      var pb = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|\|)/.test(lines[i].trim()) && !/^([-*_])\1{2,}$/.test(lines[i].trim())) {
        pb.push(lines[i].trim()); i++;
      }
      if (pb.length) out.push("<p>" + mdInline(esc(pb.join(" "))) + "</p>");
    }
    return out.join("\n");
  }

  // ── routing (hash) ──
  function route() {
    var h = location.hash.replace(/^#/, "");
    if (h.indexOf("stock/") === 0) renderDetail(decodeURIComponent(h.slice(6)));
    else if (h === "plan") renderPlan();
    else if (h.indexOf("report/") === 0) renderReport(decodeURIComponent(h.slice(7)));
    else if (h === "reports") renderReports();
    else if (h.indexOf("video/") === 0) renderVideo(decodeURIComponent(h.slice(6)));
    else if (h === "archive") renderArchive();
    else if (h === "hunter") renderHunter();
    else if (h === "pmview") renderPMView();
    else if (h === "decisions") renderDecisions();
    else renderHome();
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", route);

  function find(tk) {
    var all = (D.holdings || []).concat(D.watchlist || []);
    for (var i = 0; i < all.length; i++) if (all[i].ticker === tk) return all[i];
    return null;
  }

  // ── SVG 차트 ──
  function lineChart(hist, color, cur) {
    var c = (hist && hist.closes) || [], dts = (hist && hist.dates) || [];
    if (c.length < 2) return '<div class="empty sm">시계열 데이터 없음</div>';
    var W = 320, H = 110, P = 8, BL = 22;
    var min = Math.min.apply(null, c), max = Math.max.apply(null, c);
    var rng = (max - min) || 1, n = c.length;
    function X(i) { return P + i * (W - 2 * P) / (n - 1); }
    function Y(v) { return P + (1 - (v - min) / rng) * (H - P - BL); }
    var pts = c.map(function (v, i) { return X(i).toFixed(1) + "," + Y(v).toFixed(1); }).join(" ");
    var area = "M" + X(0).toFixed(1) + "," + (H - BL) + " L" + pts.split(" ").join(" L") + " L" + X(n - 1).toFixed(1) + "," + (H - BL) + " Z";
    var last = c[n - 1], first = c[0], chg = ((last - first) / first * 100);
    var gid = "g" + color.replace("#", "");
    var fmt = function (v) { return cur === "USD" ? v.toFixed(2) : num(Math.round(v)); };
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" preserveAspectRatio="none" style="display:block">';
    s += '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + color + '" stop-opacity="0.28"/><stop offset="1" stop-color="' + color + '" stop-opacity="0"/></linearGradient></defs>';
    s += '<path d="' + area + '" fill="url(#' + gid + ')"/>';
    s += '<polyline points="' + pts + '" fill="none" stroke="' + color + '" stroke-width="2" stroke-linejoin="round"/>';
    s += '<circle cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(last).toFixed(1) + '" r="3" fill="' + color + '"/>';
    s += '<text x="' + P + '" y="' + (H - 6) + '" fill="#5f6b87" font-size="9">' + esc(dts[0]) + '</text>';
    s += '<text x="' + (W - P) + '" y="' + (H - 6) + '" fill="#5f6b87" font-size="9" text-anchor="end">' + esc(dts[n - 1]) + '</text>';
    s += '<text x="' + P + '" y="' + (P + 8) + '" fill="#5f6b87" font-size="9">고 ' + fmt(max) + '</text>';
    s += '</svg>';
    var head = '<div class="row between" style="margin-bottom:4px"><span class="bold">' + fmt(last) + '</span><span class="sm ' + cls(chg) + '">' + (chg >= 0 ? "+" : "") + chg.toFixed(2) + '% <span class="mut">(' + n + '일)</span></span></div>';
    return head + s;
  }

  function flowChart(flows) {
    var ser = (flows && flows.series) || [];
    if (!ser.length) return '<div class="empty sm">수급 데이터 없음</div>';
    var W = 320, H = 150, BL = 22, TOP = 8;
    var vals = [];
    ser.forEach(function (d) { ["foreign", "inst", "indiv"].forEach(function (k) { if (d[k] != null) vals.push(Math.abs(d[k])); }); });
    var maxA = Math.max.apply(null, vals) || 1;
    var zoneH = (H - BL - TOP) / 2, zeroY = TOP + zoneH;
    var gw = W / ser.length, bw = gw * 0.22;
    var colors = { foreign: "#ffcc4d", inst: "#34d399", indiv: "#6d8bff" };
    var keys = ["foreign", "inst", "indiv"];
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="display:block">';
    s += '<line x1="0" y1="' + zeroY + '" x2="' + W + '" y2="' + zeroY + '" stroke="#27304a" stroke-width="1"/>';
    ser.forEach(function (d, gi) {
      var cx = gi * gw + gw / 2;
      keys.forEach(function (k, ki) {
        var v = d[k];
        var bx = cx + (ki - 1) * (bw + 1.5) - bw / 2;
        if (v == null) { s += '<text x="' + (bx + bw / 2).toFixed(1) + '" y="' + (zeroY - 1) + '" fill="#5f6b87" font-size="7" text-anchor="middle">·</text>'; return; }
        var hh = Math.abs(v) / maxA * zoneH;
        var y = v >= 0 ? zeroY - hh : zeroY;
        s += '<rect x="' + bx.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(hh, 0.5).toFixed(1) + '" fill="' + colors[k] + '" rx="1"/>';
      });
      s += '<text x="' + cx.toFixed(1) + '" y="' + (H - 8) + '" fill="#5f6b87" font-size="8" text-anchor="middle">' + esc(d.date.slice(5)) + '</text>';
    });
    s += '</svg>';
    var legend = '<div class="row wrap" style="gap:10px;margin-top:6px;font-size:11px">'
      + '<span><span class="lg" style="background:#ffcc4d"></span>외국인</span>'
      + '<span><span class="lg" style="background:#34d399"></span>기관</span>'
      + '<span><span class="lg" style="background:#6d8bff"></span>개인</span>'
      + '<span class="mut" style="margin-left:auto">↑순매수 ↓순매도 (억원)</span></div>';
    return s + legend;
  }

  // ── HOME ──
  function renderHome() {
    var t = D.totals || {}, s = D.safety || {};
    var pinTxt = { ok: "정상 — 안전핀 이격 충분", watch: "주의 — 2차 트랜치 구간(8,000 부근)", freeze: "⚠ 동결 — 안전핀 하회, 잔여 트랜치 전면 동결", unknown: "코스피 시세 미확인" };
    var firedAlerts = (D.alerts || []).filter(function (a) { return a.fired; });
    var events = (D.alerts || []).filter(function (a) { return a.cond === "event" || a.cond === "signal"; });
    var kr = (D.holdings || []).filter(function (h) { return h.region === "kr"; });
    var us = (D.holdings || []).filter(function (h) { return h.region === "us"; });

    var h = "";
    h += '<header><div class="title">정훈 증권 · 포트폴리오</div>';
    h += '<div class="sub">' + esc(D.as_of || "") + ' · 갱신 ' + esc(D.generated_at || "") + (D.offline ? " · 오프라인" : "") + '</div></header>';

    h += '<div class="hero"><div class="lbl">총 자산</div>';
    h += '<div class="big">' + won(t.assets_krw) + '</div>';
    h += '<div class="row" style="gap:12px"><span class="' + cls(t.day_change_krw) + ' bold">당일 ' + (t.day_change_krw >= 0 ? "+" : "") + num(t.day_change_krw) + '원 (' + pct(t.day_change_pct) + ')</span></div>';
    h += '<div class="chips">';
    h += '<div class="chip"><div class="mut">평가손익</div><div class="v ' + cls(t.total_pnl_krw) + '">' + (t.total_pnl_krw >= 0 ? "+" : "") + num(t.total_pnl_krw) + '원<br><span class="sm">' + pct(t.total_pnl_pct) + '</span></div></div>';
    h += '<div class="chip"><div class="mut">현금</div><div class="v">' + num(t.cash_krw) + '원</div></div>';
    h += '<div class="chip"><div class="mut">환율</div><div class="v">₩' + num(D.fx && D.fx.usdkrw) + '</div></div>';
    h += '</div></div>';

    var GH = "https://github.com/hansol-star/-/actions/workflows/";
    h += '<div class="nav"><a class="navbtn" href="#plan">🗓️ 계획·할일</a><a class="navbtn" href="#reports">📄 일일 보고서</a><a class="navbtn" href="#hunter">🎬 경제사냥꾼</a><a class="navbtn" href="#pmview">💭 PM 사견</a></div>';
    var decN = (D.decisions && D.decisions.open_count) || 0;
    h += '<div class="nav"><a class="navbtn" href="#decisions">🧭 결정·전략 아젠다' + (decN ? ' (' + decN + ')' : '') + '</a></div>';

    // 오늘 할일 요약 + 시간축 전망 (자세히는 #plan)
    h += planSummary();
    h += '<div class="nav">'
      + '<a class="navbtn run" href="' + GH + 'refresh-prices.yml" target="_blank" rel="noopener">🔄 시세 새로고침</a>'
      + '<a class="navbtn run" href="' + GH + 'daily-report.yml" target="_blank" rel="noopener">🧠 전체 분석</a>'
      + '</div>';
    h += '<div class="runhint">버튼 → GitHub 열림 → <b>Run workflow</b> 탭하면 실행. 시세=무료 · 전체 분석=API 키 필요.</div>';

    h += '<div class="pin ' + (s.status || "unknown") + '"><div><div class="xs">코스피 매수 안전핀 ' + num(s.pin) + '</div><div>' + esc(pinTxt[s.status] || "") + '</div></div>';
    h += '<div class="pv">' + num(s.price) + ' <span class="sm ' + cls(s.change_pct) + '">' + pct(s.change_pct) + '</span></div></div>';

    if (firedAlerts.length) {
      h += '<div class="sec"><h2>🔔 발동 트리거 (' + firedAlerts.length + ')</h2></div>';
      firedAlerts.forEach(function (a) {
        h += '<div class="alert fired"><div class="row between"><span class="aid">' + esc(a.id) + '</span><span class="badge">발동</span></div><div class="act">' + esc(a.action) + '</div></div>';
      });
    }

    // 차트
    h += '<div class="sec"><h2>📈 차트</h2></div>';
    h += '<div class="card"><div class="ctitle">코스피 <span class="mut sm">(1개월)</span></div>' + lineChart(D.kospi_history, "#34d399", "KRW") + '</div>';
    h += '<div class="card"><div class="ctitle">USD/KRW 환율 <span class="mut sm">(1개월)</span></div>' + lineChart(D.fx_history, "#60a5fa", "KRW") + '</div>';
    h += '<div class="card"><div class="ctitle">코스피 투자자별 순매수 <span class="mut sm">(외인·기관·개인)</span></div>' + flowChart(D.flows) + '</div>';

    // 지수
    h += '<div class="sec"><h2>지수</h2></div><div class="row wrap" style="gap:8px">';
    (D.indices || []).forEach(function (i) {
      h += '<div class="chip" style="flex:1;min-width:30%"><div class="mut sm">' + esc(i.label) + '</div><div class="v">' + num(i.price) + '<br><span class="sm ' + cls(i.change_pct) + '">' + pct(i.change_pct) + '</span></div></div>';
    });
    h += '</div>';

    // 보유 — 국내 / 해외 분리
    h += '<div class="sec"><h2>🇰🇷 국내 보유 ' + kr.length + '</h2></div><div class="list">';
    kr.forEach(function (st) { h += itemRow(st, true); });
    h += '</div>';
    h += '<div class="sec"><h2>🇺🇸 해외 보유 ' + us.length + '</h2></div><div class="list">';
    us.forEach(function (st) { h += itemRow(st, true); });
    h += '</div>';

    if ((D.watchlist || []).length) {
      h += '<div class="sec"><h2>👀 워치리스트</h2></div><div class="list">';
      (D.watchlist || []).forEach(function (st) { h += itemRow(st, false); });
      h += '</div>';
    }

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
    line += '<div class="row" style="gap:8px;margin-top:1px"><span class="stars">' + stars(st.stars) + '</span>' + scoreBadge(st.score) + '<span class="tk">' + esc(st.ticker) + '</span></div></div>';
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
    h += '<div class="dhero"><div class="row between"><div class="nm">' + esc(st.label) + '</div><div class="row" style="gap:6px;align-items:center"><div class="stars" style="font-size:14px">' + stars(st.stars) + '</div>' + scoreBadge(st.score) + '</div></div>';
    h += '<div class="tk mut sm">' + esc(st.ticker) + '</div>';
    h += '<div class="dprice">' + price(st.price, st.currency) + ' <span class="' + cls(st.change_pct) + '" style="font-size:16px">' + pct(st.change_pct) + '</span></div></div>';

    h += '<div class="kv">';
    if (isHolding) {
      h += box("평가손익", '<span class="' + cls(st.pnl_krw) + '">' + (st.pnl_krw >= 0 ? "+" : "") + num(st.pnl_krw) + '원 (' + pct(st.pnl_pct) + ')</span>');
      h += box("평가금액", num(st.value_krw) + '원');
      h += box("보유수량", num(st.shares) + '주');
      h += box("평단", price(st.cost, st.currency));
    }
    if (st.score != null) h += box("스코어(0~100)", scoreBadge(st.score));
    h += box("목표가", esc(st.target || "—"));
    if (isHolding) {
      h += box("매수존", esc(st.buy_zone || "—"));
      h += boxFull("트림/매도", esc(st.trim || "—"));
    }
    h += '</div>';

    if (st.comment) h += '<div class="comment">' + esc(st.comment) + '</div>';

    // 시간축 가격 예상 (주/월 레인지)
    if (st.forecast) {
      h += '<div class="sec"><h2>🔮 가격 예상 (시간축 레인지)</h2></div>';
      h += forecastRow("이번주", st.forecast.week, st.price, st.currency);
      h += forecastRow("이번달", st.forecast.month, st.price, st.currency);
      h += '<div class="runhint" style="margin:2px 0 0">레인지는 단기 예측치 — 목표가/매수존과 별개. 분석 참고.</div>';
    }

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

  // ── 시간축 전망 / 할일 / 매수추적 공용 ──
  function dirArrow(d) {
    if (d === "↑") return '<span class="up bold">↑ 상방</span>';
    if (d === "↓") return '<span class="down bold">↓ 하방</span>';
    return '<span class="mut bold">→ 중립</span>';
  }
  // 종목 가격 예상 한 줄(레인지 바 + 현재가 마커)
  function forecastRow(label, f, cpx, cur) {
    if (!f) return "";
    var lo = f.low, hi = f.high, rng = (hi - lo) || 1;
    var posv = (cpx == null) ? null : Math.max(0, Math.min(100, (cpx - lo) / rng * 100));
    var s = '<div class="fc">';
    s += '<div class="row between"><span class="fc-lb">' + esc(label) + '</span>' + dirArrow(f.dir) + '</div>';
    s += '<div class="fc-rng">' + price(lo, cur) + ' <span class="mut">~</span> ' + price(hi, cur) + '</div>';
    s += '<div class="fc-bar">';
    if (posv != null) s += '<div class="fc-now" style="left:' + posv.toFixed(0) + '%"></div>';
    s += '</div>';
    if (cpx != null) s += '<div class="fc-cap"><span class="mut">현재 ' + price(cpx, cur) + '</span></div>';
    if (f.note) s += '<div class="fc-note">' + esc(f.note) + '</div>';
    s += '</div>';
    return s;
  }

  // 홈 요약: 오늘 할일 진행 + 월요일/이번주 전망 1~2줄
  // 할일 체크 — 이 폰 임시저장(localStorage). git(채팅)이 정본: 정본 done=true는 고정,
  // 아직 정본에 없는 할일만 앱에서 탭 토글. 정본이 항상 우선.
  var LS_TASK = "jh_task_done";
  function lsTasks() { try { return JSON.parse((window.localStorage && localStorage.getItem(LS_TASK)) || "{}"); } catch (e) { return {}; } }
  function lsSetTask(id, v) { try { var m = lsTasks(); if (v) m[id] = 1; else delete m[id]; localStorage.setItem(LS_TASK, JSON.stringify(m)); } catch (e) {} }
  function taskDone(t) { return !!(t.done || lsTasks()[t.id]); }

  function planSummary() {
    var today = (D.tasks && D.tasks.today) || [];
    var done = today.filter(taskDone).length;
    var ol = D.outlook || [];
    var key = ol.find(function (o) { return /월요일|내일|이번주/.test(o.horizon); }) || ol[1] || ol[0];
    var s = '<a class="plansum" href="#plan">';
    s += '<div class="row between"><span class="ps-t">🗓️ 오늘 할일</span><span class="ps-n">' + done + ' / ' + today.length + ' 완료</span></div>';
    if (key) s += '<div class="ps-ol"><span class="otag">' + esc(key.tag || "") + '</span> <b>' + esc(key.horizon) + '</b> · ' + esc(key.text) + '</div>';
    s += '<div class="ps-more">계획·할일·매수추적 전체 보기 ›</div></a>';
    return s;
  }

  // 할일 한 묶음. 정본 done=true=잠금(✅고정) · 그 외=탭 토글 가능
  function taskGroup(title, arr) {
    arr = arr || [];
    var done = arr.filter(taskDone).length;
    var s = '<div class="sec"><h2>' + esc(title) + ' <span class="mut">(' + done + '/' + arr.length + ')</span></h2></div>';
    if (!arr.length) { s += '<div class="empty sm">등록된 할일이 없어요.</div>'; return s; }
    s += '<div class="tlist">';
    arr.forEach(function (t) {
      var d = taskDone(t), locked = !!t.done;
      s += '<div class="trow' + (d ? " done" : "") + (locked ? " lock" : " tog") + '" data-id="' + esc(t.id) + '">'
        + '<span class="tck">' + (d ? "✅" : "⬜") + '</span>'
        + '<span class="ttx">' + mdInline(esc(t.text)) + '</span>'
        + (locked ? '<span class="tlock">정본</span>' : '') + '</div>';
    });
    s += '</div>';
    return s;
  }

  // 매수추적 행
  function orderRow(o) {
    var stMap = { "계획": "plan", "예약": "wait", "체결": "fill", "취소": "cxl" };
    var sc = stMap[o.status] || "plan";
    var qty = (o.shares != null ? num(o.shares) + "주" : "");
    var px = (o.price != null) ? price(o.price, /\.K[SQ]$/.test(o.ticker || "") ? "KRW" : "USD") : "";
    var meta = [px, qty].filter(Boolean).join(" · ");
    var s = '<div class="ord ' + sc + '">';
    s += '<div class="row between"><span class="o-nm">' + esc(o.action || "") + ' ' + esc(o.label || "") + '</span><span class="o-st ' + sc + '">' + esc(o.status || "") + '</span></div>';
    s += '<div class="o-meta">' + esc(meta) + (o.date ? ' <span class="mut">· ' + esc(o.date) + '</span>' : '') + '</div>';
    if (o.note) s += '<div class="o-note">' + esc(o.note) + '</div>';
    s += '</div>';
    return s;
  }

  // ── PLAN (계획·할일·매수추적·시간축 전망) ──
  function renderPlan() {
    var h = '<header><a class="back" href="#">← 포트폴리오</a><div class="title" style="margin-top:6px">🗓️ 계획 · 할일 · 매수추적</div>';
    h += '<div class="sub">갱신 ' + esc(D.tasks_updated || "") + ' · 할일은 탭으로 체크(이 폰 임시) · 매수기록·영구반영은 채팅 “~했어/샀어”</div></header>';

    // 시간축 장 전망
    h += '<div class="sec"><h2>📅 장 전망 (오늘·내일·이번주·이번달)</h2></div>';
    (D.outlook || []).forEach(function (o) {
      h += '<div class="card ol"><div class="row between" style="margin-bottom:5px"><span class="ol-h"><span class="otag">' + esc(o.tag || "") + '</span> ' + esc(o.horizon) + '</span>' + dirArrow(o.dir) + '</div><div class="ol-tx">' + esc(o.text) + '</div></div>';
    });

    // 지수 예상 레인지
    if ((D.index_forecast || []).length) {
      h += '<div class="sec"><h2>📈 지수 예상 레인지</h2></div>';
      (D.index_forecast || []).forEach(function (f) {
        var cur = f.name === "코스피" ? "KRW" : "USD";
        var fmt = function (v) { return cur === "KRW" ? num(v) : num(v); };
        h += '<div class="card"><div class="row between"><span class="bold">' + esc(f.name) + '</span>' + dirArrow(f.dir) + '</div>';
        h += '<div class="fc-rng" style="margin:4px 0">' + fmt(f.low) + ' <span class="mut">~ (기준 ' + fmt(f.base) + ') ~</span> ' + fmt(f.high) + '</div>';
        h += '<div class="fc-bar">';
        var rng = (f.high - f.low) || 1, pos = Math.max(0, Math.min(100, (f.ref - f.low) / rng * 100));
        if (f.ref != null) h += '<div class="fc-now" style="left:' + pos.toFixed(0) + '%"></div>';
        h += '</div><div class="fc-cap"><span class="mut">현재 ' + fmt(f.ref) + '</span></div>';
        if (f.note) h += '<div class="fc-note">' + esc(f.note) + '</div></div>';
        else h += '</div>';
      });
    }

    // 매수추적
    h += '<div class="sec"><h2>🛒 매수 추적 (계획·예약·체결)</h2></div>';
    var orders = D.orders || [];
    if (!orders.length) h += '<div class="empty sm">기록된 주문이 없어요. “NAVER 1주 샀어” 라고 하면 추가돼요.</div>';
    orders.forEach(function (o) { h += orderRow(o); });

    // 할일
    var tasks = D.tasks || {};
    h += taskGroup("✅ 오늘 할일", tasks.today);
    h += taskGroup("📌 이번주 할일", tasks.week);
    h += taskGroup("🗓️ 이번달 할일", tasks.month);

    h += '<div class="foot">앱 체크 = 이 폰 임시저장 · 정본 = git(채팅으로 “했어” 하면 영구반영·다른 기기에도).<br>투자 자문 아님 · 분석 참고 · 최종 결정은 정훈.</div>';

    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));

    // 할일 탭 체크 (정본 잠금 제외) — localStorage 토글 후 스크롤 유지 재렌더
    Array.prototype.forEach.call(root.querySelectorAll(".trow.tog"), function (rowEl) {
      rowEl.addEventListener("click", function () {
        var id = rowEl.getAttribute("data-id");
        lsSetTask(id, !lsTasks()[id]);
        var y = window.scrollY || 0;
        renderPlan();
        window.scrollTo(0, y);
      });
    });
  }

  // ── HUNTER (경제사냥꾼) ──
  function renderHunter() {
    var hu = D.hunter || {};
    var h = '<header><a class="back" href="#">← 포트폴리오</a><div class="title" style="margin-top:6px">🎬 경제사냥꾼</div>';
    h += '<div class="sub">' + esc(hu.source || "") + ' · 갱신 ' + esc(hu.updated || "") + '</div></header>';

    if (!hu.latest_videos) { h += '<div class="empty">경제사냥꾼 데이터가 없어요.</div>'; root.innerHTML = ""; root.appendChild(el('<div>' + h + '</div>')); return; }

    if (hu.headline) h += '<div class="hl">💡 ' + esc(hu.headline) + '</div>';
    if (hu.channel_note) h += '<div class="comment sm">' + esc(hu.channel_note) + '</div>';

    // 채널 정확도 스코어카드 (전체 아카이브 기준) + 전체 아카이브 진입
    var sc = hu.scorecard;
    var arch = D.hunter_archive || [];
    if (sc && sc.total) {
      var bk = sc.buckets || {};
      h += '<div class="scard"><div class="row between"><span class="sck">📊 채널 정확도 <span class="mut sm">(분석 ' + sc.total + '건)</span></span><span class="scacc">' + sc.accuracy_pct + '%</span></div>';
      h += '<div class="scbar">';
      var segs = [["정확", "#34d399", bk["정확"]], ["근사", "#7dd3fc", bk["근사"]], ["시점", "#9db4ff", bk["시점"]], ["미확인", "#ffd87a", bk["미확인"]], ["정정", "#fb6a6a", bk["정정"]], ["과장", "#f0883e", bk["과장"]]];
      segs.forEach(function (s) { if (s[2]) h += '<span class="scseg" style="flex:' + s[2] + ';background:' + s[1] + '" title="' + s[0] + ' ' + s[2] + '"></span>'; });
      h += '</div><div class="row wrap sclegend">';
      segs.forEach(function (s) { if (s[2]) h += '<span><span class="lg" style="background:' + s[1] + '"></span>' + s[0] + ' ' + s[2] + '</span>'; });
      h += '</div><div class="mut xs" style="margin-top:6px">방향성 채택 · 숫자는 교차검증 전제. 정확+근사 = 방향 적중.</div></div>';
    }
    if (arch.length) h += '<div class="nav"><a class="navbtn" href="#archive">🗂️ 전체 영상 아카이브 (' + arch.length + ')</a></div>';

    var vids = hu.latest_videos || [];
    h += '<div class="sec"><h2>최신 영상 분석 (' + vids.length + ') · 눌러서 자세히</h2></div>';
    vids.forEach(function (v, idx) {
      var vid = v.id || String(idx);
      h += '<div class="vid tappable" onclick="location.hash=\'video/' + encodeURIComponent(vid) + '\'">';
      h += '<div class="top"><span class="itag ' + esc(v.tag || "") + '">' + esc(v.tag || "") + '</span><span class="dt">' + esc(v.date || "") + '</span><span class="vmore">자세히 ›</span></div>';
      h += '<div class="vtitle">' + esc(v.title) + '</div>';
      h += '<div class="tx clamp">' + esc(v.summary || v.note || "") + '</div>';
      if (v.tickers && v.tickers.length) {
        h += '<div class="row wrap" style="gap:5px;margin-top:7px">';
        v.tickers.forEach(function (tk) {
          var st = find(tk); var nm = st ? st.label : tk;
          h += '<span class="tchip">' + esc(nm) + '</span>';
        });
        h += '</div>';
      }
      h += '</div>';
    });

    var tr = hu.track_record || [];
    if (tr.length) {
      h += '<div class="sec"><h2>📊 채널 트랙레코드 (정확도)</h2></div>';
      tr.forEach(function (r) {
        h += '<div class="trk"><div class="row between"><span class="dt">' + esc(r.date) + '</span><span class="itag ' + esc(r.verdict || "") + '">' + esc(r.verdict || "") + '</span></div>';
        h += '<div class="tx sm"><b>주장:</b> ' + esc(r.claim) + '</div>';
        h += '<div class="tx sm mut"><b>실제:</b> ' + esc(r.actual) + '</div></div>';
      });
    }

    var th = hu.themes || [];
    if (th.length) {
      h += '<div class="sec"><h2>🔭 반복 논지 · 테마</h2></div><div class="list">';
      th.forEach(function (x) { h += '<div class="theme">' + esc(x) + '</div>'; });
      h += '</div>';
    }

    h += '<div class="foot">방향성은 채택, 수치는 교차검증 · 투자 자문 아님.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  // ── PM 사견 (클로드의 객관적 독립 의견) ──
  function renderPMView() {
    var pv = D.pm_view || {};
    var items = pv.items || [];
    var h = '<header><a class="back" href="#">← 포트폴리오</a><div class="title" style="margin-top:6px">💭 PM 사견</div>';
    h += '<div class="sub">클로드의 객관적 시선 · 갱신 ' + esc(pv.updated || "") + '</div></header>';

    if (pv.headline) h += '<div class="hl">💡 ' + esc(pv.headline) + '</div>';
    if (pv.philosophy) h += '<div class="comment sm">' + esc(pv.philosophy) + '</div>';

    if (!items.length) {
      h += '<div class="empty">아직 등록된 사견이 없어요.</div>';
      root.innerHTML = ""; root.appendChild(el('<div>' + h + '</div>')); return;
    }

    h += '<div class="sec"><h2>독립 의견 (' + items.length + ')</h2></div>';
    items.forEach(function (it) {
      var stance = it.stance || "";
      var sc = stance === "강세" ? "up" : (stance === "신중" ? "down" : "");
      h += '<div class="pmcard">';
      h += '<div class="row wrap" style="gap:6px;align-items:center">';
      if (stance) h += '<span class="pmtag ' + sc + '">' + esc(stance) + '</span>';
      if (it.align) h += '<span class="pmtag mut">룰 ' + esc(it.align) + '</span>';
      if (it.conviction) h += '<span class="mut xs">확신 ' + esc(it.conviction) + '</span>';
      h += '<span class="mut xs" style="margin-left:auto">' + esc(it.topic || "") + ' · ' + esc(it.date || "") + '</span>';
      h += '</div>';
      h += '<div class="pmtitle">' + esc(it.title || "") + '</div>';
      h += '<div class="md-body">' + mdToHtml(it.view || "") + '</div>';
      if (it.rule_note) h += '<div class="pmrule"><b>룰 vs 내 시선 — </b>' + esc(it.rule_note) + '</div>';
      h += '</div>';
    });

    h += '<div class="foot">정훈 룰을 잠시 빼고 본 객관적 보조 시선 · 포트 운용은 룰이 우선 · 투자 자문 아님.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  // ── DECISIONS (결정 메모리 · 전략 아젠다) ──
  function decCard(it, open) {
    var h = '<div class="pmcard">';
    h += '<div class="row wrap" style="gap:6px;align-items:center">';
    h += '<span class="pmtag ' + (open ? "up" : "mut") + '">' + (open ? "🟢 열림" : "⚪ 결정") + '</span>';
    h += '<span class="mut xs" style="margin-left:auto">' + esc(it.date || "") + '</span></div>';
    h += '<div class="pmtitle">' + esc(it.topic || "") + '</div>';
    if (it.decision) h += '<div class="md-body sm">' + esc(it.decision) + '</div>';
    if (it.rationale) h += '<div class="comment sm"><b>근거 — </b>' + esc(it.rationale) + '</div>';
    if (it.rejected) h += '<div class="comment sm mut"><b>기각/대안 — </b>' + esc(it.rejected) + '</div>';
    if (it.tags && it.tags.length) {
      h += '<div class="row wrap" style="gap:5px;margin-top:6px">';
      it.tags.forEach(function (t) { h += '<span class="tag">' + esc(t) + '</span>'; });
      h += '</div>';
    }
    if (it.refs) h += '<div class="mut xs" style="margin-top:5px">' + esc(it.refs) + '</div>';
    h += '</div>';
    return h;
  }
  function renderDecisions() {
    var d = D.decisions || {}, op = d.open || [], cl = d.closed || [];
    var h = '<header><a class="back" href="#">← 포트폴리오</a><div class="title" style="margin-top:6px">🧭 결정·전략 아젠다</div>';
    h += '<div class="sub">왜 그렇게 결정했나 + 큰그림 열린 질문 · master §9/§10 정본의 폰 뷰</div></header>';
    if (!op.length && !cl.length) {
      h += '<div class="empty">결정 메모리가 없어요. decisions.jsonl 생성 후 build_app_data.py 실행.</div>';
      root.innerHTML = ""; root.appendChild(el('<div>' + h + '</div>')); return;
    }
    if (op.length) {
      h += '<div class="sec"><h2>열린 전략 아젠다 (' + op.length + ')</h2></div>';
      h += '<div class="comment sm">매 보고서마다 상태를 재검토·갱신하는 큰그림 열린 질문.</div>';
      op.forEach(function (it) { h += decCard(it, true); });
    }
    if (cl.length) {
      h += '<div class="sec"><h2>최근 결정 (' + cl.length + ')</h2></div>';
      cl.forEach(function (it) { h += decCard(it, false); });
    }
    h += '<div class="foot">결정 정본은 docs/master.md §9·§10 + data/app/decisions.jsonl · 세션이 바뀌어도 이어지는 기억.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  // ── REPORTS (일일 보고서 목록) ──
  var reportFilter = "전체";
  function renderReports() {
    var all = D.reports || [];
    var h = '<header><a class="back" href="#">← 포트폴리오</a><div class="title" style="margin-top:6px">📄 일일 보고서</div>';
    h += '<div class="sub">' + all.length + '개 · 최신순 · 눌러서 전문 보기</div></header>';
    if (!all.length) { h += '<div class="empty">보고서가 없어요. build_app_data.py를 실행하세요.</div>'; root.innerHTML = ""; root.appendChild(el('<div>' + h + '</div>')); return; }

    // 종류 필터 칩
    var kinds = ["전체"];
    all.forEach(function (r) { if (kinds.indexOf(r.kind) === -1) kinds.push(r.kind); });
    h += '<div class="filters">';
    kinds.forEach(function (k) {
      var n = k === "전체" ? all.length : all.filter(function (r) { return r.kind === k; }).length;
      h += '<button class="fchip' + (k === reportFilter ? " on" : "") + '" data-k="' + esc(k) + '">' + esc(k) + ' ' + n + '</button>';
    });
    h += '</div>';

    var reps = reportFilter === "전체" ? all : all.filter(function (r) { return r.kind === reportFilter; });

    // 날짜별 그룹
    var lastDate = null;
    h += '<div class="list">';
    reps.forEach(function (r) {
      if (r.date && r.date !== lastDate) { h += '<div class="rdate">' + esc(r.date) + '</div>'; lastDate = r.date; }
      h += '<div class="item rep" onclick="location.hash=\'report/' + encodeURIComponent(r.id) + '\'">';
      h += '<div class="flex1"><div class="row" style="gap:6px"><span class="tag">' + esc(r.kind || "") + '</span>';
      if (r.version != null) h += '<span class="tag vtag">v' + esc(r.version) + '</span>';
      h += '</div><div class="nm" style="margin-top:5px">' + esc(r.title) + '</div>';
      if (r.preview) h += '<div class="rprev">' + esc(r.preview) + '</div>';
      h += '</div><span class="chev">›</span></div>';
    });
    h += '</div>';
    h += '<div class="foot">보고서는 docs/reports/ 의 원문을 그대로 표시 · 매 루틴 실행 시 자동 갱신.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
    Array.prototype.forEach.call(root.querySelectorAll(".fchip"), function (b) {
      b.addEventListener("click", function () { reportFilter = b.getAttribute("data-k"); renderReports(); window.scrollTo(0, 0); });
    });
  }

  // ── REPORT (보고서 전문) ──
  function renderReport(id) {
    var reps = D.reports || [];
    var r = null;
    for (var i = 0; i < reps.length; i++) if (reps[i].id === id) { r = reps[i]; break; }
    if (!r) { root.innerHTML = '<header><a class="back" href="#reports">← 보고서 목록</a></header><div class="empty">보고서를 찾을 수 없어요.</div>'; return; }

    var h = '<header><a class="back" href="#reports">← 보고서 목록</a></header>';
    h += '<div class="rphead"><div class="row" style="gap:6px"><span class="tag">' + esc(r.kind || "") + '</span>';
    if (r.version != null) h += '<span class="tag vtag">v' + esc(r.version) + '</span>';
    if (r.date) h += '<span class="dt">' + esc(r.date) + '</span>';
    h += '</div><div class="rptitle">' + esc(r.title) + '</div><div class="rpfile mut sm">' + esc(r.file) + '</div></div>';
    // 본문 첫 H1은 헤더 제목과 중복 → 제거하고 렌더
    var body = String(r.content || "").replace(/^﻿?\s*#\s+.*(\r?\n|$)/, "");
    h += '<div class="md-body">' + mdToHtml(body) + '</div>';
    h += '<div class="foot">투자 자문 아님 · 분석 참고 · 최종 결정은 정훈.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  // ── VIDEO (경제사냥꾼 영상 상세) ──
  function renderVideo(id) {
    var hu = D.hunter || {};
    var vids = hu.latest_videos || [];
    var v = null;
    for (var i = 0; i < vids.length; i++) { if ((vids[i].id || String(i)) === id) { v = vids[i]; break; } }
    if (!v) { root.innerHTML = '<header><a class="back" href="#hunter">← 경제사냥꾼</a></header><div class="empty">영상을 찾을 수 없어요.</div>'; return; }

    var h = '<header><a class="back" href="#hunter">← 경제사냥꾼</a></header>';
    h += '<div class="vhead"><div class="top"><span class="itag ' + esc(v.tag || "") + '">' + esc(v.tag || "") + '</span><span class="dt">' + esc(v.date || "") + '</span></div>';
    h += '<div class="vhtitle">' + esc(v.title) + '</div>';
    if (v.link) h += '<a class="vlink" href="' + esc(v.link) + '" target="_blank" rel="noopener">▶ 영상 보기</a>';
    h += '</div>';

    // 요약
    h += '<div class="sec"><h2>요약</h2></div>';
    h += '<div class="comment">' + esc(v.summary || v.note || "—") + '</div>';

    // 핵심 포인트
    if (v.points && v.points.length) {
      h += '<div class="sec"><h2>핵심 포인트</h2></div><div class="vpoints">';
      v.points.forEach(function (p) { h += '<div class="vpoint">' + esc(p) + '</div>'; });
      h += '</div>';
    }

    // 언급 (서술)
    if (v.mentions) {
      h += '<div class="sec"><h2>언급 내용</h2></div>';
      h += '<div class="comment sm">' + esc(v.mentions) + '</div>';
    }

    // 언급 종목 (칩 → 종목 상세)
    if (v.tickers && v.tickers.length) {
      h += '<div class="sec"><h2>언급 종목</h2></div><div class="row wrap" style="gap:6px">';
      v.tickers.forEach(function (tk) {
        var st = find(tk); var nm = st ? st.label : tk;
        h += '<a class="tchip" href="#stock/' + encodeURIComponent(tk) + '">' + esc(nm) + '</a>';
      });
      h += '</div>';
    }

    // 참고 (출처)
    if (v.references && v.references.length) {
      h += '<div class="sec"><h2>참고 · 출처</h2></div><div class="row wrap" style="gap:6px">';
      v.references.forEach(function (rf) { h += '<span class="refchip">' + esc(rf) + '</span>'; });
      h += '</div>';
    }

    // 주의 · 미확인
    if (v.caveats && v.caveats.length) {
      h += '<div class="sec"><h2>⚠ 주의 · 교차검증</h2></div>';
      v.caveats.forEach(function (c) { h += '<div class="caveat">' + esc(c) + '</div>'; });
    }

    // 관련 트랙레코드 (티커 교차)
    var tset = {};
    (v.tickers || []).forEach(function (tk) { tset[tk] = 1; });
    var related = (hu.track_record || []).filter(function (rec) {
      var c = rec.claim || "";
      return (v.tickers || []).some(function (tk) {
        var st = find(tk); var nm = st ? st.label : "";
        return (nm && c.indexOf(nm) !== -1);
      });
    });
    if (related.length) {
      h += '<div class="sec"><h2>📊 검증 이력 (트랙레코드)</h2></div>';
      related.forEach(function (rec) {
        h += '<div class="trk"><div class="row between"><span class="dt">' + esc(rec.date) + '</span><span class="itag ' + esc(rec.verdict || "") + '">' + esc(rec.verdict || "") + '</span></div>';
        h += '<div class="tx sm"><b>주장:</b> ' + esc(rec.claim) + '</div>';
        h += '<div class="tx sm mut"><b>실제:</b> ' + esc(rec.actual) + '</div></div>';
      });
    }

    h += '<div class="foot">방향성은 채택, 수치는 교차검증 · 투자 자문 아님.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
  }

  // ── ARCHIVE (경제사냥꾼 전체 영상 데이터) ──
  var archFilter = "전체";
  function verdictClass(v) {
    v = v || "";
    if (v.indexOf("정정") >= 0 || v.indexOf("오류") >= 0) return "정정";
    if (v.indexOf("미확인") >= 0) return "미확인";
    if (v.indexOf("과장") >= 0) return "과장";
    return "검증";
  }
  function renderArchive() {
    var all = D.hunter_archive || [];
    var h = '<header><a class="back" href="#hunter">← 경제사냥꾼</a><div class="title" style="margin-top:6px">🗂️ 전체 영상 아카이브</div>';
    h += '<div class="sub">' + all.length + '개 · 첫 영상부터 시계열 · 종목으로 필터</div></header>';
    if (!all.length) { h += '<div class="empty">아카이브 데이터가 없어요.</div>'; root.innerHTML = ""; root.appendChild(el('<div>' + h + '</div>')); return; }

    // 보유/워치 종목으로 필터 칩 구성 (영상이 실제 언급한 것만)
    var tkCount = {};
    all.forEach(function (v) { (v.tickers || []).forEach(function (tk) { tkCount[tk] = (tkCount[tk] || 0) + 1; }); });
    var chips = ["전체"].concat(Object.keys(tkCount).sort(function (a, b) { return tkCount[b] - tkCount[a]; }));
    h += '<div class="filters">';
    chips.forEach(function (k) {
      var label = k === "전체" ? ("전체 " + all.length) : ((function () { var st = find(k); return (st ? st.label : k); })() + " " + tkCount[k]);
      h += '<button class="fchip' + (k === archFilter ? " on" : "") + '" data-k="' + esc(k) + '">' + esc(label) + '</button>';
    });
    h += '</div>';

    var rows = archFilter === "전체" ? all : all.filter(function (v) { return (v.tickers || []).indexOf(archFilter) >= 0; });
    var lastDate = null;
    rows.forEach(function (v) {
      if (v.date !== lastDate) { h += '<div class="rdate">' + esc(v.date) + '</div>'; lastDate = v.date; }
      h += '<div class="avid"><div class="row between" style="gap:8px"><span class="avtitle">' + esc(v.title) + '</span><span class="itag ' + verdictClass(v.verdict) + '">' + esc(v.verdict || "") + '</span></div>';
      if (v.theme) h += '<div class="atheme">' + esc(v.theme) + '</div>';
      h += '<div class="atx">' + esc(v.takeaway || "") + '</div>';
      if (v.tickers && v.tickers.length) {
        h += '<div class="row wrap" style="gap:5px;margin-top:6px">';
        v.tickers.forEach(function (tk) { var st = find(tk); h += '<a class="tchip" href="#stock/' + encodeURIComponent(tk) + '">' + esc(st ? st.label : tk) + '</a>'; });
        h += '</div>';
      }
      h += '</div>';
    });
    h += '<div class="foot">방향성 채택 · 수치는 교차검증 · 투자 자문 아님.</div>';
    root.innerHTML = "";
    root.appendChild(el('<div>' + h + '</div>'));
    Array.prototype.forEach.call(root.querySelectorAll(".fchip"), function (b) {
      b.addEventListener("click", function () { archFilter = b.getAttribute("data-k"); renderArchive(); window.scrollTo(0, 0); });
    });
  }

  if (!D) { root.innerHTML = '<div class="empty">데이터(data.js)가 없어요. build_app_data.py를 먼저 실행하세요.</div>'; return; }
  route();
})();
