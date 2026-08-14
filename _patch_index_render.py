#!/usr/bin/env python3
"""index.html 인라인 스크립트의 _groupCoral 함수 추가 + renderCoral 스레드 그룹화 버전 교체
+ loadAll에 _coral 변수 할당 추가"""
import re

path = r"D:\develop\project\hermes-team-hub\index.html"
with open(path, encoding="utf-8") as f:
    html = f.read()

# 1. loadAll에 _coral 변수 추가 (const [kb, ag, cr] 부분)
old_loadall = "const [kb, ag, cr] = await Promise.all([getJSON('/api/kanban'), getJSON('/api/agents'), getJSON('/api/coral')]);\n        _kb = kb;"
new_loadall = "const [kb, ag, cr] = await Promise.all([getJSON('/api/kanban'), getJSON('/api/agents'), getJSON('/api/coral')]);\n        _kb = kb;\n        _coral = cr;"
if old_loadall in html:
    html = html.replace(old_loadall, new_loadall)
    print("LOADALL_CORAL_ASSIGNED")
else:
    print("WARN: loadAll pattern not found — checking if already modified")
    if "_coral = cr" in html:
        print("ALREADY_HAS_CORAL_ASSIGN")
    else:
        raise SystemExit("ERROR: loadAll coral assignment not found")

# 2. _groupCoral 함수 추가 + renderCoral 교체
old_render = '''    function renderCoral(){
      const list = (MOCK.coral||[]).filter(c=> coralFilter==="all" || c.agent===coralFilter);
      document.getElementById('coral-list').innerHTML = list.length
        ? list.slice().reverse().map(r=>'<div class=\\"row'+(r.isNew?' new':'')+'\\"'+badge(r.agent)+' <span style=\\"color:var(--muted);font-size:12px\\">'+esc(r.ts||'')+'</span><div style=\\"margin-top:4px\\">'+(r.content?esc(r.content):'(본문 없음)')+'</div></div>').join('')
        : '<div class=\\"empty\\">해당 역할 무전 없음</div>';
    }'''

new_render = '''    let _coral = [];
    function _groupCoral(list){
      const byThread = {};
      const order = [];
      (list || []).forEach(m => {
        const key = m.thread || "unknown";
        if (!byThread[key]) { byThread[key] = []; order.push(key); }
        byThread[key].push(m);
      });
      order.forEach(k => {
        byThread[k].sort((a, b) => {
          const ta = a.ts || "", tb = b.ts || "";
          return tb < ta ? -1 : tb > ta ? 1 : 0;
        });
      });
      const out = [];
      order.forEach(k => {
        out.push({ thread: k, name: byThread[k][0].threadName || k, msgs: byThread[k] });
      });
      return out;
    }
    function renderCoral(){
      const list = (_coral || MOCK.coral || []).filter(c => coralFilter === "all" || c.agent === coralFilter);
      const threads = _groupCoral(list);
      const ROLE_META = {
        pm:"🧄 마늘쿵야", dev:"🧅 양파쿵야", infra:"🥬 무시쿵야", qa:"🥗 샐러리쿵야",
        ops:"🍄 버섯쿵야", claude:"🤖 claude", default:"🤖 unknown"
      };
      const timeHeader = (ts) => { if (!ts) return ""; const p = String(ts).split(" "); return p[0] || ""; };
      const hourLabel = (ts) => { if (!ts) return ""; const m = String(ts).match(/\\d{2}:\\d{2}/); return m ? m[0] : ""; };
      const el = document.getElementById('coral-list');
      el.innerHTML = threads.length
        ? threads.map(t => {
            const head = '<div class="thread-header"><b>#' + esc(t.name || t.thread) + '</b>' +
              (t.msgs[0].isNew ? '<span class="new-tag">NEW</span>' : '') + '</div>';
            let html = ""; let lastAgent = null; let lastDate = "";
            t.msgs.slice().reverse().forEach(r => {
              const curDate = timeHeader(r.ts);
              const me = (r.agent === "ops");
              const meta = ROLE_META[r.agent] || r.agent;
              const urgent = ((r.content || "")).includes("URGENT");
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
          }).join('')
        : '<div class="empty">해당 역할 무전 없음</div>';
    }'''

if old_render in html:
    html = html.replace(old_render, new_render)
    print("RENDER_CORAL_REPLACED")
else:
    print("WARN: old renderCoral not found exactly — trying flexible match")
    # flexible match
    m = re.search(r'    function renderCoral\(\)\{[\s\S]*?}\s*', html)
    if m:
        html = html[:m.start()] + new_render + "\n    }" + html[m.end():]
        print("RENDER_CORAL_REPLACED_FLEXIBLE")
    else:
        raise SystemExit("ERROR: renderCoral block not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print("INDEX_HTML_PATCHED")
