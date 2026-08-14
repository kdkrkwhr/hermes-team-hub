const _log = [];
function FakeEl(id){ this.id=id; this.dataset={}; this._html=''; this.textContent=''; }
FakeEl.prototype.querySelectorAll = function(){ return []; };
FakeEl.prototype.addEventListener = function(){};
Object.defineProperty(FakeEl.prototype, 'innerHTML', {
  set: function(v){ this._html=v; _log.push(this.id + ' <- len ' + (v?v.length:0)); },
  get: function(){ return this._html; }
});
var _els = {};
var document = {
  getElementById: function(id){ if(!_els[id]) _els[id]=new FakeEl(id); return _els[id]; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(){}
};
var window = {};
var location = { hostname: 'kdkrkwhr.github.io' };
var setInterval = function(){ return 0; };
function fetch(){ return Promise.reject(new Error('no endpoint')); }
var urlparse = function(){ return {}; };
var localStorage = { getItem: function(){return null;}, setItem: function(){} };
var console = { log: function(...a){ process.stdout.write('[log] '+a.join(' ')+'\n'); }, error: function(...a){ process.stdout.write('[err] '+a.join(' ')+'\n'); } };
global._log = _log; global._els = _els;
process.on('unhandledRejection', e=>{ process.stdout.write('[unhandledRejection] '+(e&&e.message||e)+'\n'); });

const fs = require('fs');
const html = fs.readFileSync(process.argv[2] || 'index.html','utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
try { eval(js); } catch(e){ process.stdout.write('[INIT THREW] '+e.message+'\n'+e.stack+'\n'); }
(async()=>{
  try { await loadAll(); } catch(e){ process.stdout.write('[LOADALL THREW] '+e.message+'\n'+e.stack+'\n'); }
  process.stdout.write('=== innerHTML sets ===\n');
  _log.forEach(x=>process.stdout.write(x+'\n'));
  process.stdout.write('pm-kanban-list len: ' + ((_els['pm-kanban-list']||{})._html||'').length + '\n');
  process.stdout.write('dev-kanban-list len: ' + ((_els['dev-kanban-list']||{})._html||'').length + '\n');
})();
