const _log = [];
function FakeEl(id){ this.id=id; this.dataset={}; this._html=''; this.textContent=''; }
FakeEl.prototype.querySelectorAll = function(){ return []; };
FakeEl.prototype.addEventListener = function(){};
Object.defineProperty(FakeEl.prototype, 'innerHTML', {
  set: function(v){ this._html=v; _log.push([this.id, v?v.length:0, v||'']); },
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
var console = { log: function(){}, error: function(...a){ process.stdout.write('[err] '+a.join(' ')+'\n'); } };
global._log = _log; global._els = _els;
process.on('unhandledRejection', e=>{ process.stdout.write('[unhandledRejection] '+(e&&e.message||e)+'\n'); });

const fs = require('fs');
const html = fs.readFileSync(process.argv[2] || 'index.html','utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
try { eval(js); } catch(e){ process.stdout.write('[INIT THREW] '+e.message+'\n'); }
(async()=>{
  try { await loadAll(); } catch(e){ process.stdout.write('[LOADALL THREW] '+e.message+'\n'); }
  process.stdout.write('=== EMPTY/SHORT renders (len<10) ===\n');
  _log.filter(x=>x[1]<10).forEach(x=>process.stdout.write('  '+x[0]+' len='+x[1]+'\n'));
  process.stdout.write('=== ALL renders len ===\n');
  _log.forEach(x=>process.stdout.write('  '+x[0]+' = '+x[1]+'\n'));
})();
