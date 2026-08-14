// app.js — hermes-team-hub 메인 로직
// 기능: 역할 탭 전환 + 각 역할별 뷰 렌더링 + localStorage CRUD
// (global.HubStore in store.js 담당)

(function (global) {
  "use strict";

  var ROLES = [
    { key: "pm",    label: "🧄 PM",    color: "var(--pm)",   view: "view-pm" },
    { key: "dev",   label: "🧅 Dev",   color: "var(--dev)",  view: "view-dev" },
    { key: "infra", label: "🧄 Infra", color: "var(--infra)",view: "view-infra" },
    { key: "qa",    label: "🥗 QA",    color: "var(--qa)",   view: "view-qa" },
    { key: "ops",   label: "🍄 Ops",   color: "var(--ops)",  view: "view-ops" }
  ];

  var state = { current: null };

  // ---------- DOM ----------
  function $(sel) { return document.querySelector(sel); }

  function setupTabs() {
    var nav = $("#nav");
    if (!nav) return;
    nav.innerHTML = "";
    ROLES.forEach(function (r) {
      var btn = document.createElement("button");
      btn.className = "tab";
      btn.setAttribute("data-role", r.key);
      btn.textContent = r.label;
      btn.addEventListener("click", function () { switchTo(r.key); });
      nav.appendChild(btn);
    });
  }

  function switchTo(role) {
    state.current = role;
    ROLES.forEach(function (r) {
      // 탭 active 토글
      var btn = $("button.tab[data-role='" + r.key + "']");
      if (btn) {
        if (r.key === role) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      }
      // 뷰 show/hide
      var view = $("#" + r.view);
      if (view) {
        if (r.key === role) {
          view.classList.add("active");
        } else {
          view.classList.remove("active");
        }
      }
    });
    render(role);
  }

  // ---------- 카드 빌더 ----------
  function cardTitle(role) {
    var titles = {
      pm:    "📋 로드맵 & 의사결정",
      dev:   "💻 작업 & 구현",
      infra: "🔧 인프라 & 배포",
      qa:    "🧪 검증 & 테스트",
      ops:   "🔔 운영 & 알림"
    };
    return titles[role] || (role + " 로그");
  }

  function emptyMsg() {
    return '<p class="empty">아직 기록이 없어요.<br>아래에서 추가해 보세요.</p>';
  }

  // ---------- 렌더링 ----------
  function render(role) {
    var container = $("#" + roleToView(role));
    if (!container) return;

    var entries = HubStore.byRole(role);
    var html = "";

    // 헤더 카드 + 추가 폼
    html += ""
      + '<div class="card">'
      +   '<h2 class="card-title">' + cardTitle(role) + '</h2>'
      +   '<form class="edit-form" data-role="' + role + '">'
      +     '<input type="date" name="date" required />'
      +     '<textarea name="text" placeholder="내용을 입력하세요…" required></textarea>'
      +     '<button type="submit" class="action">저장</button>'
      +   '</form>'
      + '</div>';

    // 기존 로그 리스트
    if (entries.length === 0) {
      html += '<div class="card">' + emptyMsg() + '</div>';
    } else {
      entries.forEach(function (e) {
        html += renderEntry(e, role);
      });
    }

    container.innerHTML = html;

    // 폼 이벤트 바인드
    bindForms();
  }

  function roleToView(role) {
    var m = ROLES.filter(function (r) { return r.key === role; });
    return m.length ? m[0].view : ("view-" + role);
  }

  function renderEntry(e, role) {
    var badge = '<span class="badge ' + role + '">' + role.toUpperCase() + '</span>';
    var d = e.date || "";
    var t = escapeHtml(e.text || "");
    var ts = e.ts || "";
    return ""
      + '<div class="card log-card" data-id="' + escapeHtml(e.id) + '" data-role="' + role + '">'
      +   '<div class="log-row">'
      +     '<div class="meta">' + badge + '<span class="date">' + d + '</span>'
      +       '<span class="ts">' + ts + '</span>'
      +       '<button class="del-btn" title="삭제">🗑</button>'
      +     '</div>'
      +     '<div class="body">' + t + '</div>'
      +   '</div>'
      + '</div>';
  }

  function bindForms() {
    document.querySelectorAll("form.edit-form").forEach(function (form) {
      form.removeEventListener("submit", onFormSubmit);
      form.addEventListener("submit", onFormSubmit);
    });
    // 삭제 버튼
    document.querySelectorAll("button.del-btn").forEach(function (btn) {
      btn.removeEventListener("click", onDelClick);
      btn.addEventListener("click", onDelClick);
    });
  }

  function onFormSubmit(e) {
    e.preventDefault();
    var form = e.target;
    var role = form.getAttribute("data-role");
    var date = form.querySelector('input[name="date"]').value;
    var text = form.querySelector('textarea[name="text"]').value.trim();
    if (!text) return;
    if (!date) date = new Date().toISOString().slice(0, 10);
    HubStore.add(role, text, date);
    // 초기화 + 리렌더
    form.reset();
    render(role);
  }

  function onDelClick(e) {
    var card = e.target.closest(".log-card");
    var id = card.getAttribute("data-id");
    var role = card.getAttribute("data-role");
    HubStore.remove(id);
    render(role);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---------- 초기화 ----------
  function init() {
    setupTabs();
    // 기본 탭: Dev
    var first = ROLES[1].key; // dev
    switchTo(first);
    // today 날짜 기본값 채우기 (가장 첫 폼)
    var firstDate = $("#view-dev input[type='date']");
    if (firstDate) firstDate.valueAsDate = new Date();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})(window);
