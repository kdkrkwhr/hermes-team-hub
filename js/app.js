// app.js — hermes-team-hub 메인 로직 (MOCK-first 버전)
// 정적 Pages에서는 fetch 없이 window.MOCK 데이터 사용. local/app.py가 있으면 실제 fetch.
// 모든 기능: 역할 탭 전환 + 각 역할별 뷰 렌더링 + localStorage CRUD (정적 버전)

(function (global) {
  "use strict";

  var ROLES = [
    { key: "pm",    label: "🧄 PM",    color: "var(--pm)",   view: "view-pm" },
    { key: "dev",   label: "🧅 Dev",   color: "var(--dev)",  view: "view-dev" },
    { key: "infra", label: "🧄 Infra", color: "var(--infra)",view: "view-infra"},
    { key: "qa",    label: "🥗 QA",    color: "var(--qa)",   view: "view-qa" },
    { key: "ops",   label: "🍄 Ops",   color: "var(--ops)",  view: "view-ops" }
  ];

  var NAV_ITEMS = [
    { key: "dashboard", label: "📊 현황", ic: "📊" },
    { key: "pm",        label: "🧄 PM",   ic: "🧄" },
    { key: "dev",       label: "🧅 Dev",  ic: "🧅" },
    { key: "infra",     label: "🧄 Infra",ic: "🧄" },
    { key: "qa",        label: "🥗 QA",   ic: "🥗" },
    { key: "ops",       label: "🍄 Ops",  ic: "🍄" },
    { key: "coral",     label: "📡 무전", ic: "📡" },
    { key: "timeline",  label: "🗓️ 타임라인", ic: "🗓️" }
  ];

  var state = { current: null };

  // ---------- DOM ----------
  function $(sel) { return document.querySelector(sel); }

  // ---------- MOCK-first getJSON ----------
  // window.MOCK이 있으면 그 데이터 사용, 없으면 fetch 시도 (local/app.py)
  async function getJSON(url) {
    // MOCK 키 매핑: /api/foo -> window.MOCK["foo"]
    var key = url.replace(/^\/api\//, "").replace(/\/$/, "");
    if (typeof window.MOCK !== "undefined" && window.MOCK[key] !== undefined) {
      return window.MOCK[key];
    }
    // 폴백: 실제 fetch (local/app.py 실행 시)
    try {
      var resp = await fetch(url);
      if (!resp.ok) return [];
      return await resp.json();
    } catch (e) {
      return [];
    }
  }

  // POST는 정적 Pages에서는 no-op (localStorage에 저장하거나 무시)
  async function postJSON(url, obj) {
    var key = url.replace(/^\/api\//, "").replace(/\/$/, "");
    if (typeof window.MOCK === "undefined") {
      // local/app.py가 있으면 실제 POST
      try {
        await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json; charset=utf-8" },
          body: JSON.stringify(obj)
        });
      } catch (e) {}
      return;
    }
    // 정적 MOCK 모드: localStorage에 저장 (no-op 느낌)
    var storageKey = "hermes-mock-" + key;
    try {
      localStorage.setItem(storageKey, JSON.stringify(obj));
    } catch (e) {}
  }

  // ---------- 네비게이션 셋업 ----------
  function setupNav() {
    var nav = $("#nav");
    if (nav && !nav.querySelector(".navbtn")) {
      nav.innerHTML = "";
      NAV_ITEMS.forEach(function (item) {
        var btn = document.createElement("div");
        btn.className = "navbtn";
        btn.setAttribute("data-role", item.key);
        btn.innerHTML = '<span class="ic">' + item.ic + "</span> " + item.label;
        nav.appendChild(btn);
      });
      if (nav.children[0]) nav.children[0].classList.add("active");
    }
    document.querySelectorAll(".navbtn").forEach(function (btn) {
      btn.addEventListener("click", function () { switchTo(btn.dataset.role); });
    });
  }

  function switchTo(role) {
    state.current = role;
    // 네비 active 토글
    document.querySelectorAll(".navbtn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.role === role);
    });
    // 뷰 show/hide
    document.querySelectorAll(".view").forEach(function (v) {
      v.classList.toggle("active", v.id === "view-" + role);
    });
    // 페이지 타이틀
    var t = TITLES[role];
    if (t) {
      $("#page-title").textContent = t[0];
      $("#page-desc").textContent = t[1];
    }
    // localStorage에 현재 탭 저장 (local/index.html에서 th_tab 키 사용)
    try { localStorage.setItem("th_tab", role); } catch (e) {}
    loadAll();
  }

  // ---------- 카드 빌더 ----------
  function cardTitle(role) {
    var titles = {
      pm:    "📋 로드맵 & 의사결정",
      dev:   "💻 작업 & 구현",
      infra: "🔧 인프라 & 상태",
      qa:    "🧪 검증 & 테스트",
      ops:   "🔔 운영 & 브리핑"
    };
    return titles[role] || (role + " 로그");
  }

  function emptyMsg() {
    return '<p class="empty">아직 기록이 없어요.<br>아래에서 추가해 보세요.</p>';
  }

  // ---------- 렌더링 ----------
  var _kb = [];
  var _qaCov = null;
  // 칸반 필터 상태
  var kanbanFilter = { status: "all", q: "" };
  var coralFilter = "all";

  // 상태 필터 칩 버튼 (각 role 칸반 공통)
  function setupStatusChips() {
    document.querySelectorAll('.status-chips').forEach(function (group) {
      var role = group.dataset.role;
      if (!role) {
        // coral-role-filter 같은 특수 그룹 처리
        group.querySelectorAll('.chip-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            group.querySelectorAll('.chip-btn').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            coralFilter = btn.dataset.role;
            renderCoral();
          });
        });
        return;
      }
      group.querySelectorAll('.chip-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var btns = group.querySelectorAll('.chip-btn');
          for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
          btn.classList.add('active');
          kanbanFilter.status = btn.dataset.status;
          renderKanban(role + '-kanban-list', _kb);
        });
      });
      var first = group.querySelector('.chip-btn[data-status="all"]');
      if (first) first.classList.add('active');
    });
  }

  // 칸반 검색 (실시간) + localStorage persistence
  function setupSearch() {
    document.querySelectorAll('.kanban-search').forEach(function (inp) {
      var role = inp.dataset.role;
      // 복원
      var saved = null;
      try { saved = localStorage.getItem('th_search_' + role); } catch (e) {}
      if (saved) { inp.value = saved; kanbanFilter.q = saved; }
      inp.addEventListener('input', function () {
        kanbanFilter.q = inp.value.trim();
        try { localStorage.setItem('th_search_' + role, kanbanFilter.q); } catch (e) {}
        renderKanban(role + '-kanban-list', _kb);
      });
    });
  }

  function renderKanban(elId, rows) {
    var role = elId.split('-')[0];
    var f = rows.filter(function (r) {
      if (r.assignee !== role) return false;
      if (kanbanFilter.status !== "all" && r.status !== kanbanFilter.status) return false;
      if (kanbanFilter.q && !(r.title || "").toLowerCase().includes(kanbanFilter.q.toLowerCase())) return false;
      return true;
    });
    var html = f.map(function (r) {
      return '<div class="krow">' +
        '<div class="st ' + statusClass(r.status) + '">' + statusLabel(r.status) + '</div>' +
        '<div><div class="title">' + esc(r.title) + '</div>' +
        '<div class="meta">' + badge(r.assignee) + ' <span class="tid">' + esc(r.id) + '</span>' + (r.created ? ' · ' + esc(r.created) : '') + '</div></div>' +
        '<div class="meta">' + esc(r.created || "") + '</div>' +
      '</div>';
    }).join("") || '<div class="empty">조건에 맞는 카드가 없습니다.</div>';
    var el = document.getElementById(elId);
    if (el) el.innerHTML = html;
  }

  function renderHealth() {
    var el = document.getElementById("health");
    if (!el) return;
    function _paint(list) {
      el.innerHTML = (list || []).map(function (s) {
        return '<div class="acard"><span class="dot ' + esc(s.state) + '"></span><div class="nm" style="font-size:14px;margin:0">' + esc(s.name) + '</div><div class="id">' + esc(s.note || "") + '</div></div>';
      }).join("");
    }
    if (window.MOCK && window.MOCK.infraStatus) {
      _paint(window.MOCK.infraStatus);
    } else {
      fetch("/api/infra-status").then(function (r) { return r.json(); }).catch(function () { return []; }).then(_paint);
    }
  }

  function renderTimeline() {
    var el = document.getElementById("timeline-list");
    if (!el) return;
    el.innerHTML = (getMOCK().timeline || []).map(function (d) {
      return '<div style="margin-bottom:18px"><div class="pagedesc" style="font-weight:700;margin-bottom:8px">📅 ' + esc(d.date) + '</div>' +
        d.logs.map(function (l) { return '<div class="item">' + badge(l.role) + ' ' + esc(l.text) + '</div>'; }).join('') +
      '</div>';
    }).join("");
  }

  // Coral 메시지 스레드별 그룹화 + 시간대 헤더 + 연속 발신자 병합
  var _coral = [];
  function _groupCoral(list) {
    // 스레드별로 메시지를 시간순 정렬 → 스레드 그룹화
    var byThread = {};
    var order = [];
    (list || []).forEach(function (m) {
      var key = m.thread || "unknown";
      if (!byThread[key]) { byThread[key] = []; order.push(key); }
      byThread[key].push(m);
    });
    order.forEach(function (k) {
      byThread[k].sort(function (a, b) {
        var ta = a.ts || "", tb = b.ts || "";
        return tb < ta ? -1 : tb > ta ? 1 : 0;
      });
    });
    var out = [];
    order.forEach(function (k) {
      out.push({ thread: k, name: byThread[k][0].threadName || k, msgs: byThread[k] });
    });
    return out;
  }
  function _groupCoral(list) {
    var byThread = {};
    var order = [];
    (list || []).forEach(function (m) {
      var key = m.thread || "unknown";
      if (!byThread[key]) { byThread[key] = []; order.push(key); }
      byThread[key].push(m);
    });
    order.forEach(function (k) {
      byThread[k].sort(function (a, b) {
        var ta = a.ts || "", tb = b.ts || "";
        return tb < ta ? -1 : tb > ta ? 1 : 0;
      });
    });
    var out = [];
    order.forEach(function (k) {
      out.push({ thread: k, name: byThread[k][0].threadName || k, msgs: byThread[k] });
    });
    return out;
  }
  function renderCoral() {
    var el = document.getElementById("coral-list");
    if (!el) return;
    var list = (_coral || []).filter(function (c) { return coralFilter === "all" || c.agent === coralFilter; });
    var threads = _groupCoral(list);
    var ROLE_META = {
      pm: "🧄 마늘쿵야", dev: "🧅 양파쿵야", infra: "🥬 무시쿵야", qa: "🥗 샐러리쿵야",
      ops: "🍄 버섯쿵야", claude: "🤖 claude", default: "🤖 unknown"
    };
    function timeHeader(ts) { if (!ts) return ""; var p = String(ts).split(" "); return p[0] || ""; }
    function hourLabel(ts) { if (!ts) return ""; var m = String(ts).match(/\d{2}:\d{2}/); return m ? m[0] : ""; }
    el.innerHTML = threads.length
      ? threads.map(function (t) {
          var head = '<div class="thread-header"><b>#' + esc(t.name || t.thread) + '</b>' +
            (t.msgs[0].isNew ? '<span class="new-tag">NEW</span>' : '') + '</div>';
          var html = ""; var lastAgent = null; var lastDate = "";
          t.msgs.slice().reverse().forEach(function (r) {
            var curDate = timeHeader(r.ts);
            var me = (r.agent === "ops");
            var meta = ROLE_META[r.agent] || r.agent;
            var urgent = ((r.content || "")).includes("URGENT");
            if (curDate && curDate !== lastDate) {
              html += '<div class="thread-date">' + esc(curDate) + '</div>';
              lastDate = curDate;
            }
            if (r.agent !== lastAgent) {
              html += '<div class="chat-row ' + (me ? "me" : "them") + '">' +
                '<div class="chat-ava">' + (meta[0] || "🤖") + '</div>' +
                '<div class="chat-bubble' + (urgent ? " urgent" : "") + '">' +
                '<div class="chat-head"><b>' + meta + '</b><span class="chat-ts">' + esc(hourLabel(r.ts)) + '</span></div>' +
                '<div class="chat-msg">' + ((r.content || "").trim() ? esc(r.content) : "(본문 없음)") + '</div>' +
                '</div></div>';
              lastAgent = r.agent;
            } else {
              html += '<div class="chat-row ' + (me ? "me" : "them") + ' merged">' +
                '<div class="chat-bubble' + (urgent ? " urgent" : "") + '">' +
                '<div class="chat-msg">' + ((r.content || "").trim() ? esc(r.content) : "(본문 없음)") + '</div>' +
                '</div></div>';
            }
          });
          return head + html;
        }).join("")
      : '<div class="empty">해당 역할 무전 없음</div>';
  }

  function renderCoverageDonut() {
    var cov = _qaCov || getMOCK().qaCoverage || {};
    var pct = cov.total ? Math.round(cov.passed / cov.total * 100) : 0;
    var gate = 80;
    var pass = pct >= gate;
    var color = pass ? "var(--dev)" : "var(--bad, #ff7a90)";
    // 1) 게이트 배지
    var gateEl = document.getElementById("qa-coverage-gate");
    if (gateEl) {
      gateEl.innerHTML = '<span class="chip ' + (pass ? "ok" : "bad") + '"><span class="k">커버리지</span> ' + pct + '% · 임계선 ' + gate + '% ' + (pass ? "통과 ✅" : "미달 ⚠") + '</span> <span class="chip"><span class="k">통과</span> ' + (cov.passed||0) + ' / ' + (cov.total||0) + ' (실패 ' + (cov.failed||0) + ')</span>';
    }
    // 2) 메인 도넛
    var el = document.getElementById("qa-coverage-donut");
    if (el) {
      var r = 40, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
      el.innerHTML =
        '<svg width="100" height="100"><circle cx="50" cy="50" r="' + r + '" fill="none" stroke="var(--panel2)" stroke-width="12"/>' +
        '<circle cx="50" cy="50" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="12" stroke-dasharray="' + c + '" stroke-dashoffset="' + off + '" transform="rotate(-90 50 50)"/></svg>' +
        '<div class="item" style="text-align:center">전체 통과율</div>';
    }
    // 3) 추이 스파크라인
    var tEl = document.getElementById("qa-coverage-trend");
    if (tEl && cov.trend && cov.trend.length) {
      var tr = cov.trend, w = 160, h = 60, max = 100, min = Math.min.apply(null, tr) - 5;
      var pts = tr.map(function (v, i) {
        var x = (i / (tr.length - 1)) * (w - 10) + 5;
        var y = h - ((v - min) / (max - min)) * (h - 14) - 7;
        return x.toFixed(1) + "," + y.toFixed(1);
      }).join(" ");
      tEl.innerHTML = '<div class="pagedesc" style="font-weight:700;margin-bottom:4px">📈 주간 추이</div>' +
        '<svg width="' + w + '" height="' + h + '"><polyline points="' + pts + '" fill="none" stroke="var(--dev)" stroke-width="2"/>' +
        tr.map(function (v, i) { var x = (i / (tr.length - 1)) * (w - 10) + 5; var y = h - ((v - min) / (max - min)) * (h - 14) - 7; return '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2.5" fill="var(--dev)"/>'; }).join("") +
        '</svg><div class="t" style="color:var(--muted);font-size:11px">' + tr[0] + '% → ' + tr[tr.length-1] + '% (' + ((tr[tr.length-1]-tr[0]>=0?"+":"")+(tr[tr.length-1]-tr[0])) + 'p)</div>';
    }
    // 4) 카테고리별 바
    var cEl = document.getElementById("qa-coverage-cat");
    if (cEl && cov.byCategory && cov.byCategory.length) {
      cEl.innerHTML = '<div class="pagedesc" style="font-weight:700;margin-bottom:6px">🗂️ 카테고리별</div>' +
        cov.byCategory.map(function (x) {
          var rp = x.total ? Math.round(x.passed / x.total * 100) : 0;
          var col = rp >= 80 ? "var(--dev)" : (rp >= 60 ? "var(--warn,#f4c430)" : "var(--bad,#ff7a90)");
          return '<div class="mbar"><span style="width:42px">' + esc(x.cat) + '</span><div class="bar"><div class="fill" style="width:' + rp + '%;background:' + col + '"></div></div><b>' + rp + '%</b><span class="t" style="margin-left:6px;color:var(--muted)">' + x.passed + '/' + x.total + '</span></div>';
        }).join("");
    }
    // 5) 에이전트별 표
    var aEl = document.getElementById("qa-coverage-agent");
    if (aEl && cov.byAgent && cov.byAgent.length) {
      aEl.innerHTML = '<div class="pagedesc" style="font-weight:700;margin-bottom:6px">🤖 에이전트별 통과율</div>' +
        '<div class="ktbl">' + cov.byAgent.map(function (x) {
          var rp = x.rate; var warn = rp < 80 ? ' <span class="badge-warn">⚠</span>' : '';
          var col = rp >= 80 ? "var(--dev)" : "var(--bad,#ff7a90)";
          return '<div class="ktr"><span class="krole">' + badge(x.role) + '</span><div class="bar"><div class="fill" style="width:' + rp + '%;background:' + col + '"></div></div><b>' + rp + '%</b>' + warn + '</div>';
        }).join("") + '</div>';
    }
    // 6) 기존 리스트 (호환)
    var lEl = document.getElementById("qa-coverage-list");
    if (lEl) lEl.innerHTML = '';
  }

  function renderQaEvalBoard(ev) {
    var el = document.getElementById("qa-eval-board");
    if (!el) return;
    // local: {board:[{role,name,score,grade,light,comment,metrics,date}]} / demo: {agents:[...]}
    var rows = (ev && ev.board) ? ev.board : (ev && ev.agents ? ev.agents : (getMOCK().qaEval || {}).agents);
    if (!rows || !rows.length) { el.innerHTML = '<div class="empty">평가 데이터 없음</div>'; return; }
    function gc(g) { return g === "A" ? "#7ed957" : g === "B" ? "#f4c430" : (g === "C" ? "#ff9a3c" : "#ff7a90"); }
    var avg = Math.round(rows.reduce(function (s, a) { return s + (a.score || 0); }, 0) / rows.length);
    var when = (ev && ev.updated) || (rows[0] && rows[0].date) || "";
    var bars = rows.map(function (a) {
      var col = gc(a.grade), w = Math.max(0, Math.min(100, a.score || 0));
      return '<div class="eval-bar-row"><span class="eval-bar-name">' + esc(a.name || a.role) + '</span>' +
        '<div class="eval-bar-track"><div class="eval-bar-fill" style="width:' + w + '%;background:' + col + '"></div></div>' +
        '<span class="eval-bar-score" style="color:' + col + '">' + (a.score || 0) + (a.grade ? '<small>' + esc(a.grade) + '</small>' : '') + '</span></div>';
    }).join("");
    var notes = rows.map(function (a) {
      var m = a.metrics || a;
      return '<div class="item"><span class="t">' + badge(a.role) + ' ' + esc(a.name || a.role) + '</span> · ' +
        esc(a.comment || a.note || "") +
        (m.done != null ? ' <span class="t" style="color:var(--muted)">✓' + m.done + ' ⛔' + (m.blocked||0) + ' ✗' + (m.reject||0) + ' ⚠' + (m.errors||0) + '</span>' : '') + '</div>';
    }).join("");
    el.innerHTML = '<div class="eval-avg" style="margin-bottom:10px">평균 <b>' + avg + '</b>점' +
      (when ? ' <span class="eval-date" style="color:var(--muted)">' + esc(when) + ' · ' + rows.length + '명</span>' : '') + '</div>' +
      '<div class="eval-bars">' + bars + '</div>' + notes;
  }

  function renderResources(res) {
    var el = document.getElementById("infra-resources-list");
    if (!el) return;
    res = res || getMOCK().infraResources || {};
    el.innerHTML =
      '<div class="mbar"><span>CPU</span><div class="bar"><div class="fill" style="width:' + (res.cpu || 0) + '%"></div></div><b>' + (res.cpu || 0) + '%</b></div>' +
      '<div class="mbar"><span>MEM</span><div class="bar"><div class="fill" style="width:' + (res.mem || 0) + '%"></div></div><b>' + (res.mem || 0) + '%</b></div>' +
      '<div class="t" style="color:var(--muted)">' + esc(res.note || "") + '</div>';
  }

  // ---------- 환경맵 폴더 트리 (├─└─) ----------
  // local/app.py 의 api_env_tree() 가 실제 fs 스캔 결과를 /api/env-tree 로 내려줌.
  // 정적 Pages 데모에서는 getMOCK().envTree 더미 사용.
  function treeLines(node, prefix, isLast, isRoot) {
    var parts = [];
    if (!isRoot) {
      var conn = isLast ? "└─ " : "├─ ";
      parts.push(prefix + conn + esc(node.name) +
        (node.type === "dir" && node.children && node.children.length ? "/" : ""));
    } else {
      parts.push(prefix + esc(node.name) + (node.type === "dir" ? "/" : ""));
    }
    if (node.children && node.children.length) {
      var childPrefix = isRoot ? "" : (prefix + (isLast ? "   " : "│  "));
      for (var i = 0; i < node.children.length; i++) {
        var sub = treeLines(node.children[i], childPrefix, i === node.children.length - 1, false);
        for (var j = 0; j < sub.length; j++) parts.push(sub[j]);
      }
    }
    return parts;
  }

  function renderEnvTree(data) {
    var el = document.getElementById("env-tree");
    if (!el) return;
    if (!data || !data.roots) return;
    var html = data.roots.map(function (n) {
      var rows = [];
      if (n.exists && n.tree) {
        rows = treeLines(n.tree, "", true, true);
      } else if (n.secret) {
        rows = ["<span style=\"color:#ff7a90\">(비밀 — 내용 비노출)</span>"];
      } else if (!n.exists) {
        rows = ["<span style=\"color:var(--muted)\">경로 없음</span>"];
      }
      return '<div class="env-block">' +
        '<div class="env-row"><span class="dot ' + (n.exists ? 'ok' : 'bad') + '"></span>' +
        '<code class="env-path">' + esc(n.label) + '</code>' +
        '<span class="env-desc">' + esc(n.desc || '') + '</span>' +
        (n.secret ? '<span class="env-tag">⚠️ 비노출</span>' : '') +
        '</div>' +
        '<pre class="env-tree-block" style="margin:6px 0 0 0;font-size:12px;line-height:1.45;color:var(--muted);overflow-x:auto;white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace">' + rows.join("\n") + '</pre>' +
        '</div>';
    }).join('');
    el.innerHTML = '<div class="env-tree">' + html + '</div>';
    var warn = document.getElementById("envmap-warn");
    if (warn) {
      warn.innerHTML = '<div class="env-note">⚠️ <b>.env.local</b> 은 절대 Git에 커밋하지 마세요. 노출 시 즉시 키 로테이션 권장.</div>';
    }
  }

  async function loadAll() {
    try {
      var [kb, ag, cr, qaEval, envTree, qaCov,
           pmTasks, pmRoadmap, devSnippets, infraStatus, infraRes, qaChecklist, opsBrief, opsCmds] = await Promise.all([
        getJSON("/api/kanban"), getJSON("/api/agents"), getJSON("/api/coral"), getJSON("/api/qa-eval"), getJSON("/api/env-tree"), getJSON("/api/qa-coverage"),
        getJSON("/api/pm-tasks"), getJSON("/api/pm-roadmap"), getJSON("/api/dev-snippets"), getJSON("/api/infra-status"), getJSON("/api/infra-resources"), getJSON("/api/qa-checklist"), getJSON("/api/ops-briefing"), getJSON("/api/ops-commands")]);
      // local(실 fetch) 우선, 비면 demo MOCK 폴백
      function _pick(real, mockKey) { var m = getMOCK()[mockKey];
        if (Array.isArray(real)) return real.length ? real : (m || []);
        return (real && Object.keys(real).length) ? real : (m || real); }
      // demo(Pages/file://) 폴백: fetch 실패 시 window.MOCK 사용
      if ((!kb || !kb.length) && window.MOCK && window.MOCK.kanban) kb = window.MOCK.kanban;
      if ((!ag || !ag.length) && window.MOCK && window.MOCK.agents) ag = window.MOCK.agents;
      if ((!cr || !cr.length) && window.MOCK && window.MOCK.coral) cr = window.MOCK.coral;
      if ((!envTree || !envTree.length) && window.MOCK && window.MOCK.envTree) envTree = window.MOCK.envTree;
      if ((!qaCov || !qaCov.total) && window.MOCK && window.MOCK.qaCoverage) qaCov = window.MOCK.qaCoverage;
      _qaCov = qaCov;
      _kb = kb;
      _coral = cr;
      var active = kb.filter(function (r) { return r.status !== "done" && r.status !== "blocked" && r.status !== "archived"; }).length;
      setText("k-count", String(active));
      setText("a-count", String(ag.filter(function (a) { return a.exists; }).length));
      setText("c-count", String(cr.length));
      var updated = document.getElementById("updated");
      if (updated) updated.textContent = "마지막 갱신 " + nowStr() + " · 30s 자동갱신";

      // 로스터
      var roster = document.getElementById("roster");
      if (roster) {
        roster.innerHTML = ag.map(function (a) {
          return '<div class="acard">' + badge(a.role) +
            '<div class="nm" style="margin-top:6px">' + esc(a.name || a.role) + '</div>' +
            '<div class="id">' + esc(a.identity || "") + '</div>' +
            (a.provider ? '<span class="chip"><span class="k">provider</span> ' + esc(a.provider) + '</span>' : "") +
            (a.model ? '<span class="chip"><span class="k">model</span> ' + esc(a.model) + '</span>' : "") +
            (a.fallback ? '<span class="chip"><span class="k">fb</span> ' + esc(a.fallback) + '</span>' : "") +
          '</div>';
        }).join("");
      }

      // 봇별 칸반 (role 필터 적용)
      ["pm", "dev", "infra", "qa", "ops"].forEach(function (r) {
        renderKanban(r + "-kanban-list", kb);
      });

      // PM
      pmTasks = _pick(pmTasks, "pmTasks");
      var el = document.getElementById("pm-tasks-list");
      if (el) el.innerHTML = pmTasks.length ? pmTasks.map(function (t) { return '<div class="item">' + esc(typeof t === "string" ? t : (t.title || t.text || "")) + '</div>'; }).join("") : '<div class="empty">없음</div>';
      pmRoadmap = _pick(pmRoadmap, "pmRoadmap");
      var el2 = document.getElementById("pm-roadmap-list");
      if (el2) el2.innerHTML = pmRoadmap.length ? pmRoadmap.map(function (r) {
        return '<div class="item"><span class="t">' + esc(r.month || "") + '</span><br>' + esc(r.goal || "") + '</div>';
      }).join("") : '<div class="empty">없음</div>';

      // Dev (로컬: 실제 fetch, 데모: MOCK)
      devSnippets = _pick(devSnippets, "devSnippets");
      var el3 = document.getElementById("dev-snippets-list");
      if (el3) el3.innerHTML = devSnippets.length ? devSnippets.map(function (s) {
        return '<div class="item"><span class="t">' + esc(s.ts || "") + '</span><pre style="white-space:pre-wrap;margin:4px 0">' + esc(s.code || "") + '</pre></div>';
      }).join("") : '<div class="empty">없음</div>';
      var el4 = document.getElementById("dev-bugs-list");
      if (el4) {
        fetch("/api/dev-bugs").then(function(r){return r.json();}).catch(function(){return getMOCK().devBugs || [];}).then(function(list){
          var bugs = (list && list.length) ? list : (getMOCK().devBugs || []);
          el4.innerHTML = bugs.length ? bugs.map(function (b) {
            return '<div class="krow"><div class="st st-blocked">⛔ 보류</div><div><div class="title">' + esc(b.title || b.id || "") + '</div><div class="meta"><span class="tid">' + esc(b.id || "") + '</span></div></div><div></div></div>';
          }).join("") : '<div class="empty">반려된 카드 없음 🎉</div>';
        });
      }

      // Infra
      infraStatus = _pick(infraStatus, "infraStatus");
      var el5 = document.getElementById("infra-status-list");
      if (el5) el5.innerHTML = infraStatus.length ? infraStatus.map(function (s) {
        return '<div class="item"><span class="dot ' + esc(s.state) + '"></span>' + esc(s.name) + ' — ' + esc(s.note || "") + '</div>';
      }).join("") : '<div class="empty">상태 없음</div>';
      renderResources(_pick(infraRes, "infraResources"));

      // QA
      qaChecklist = _pick(qaChecklist, "qaChecklist");
      var el6 = document.getElementById("qa-checklist-list");
      if (el6) el6.innerHTML = qaChecklist.length ? qaChecklist.map(function (c) { return '<div class="item">☐ ' + esc(typeof c === "string" ? c : (c.title || c.text || "")) + '</div>'; }).join("") : '<div class="empty">항목 없음</div>';
      renderCoverageDonut();
      renderQaEvalBoard(qaEval);

      // Ops
      var br = _pick(opsBrief, "opsBriefing");
      var el7 = document.getElementById("ops-brief-out");
      if (el7 && br) el7.textContent = buildBrief(br);
      opsCmds = _pick(opsCmds, "opsCommands");
      var el8 = document.getElementById("ops-commands-list");
      if (el8) el8.innerHTML = opsCmds.length ? opsCmds.slice().reverse().map(function (c) {
        return '<div class="item"><span class="t">' + esc(c.ts || "") + '</span><br>' + esc(c.text || "") + '</div>';
      }).join("") : '<div class="empty">보관된 명령 없음</div>';

      renderCoral();
      renderHealth();
      renderTimeline();
      // 환경맵 폴더 트리 (real fetch /api/env-tree 또는 getMOCK().envTree)
      renderEnvTree(envTree || getMOCK().envTree);
    } catch (e) {
      console.error(e);
    }
  }

  function buildBrief(b) {
    b = b || {};
    return "대장님, 오늘 브리핑입니다.\n\n[어제]\n" + (b.yesterday || "—") +
      "\n\n[오늘]\n" + (b.today || "—") +
      "\n\n[블로커]\n" + (b.blocker || "없음");
  }

  function nowStr() {
    var d = new Date();
    return d.toTimeString().slice(0, 8);
  }

  function toast(msg) {
    var t = document.getElementById("toast");
    if (t) { t.textContent = msg; t.classList.add("show"); setTimeout(function () { t.classList.remove("show"); }, 1800); }
  }

  // ---------- 저장 (정적 버전: localStorage, local/app.py 있으면 POST) ----------
  async function savePMTasks() {
    var v = document.getElementById("pm-task-input").value.trim();
    if (!v) return;
    var c = await getJSON("/api/pm-tasks");
    c.push(v);
    await postJSON("/api/pm-tasks", c);
    document.getElementById("pm-task-input").value = "";
    loadAll();
  }

  async function savePMRoadmap() {
    var v = document.getElementById("pm-roadmap-input").value.trim();
    if (!v) return;
    var parts = v.split("|");
    var c = await getJSON("/api/pm-roadmap");
    c.push({ month: (parts[0] || "").trim(), goal: (parts[1] || "").trim() });
    await postJSON("/api/pm-roadmap", c);
    document.getElementById("pm-roadmap-input").value = "";
    loadAll();
  }

  async function saveDevSnippet() {
    var v = document.getElementById("dev-snippet-input").value.trim();
    if (!v) return;
    var c = await getJSON("/api/dev-snippets");
    c.push({ ts: new Date().toISOString().slice(0, 10), code: v });
    await postJSON("/api/dev-snippets", c);
    document.getElementById("dev-snippet-input").value = "";
    loadAll();
  }

  async function saveQAChecklist() {
    var v = document.getElementById("qa-checklist-input").value.trim();
    if (!v) return;
    var c = await getJSON("/api/qa-checklist");
    c.push(v);
    await postJSON("/api/qa-checklist", c);
    document.getElementById("qa-checklist-input").value = "";
    loadAll();
  }

  async function saveQACoverage() {
    var v;
    try { v = JSON.parse(document.getElementById("qa-coverage-input").value); }
    catch (e) { alert("JSON 오류"); return; }
    await postJSON("/api/qa-coverage", v);
    document.getElementById("qa-coverage-input").value = "";
    loadAll();
  }

  async function saveBriefing() {
    var b = {
      yesterday: document.getElementById("ops-y").value,
      today: document.getElementById("ops-t").value,
      blocker: document.getElementById("ops-b").value
    };
    await postJSON("/api/ops-briefing", b);
    var el = document.getElementById("ops-brief-out");
    if (el) el.textContent = buildBrief(b);
  }

  function copyBrief() {
    var el = document.getElementById("ops-brief-out");
    if (el) navigator.clipboard.writeText(el.textContent);
  }

  async function saveCommand() {
    var v = document.getElementById("ops-command-input").value.trim();
    if (!v) return;
    var c = await getJSON("/api/ops-commands");
    c.push({ ts: new Date().toISOString().slice(0, 19), text: v });
    await postJSON("/api/ops-commands", c);
    document.getElementById("ops-command-input").value = "";
    loadAll();
  }

  // ---------- 네비 ----------
  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function badge(role) {
    return '<span class="badge ' + (role || "unknown") + '">' + esc((role || "?").toUpperCase()) + '</span>';
  }

  function esc(s) {
    return String(s === null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function statusLabel(s) {
    return ({
      done: "✅ 완료", blocked: "⛔ 보류", running: "🔄 진행",
      ready: "⏳ 대기", claimed: "🤝 착수", archived: "📦 보관"
    })[s] || s;
  }

  function statusClass(s) {
    return "st-" + (s || "ready");
  }

  var TITLES = {
    dashboard: ["팀 현황", "쿵야 크루 5명의 작업을 한눈에"],
    pm:        ["🧄 PM", "기획·분배·로드맵"],
    dev:       ["🧅 Dev", "코드·버그·스니펫"],
    infra:     ["🥬 Infra", "상태·리소스 모니터"],
    qa:        ["🥗 QA", "검증·커버리지"],
    ops:       ["🍄 Ops", "브리핑·명령 보관"],
    coral:     ["📡 에이전트 통신", "실시간 agent 교신"],
    timeline:  ["🗓️ 타임라인", "5명 로그 통합"]
  };

  // ---------- 서브탭 ----------
  function setupSubtabs() {
    document.querySelectorAll(".subtab").forEach(function (st) {
      st.addEventListener("click", function () {
        var role = st.dataset.sub.split("-")[0];
        document.querySelectorAll("#view-" + role + " .subtab").forEach(function (x) {
          x.classList.remove("active");
        });
        st.classList.add("active");
        document.querySelectorAll("#view-" + role + " .subview").forEach(function (v) {
          v.classList.remove("active");
        });
        var sv = document.getElementById("sub-" + st.dataset.sub);
        if (sv) sv.classList.add("active");
        // 탭 전환 시 해당 role 칸반을 로드된 데이터로 즉시 렌더 (초기 빈 상태 방지)
        if (_kb && _kb.length) renderKanban(role + "-kanban-list", _kb);
      });
    });
  }

  // ---------- 3단 그리드 렌더 ----------
  // demo(Pages/file://)에서 window.MOCK이 비동기/지연 바인딩될 수 있으므로,
  // 매 참조 시점의 window.MOCK을 쓰도록 getter로 노출
  function getMOCK() { return (typeof window.MOCK !== "undefined") ? window.MOCK : {}; }
  function renderRosterCompact() {
    var box = document.getElementById("roster");
    if (!box) return;
    fetch("/api/agents").then(function(r){return r.json();}).catch(function(){return getMOCK().agents || [];}).then(function(list){
      var ag = list && list.length ? list : (getMOCK().agents || []);
      box.innerHTML = ag.map(function(a){
        return '<div class="acard compact mem-card" data-role="'+a.role+'">'+
          '<div class="nm">'+a.name+' <span class="badge '+(a.role||'unknown')+'">'+(a.role||'?')+'</span></div>'+
          '<div class="id">'+(a.identity||'')+'</div>'+
          '<div class="mem-body" id="mem-'+a.role+'" style="display:none"></div></div>';
      }).join("");
      ag.forEach(function(a){
        var card = box.querySelector('.mem-card[data-role="'+a.role+'"]');
        if(!card) return;
        card.addEventListener("click", function(){
          var mb = card.querySelector(".mem-body");
          if(mb.style.display==="none"){
            var m = (a.memory) || (getMOCK().memory && getMOCK().memory[a.role]) || { snapshot:"(메모리 없음)", skills:[] };
            var snap = (m.snapshot||"(메모리 없음)").split("\n").join("<br>");
            mb.innerHTML = '<div class="mem-md">'+snap+'</div><div class="mem-skills">'+(m.skills||[]).map(function(s){return '<span class="chip">'+s+'</span>';}).join("")+'</div>';
            mb.style.display="block";
          } else { mb.style.display="none"; }
        });
      });
    });
  }
  function renderDashKanban() {
    var box = document.getElementById("dash-kanban");
    if (!box) return;
    var cols = [
      { s:"running", t:"🔄 In Progress" },
      { s:"review", t:"🔍 Review" },
      { s:"blocked", t:"⛔ Blocked" }
    ];
    box.innerHTML = cols.map(function(c){
      return '<div class="kcol"><div class="kcol-h">'+c.t+'</div><div id="dash-k-'+c.s+'"></div></div>';
    }).join("");
    cols.forEach(function(c){
      fetch("/api/kanban").then(function(r){return r.json();}).catch(function(){return getMOCK().kanban||[];}).then(function(rows){
        var rs = rows.filter(function(x){return x.status===c.s;});
        var el = document.getElementById("dash-k-"+c.s);
        if (el) el.innerHTML = rs.map(function(x){
          return '<div class="kcard"><b>'+x.title+'</b><div class="kmeta">'+(x.assignee||'?')+' · '+(x.role||'')+'</div></div>';
        }).join("") || '<div class="kempty">-</div>';
      });
    });
  }
  function renderCoralStream() {
    var box = document.getElementById("coral-stream");
    if (!box) return;
    fetch("/api/coral").then(function(r){return r.json();}).catch(function(){return getMOCK().coral||[];}).then(function(rows){
      var rs = rows && rows.length ? rows : (getMOCK().coral||[]);
      box.innerHTML = rs.slice().reverse().map(function(m){
        return '<div class="crow"><span class="cts">'+(m.ts||'')+'</span> <b>'+(m.from||'?')+'</b>: '+m.text+'</div>';
      }).join("");
    });
  }
  function renderTimelineDash() {
    var box = document.getElementById("timeline-list");
    if (!box) return;
    fetch("/api/activities").then(function(r){return r.json();}).catch(function(){return getMOCK().activities||[];}).then(function(rows){
      var rs = rows && rows.length ? rows : (getMOCK().activities||[]);
      box.innerHTML = rs.slice().reverse().map(function(a){
        return '<div class="titem"><span class="tts">'+(a.ts||'')+'</span> '+a.text+'</div>';
      }).join("");
    });
  }

  // ---------- 인프라 라이브 밴드 (폴링) ----------
  function renderInfraBand() {
    var band = document.getElementById("infra-band");
    if (!band) return;
    fetch("/api/infrastructure")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var roots = [
          { key: "project_root", label: "PROJECT" },
          { key: "e2e_root", label: "E2E" },
          { key: "hermes_home", label: "HERMES" }
        ];
        band.innerHTML = '<div class="infra-band-title">🔧 Infrastructure Live Monitor</div>' + roots.map(function (r) {
          var d = data[r.key] || {};
          var bad = !d.exists || d.branch === null || d.branch === "fatal: not a git repository";
          var sub = d.branch ? ("branch " + d.branch) : (d.exists ? "non-git" : "MISSING");
          if (r.key === "e2e_root" && typeof d.reports_count !== "undefined") sub += " · reports " + d.reports_count;
          return '<div class="infra-root' + (bad ? " bad" : "") + '">' +
            '<span class="ir-dot"></span>' +
            '<span class="ir-label">' + r.label + '</span>' +
            '<span class="ir-path">' + (d.path || "-") + '</span>' +
            '<span class="ir-status">' + (bad ? "⚠ CONVENTION VIOLATION" : sub) + '</span>' +
            '</div>';
        }).join("");
      })
      .catch(function () {
        band.innerHTML = '<div class="infra-root bad"><span class="ir-dot"></span><span class="ir-label">INFRA</span><span class="ir-status">⚠ API UNREACHABLE</span></div>';
      });
  }

  // ---------- 초기화 ----------
  function init() {
    setupNav();
    setupSubtabs();

    // localStorage에서 마지막 탭 복원 (th_tab 키)
    var savedTab = null;
    try { savedTab = localStorage.getItem("th_tab"); } catch (e) {}
    if (savedTab) {
      var tb = document.querySelector(".navbtn[data-role='" + savedTab + "']");
      if (tb) { tb.classList.add("active"); }
      var sv = document.getElementById("view-" + savedTab);
      if (sv) { sv.classList.add("active"); }
      document.querySelectorAll(".navbtn").forEach(function (b) {
        if (b.dataset.role !== savedTab) b.classList.remove("active");
      });
      document.querySelectorAll(".view").forEach(function (v) {
        if (v.id !== "view-" + savedTab) v.classList.remove("active");
      });
      var t = TITLES[savedTab];
      if (t) {
        $("#page-title").textContent = t[0];
        $("#page-desc").textContent = t[1];
      }
    }

    setupStatusChips();
    setupSearch();

    // 기본 탭: 현황(dashboard)
    if (!savedTab) switchTo("dashboard");
    loadAll();
    renderInfraBand();
    renderRosterCompact();
    renderDashKanban();
    renderCoralStream();
    renderTimelineDash();
    setInterval(loadAll, 30000);
    setInterval(renderInfraBand, 15000);
    setInterval(function(){ renderDashKanban(); renderCoralStream(); renderTimelineDash(); }, 20000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // public API for save functions (hoisted by declaration)
  global.savePMTasks = savePMTasks;
  global.savePMRoadmap = savePMRoadmap;
  global.saveDevSnippet = saveDevSnippet;
  global.saveQAChecklist = saveQAChecklist;
  global.saveQACoverage = saveQACoverage;
  global.saveBriefing = saveBriefing;
  global.copyBrief = copyBrief;
  global.saveCommand = saveCommand;
  global.loadAll = loadAll;
})(window);
