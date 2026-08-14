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
    { key: "coral",     label: "📡 무전", ic: "📡" }
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
    if (!nav) return;
    nav.innerHTML = "";
    NAV_ITEMS.forEach(function (item) {
      var btn = document.createElement("button");
      btn.className = "navbtn";
      btn.setAttribute("data-role", item.key);
      btn.innerHTML = '<span class="ic">' + item.ic + "</span> " + item.label;
      btn.addEventListener("click", function () { switchTo(item.key); });
      nav.appendChild(btn);
    });
    // 첫 번째(현황) 선택
    if (nav.children[0]) nav.children[0].classList.add("active");
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
  var kanbanFilter = { status: "all", q: "" };

  function renderKanban(elId, rows) {
    var f = rows.filter(function (r) {
      if (kanbanFilter.status !== "all" && r.status !== kanbanFilter.status) return false;
      if (kanbanFilter.q && !(r.title || "").toLowerCase().includes(kanbanFilter.q.toLowerCase())) return false;
      return true;
    });
    var html = f.map(function (r) {
      return '<div class="krow">' +
        '<div class="st ' + statusClass(r.status) + '">' + statusLabel(r.status) + '</div>' +
        '<div>' +
          '<div class="title">' + esc(r.title) + '</div>' +
          '<div class="meta">' + badge(r.assignee) + ' <span class="tid">' + esc(r.id) + '</span>' + (r.created ? ' · ' + esc(r.created) : '') + '</div>' +
        '</div>' +
        '<div class="meta">' + esc(r.created || "") + '</div>' +
      '</div>';
    }).join("") || '<div class="empty">조건에 맞는 카드가 없습니다.</div>';
    var el = document.getElementById(elId);
    if (el) el.innerHTML = html;
  }

  async function loadAll() {
    try {
      var [kb, ag, cr] = await Promise.all([
        getJSON("/api/kanban"),
        getJSON("/api/agents"),
        getJSON("/api/coral")
      ]);
      _kb = kb;

      var active = kb.filter(function (r) { return r.status !== "done" && r.status !== "blocked"; }).length;
      setText("k-count", String(active));
      setText("a-count", String(ag.filter(function (a) { return a.exists; }).length));
      setText("c-count", String(cr.length));

      // 로스터
      var roster = document.getElementById("roster");
      if (roster) {
        roster.innerHTML = ag.map(function (a) {
          return '<div class="acard">' +
            badge(a.role) +
            '<div class="nm" style="margin-top:6px">' + esc(a.name || a.role) + '</div>' +
            '<div class="id">' + esc(a.identity || "") + '</div>' +
            (a.provider ? '<span class="chip"><span class="k">provider</span> ' + esc(a.provider) + '</span>' : "") +
            (a.model ? '<span class="chip"><span class="k">model</span> ' + esc(a.model) + '</span>' : "") +
            (a.fallback ? '<span class="chip"><span class="k">fb</span> ' + esc(a.fallback) + '</span>' : "") +
          '</div>';
        }).join("");
      }

      // 봇별 칸반
      ROLES.forEach(function (r) {
        renderKanban(r.key + "-kanban-list", kb);
      });
    } catch (e) {
      console.error(e);
    }

    // 나머지 비동기 섹션들 (MOCK-first)
    await loadPM();
    await loadDev();
    await loadInfra();
    await loadQA();
    await loadOps();
    await loadCoral();
  }

  async function loadPM() {
    var [pmt, pmr] = await Promise.all([getJSON("/api/pm-tasks"), getJSON("/api/pm-roadmap")]);
    var el = document.getElementById("pm-tasks-list");
    if (el) el.innerHTML = pmt.length ? pmt.map(function (t) { return '<div class="item">' + esc(t) + '</div>'; }).join("") : '<div class="empty">없음</div>';
    var el2 = document.getElementById("pm-roadmap-list");
    if (el2) el2.innerHTML = pmr.length ? pmr.map(function (r) {
      return '<div class="item"><span class="t">' + esc(r.month || "") + '</span><br>' + esc(r.goal || "") + '</div>';
    }).join("") : '<div class="empty">없음</div>';
  }

  async function loadDev() {
    var [sn, bugs] = await Promise.all([getJSON("/api/dev-snippets"), getJSON("/api/dev-bugs")]);
    var el = document.getElementById("dev-snippets-list");
    if (el) el.innerHTML = sn.length ? sn.map(function (s) {
      return '<div class="item"><span class="t">' + esc(s.ts || "") + '</span><pre style="white-space:pre-wrap;margin:4px 0">' + esc(s.code || "") + '</pre></div>';
    }).join("") : '<div class="empty">없음</div>';
    var el2 = document.getElementById("dev-bugs-list");
    if (el2) el2.innerHTML = bugs.length ? bugs.map(function (b) {
      return '<div class="krow"><div class="st st-blocked">⛔ 보류</div><div><div class="title">' + esc(b.title) + '</div><div class="meta"><span class="tid">' + esc(b.id) + '</span></div></div><div></div></div>';
    }).join("") : '<div class="empty">반려된 카드 없음 🎉</div>';
  }

  async function loadInfra() {
    var [st, res] = await Promise.all([getJSON("/api/infra-status"), getJSON("/api/infra-resources")]);
    var el = document.getElementById("infra-status-list");
    if (el) el.innerHTML = st.map(function (s) {
      return '<div class="item"><span class="dot ' + esc(s.state) + '"></span>' + esc(s.name) + ' — ' + esc(s.note || "") + '</div>';
    }).join("");
    var el2 = document.getElementById("infra-resources-list");
    if (el2) el2.innerHTML =
      '<div class="item">CPU ' + (res.cpu || 0) + '% · MEM ' + (res.mem || 0) + '%</div>' +
      '<div class="t" style="color:var(--muted)">' + esc(res.note || "") + '</div>';
  }

  async function loadQA() {
    var [qc, cov] = await Promise.all([getJSON("/api/qa-checklist"), getJSON("/api/qa-coverage")]);
    var el = document.getElementById("qa-checklist-list");
    if (el) el.innerHTML = qc.length ? qc.map(function (c) { return '<div class="item">☐ ' + esc(c) + '</div>'; }).join("") : '<div class="empty">항목 없음</div>';
    var rate = cov.total ? Math.round(cov.passed / cov.total * 100) : 0;
    var el2 = document.getElementById("qa-coverage-list");
    if (el2) el2.innerHTML = '<div class="item">통과 ' + (cov.passed || 0) + ' / 전체 ' + (cov.total || 0) + ' (' + rate + '%)</div>';
  }

  async function loadOps() {
    var [br, cm] = await Promise.all([getJSON("/api/ops-briefing"), getJSON("/api/ops-commands")]);
    var el = document.getElementById("ops-brief-out");
    if (el) el.textContent = buildBrief(br);
    var el2 = document.getElementById("ops-commands-list");
    if (el2) el2.innerHTML = cm.length ? cm.slice().reverse().map(function (c) {
      return '<div class="item"><span class="t">' + esc(c.ts || "") + '</span><br>' + esc(c.text || "") + '</div>';
    }).join("") : '<div class="empty">보관된 명령 없음</div>';
  }

  async function loadCoral() {
    var cr = await getJSON("/api/coral");
    var el = document.getElementById("coral-list");
    if (el) {
      el.innerHTML = cr.length
        ? cr.slice().reverse().map(function (r) {
            return '<div class="row">' +
              badge(r.agent) +
              ' <span style="color:var(--muted);font-size:12px">' + esc(r.ts || "") + '</span>' +
              '<div style="margin-top:4px">' + (r.content ? esc(r.content) : "(본문 없음)") + '</div>' +
            '</div>';
          }).join("")
        : '<div class="empty">아직 무전 기록이 없습니다.</div>';
    }
  }

  function buildBrief(b) {
    b = b || {};
    return "대장님, 오늘 브리핑입니다.\n\n[어제]\n" + (b.yesterday || "—") +
      "\n\n[오늘]\n" + (b.today || "—") +
      "\n\n[블로커]\n" + (b.blocker || "없음");
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
      ready: "⏳ 대기", claimed: "🤝 착수"
    })[s] || s;
  }

  function statusClass(s) {
    return "st-" + (s || "ready");
  }

  var TITLES = {
    dashboard: ["팀 현황", "쿵야 크루 5명의 작업을 한눈에"],
    pm:        ["🧄 PM", "기획·분배·로드맵"],
    dev:       ["🧅 Dev", "코드·버그·스니펫"],
    infra:     ["🧄 Infra", "상태·리소스 모니터"],
    qa:        ["🥗 QA", "검증·커버리지"],
    ops:       ["🍄 Ops", "브리핑·명령 보관"],
    coral:     ["📡 무전", "실시간 agent 교신"]
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
      });
    });
  }

  // ---------- 초기화 ----------
  function init() {
    setupNav();
    setupSubtabs();
    // 기본 탭: 현황(dashboard)
    switchTo("dashboard");
    loadAll();
    setInterval(loadAll, 30000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})(window);
