#!/usr/bin/env python3
"""app.js의 renderCoral 스레드 그룹화 + loadAll _coral 할당 동기화"""
import re

path = r"D:\develop\project\hermes-team-hub\js/app.js"
with open(path, encoding="utf-8") as f:
    js = f.read()

# 1. loadAll에 _coral 할당 추가 (기존에 없다면)
old_loadall = "_coral = cr;"
new_loadall_block = '_coral = cr;\n      _coral = cr;'  # placeholder

if "_coral = cr;" not in js:
    # loadAll에 cr 할당 추가
    m = re.search(r'var \[kb, ag, cr\] = await Promise\.all\(\[getJSON\("/api/kanban"\), getJSON\("/api/agents"\), getJSON\("/api/coral"\)\]\);\n\s+_coral = cr;', js)
    if m:
        print("SKIPPED: already has _coral = cr")
    else:
        # 더 넓은 패턴 시도
        m2 = re.search(r'getJSON\("/api/coral"\)[^\n]*\);\s*\n\s*\}', js)
        print("PATTERN2_FOUND" if m2 else "PATTERN2_NOT_FOUND")

# 2. _groupCoral 함수 + renderCoral 교체
old_render_pattern = r'function renderCoral\(\) \{[\s\S]*?\n  \}'

new_render = '''function _groupCoral(list) {
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
    function hourLabel(ts) { if (!ts) return ""; var m = String(ts).match(/\\d{2}:\\d{2}/); return m ? m[0] : ""; }
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
  }'''

m = re.search(old_render_pattern, js)
if m:
    js = js[:m.start()] + new_render + js[m.end():]
    print("APPJS_RENDER_CORAL_REPLACED")
else:
    print("ERROR: app.js renderCoral pattern not found")
    raise SystemExit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(js)
print("APPJS_PATCHED")
