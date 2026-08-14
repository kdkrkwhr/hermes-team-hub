// store.js — 공유 데이터 레이어 (localStorage)
// 모든 역할이 같은 키를 공유한다. 기록 구조: { id, role, date, text, ts }
(function (global) {
  "use strict";

  var KEY = "hermes-team-hub.logs.v1";

  function readAll() {
    try {
      var raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function writeAll(list) {
    localStorage.setItem(KEY, JSON.stringify(list));
  }

  function add(role, text, date) {
    var list = readAll();
    list.push({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      role: role,
      date: date || new Date().toISOString().slice(0, 10),
      text: text,
      ts: new Date().toISOString()
    });
    writeAll(list);
    return list;
  }

  function byRole(role) {
    return readAll()
      .filter(function (r) { return r.role === role; })
      .sort(function (a, b) { return a.ts < b.ts ? 1 : -1; });
  }

  function byDateDesc() {
    return readAll().sort(function (a, b) { return a.date < b.date ? 1 : -1; });
  }

  function remove(id) {
    writeAll(readAll().filter(function (r) { return r.id !== id; }));
  }

  global.HubStore = {
    add: add,
    byRole: byRole,
    byDateDesc: byDateDesc,
    remove: remove,
    all: readAll
  };
})(window);
