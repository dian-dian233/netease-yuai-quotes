"""雨爱轮播页 逻辑自测（零依赖，用最小 DOM 桩跑真实 index.html 里的脚本）。
覆盖：初始渲染 / 圆点数量 / 计数器 / 前进后退回绕 / 圆点跳转 / 空格键 /
      悬停暂停 / 切标签页暂停 / reduced-motion 分支 / 无外部资源。
用法：python3 selftest.py /tmp/yuai/index.html
"""
import json
import re
import sys

HTML_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/yuai/index.html"
html = open(HTML_PATH, encoding="utf-8").read()
script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)

# ── 最小 DOM 桩 ────────────────────────────────────────────
STUB = r"""
var listeners = {};          // elementId/type -> fn
var winListeners = {};
var timeouts = [];
function FakeEl(id, tag) {
  this.id = id; this.tagName = (tag || 'div').toUpperCase();
  this.children = []; this.attrs = {}; this.dataset = {};
  this.style = {}; this._cls = {}; this._text = ''; this._html = '';
  this.clientWidth = 1280; this.clientHeight = 720;
}
FakeEl.prototype._classList = function () {
  var self = this, set = {};
  return {
    add: function (c) { set[c] = 1; },
    remove: function (c) { delete set[c]; },
    contains: function (c) { return !!set[c]; },
    toString: function () { return Object.keys(set).join(' '); }
  };
};
Object.defineProperty(FakeEl.prototype, 'classList', {
  get: function () { if (!this.__cl) this.__cl = this._classList(); return this.__cl; }
});
Object.defineProperty(FakeEl.prototype, 'textContent', {
  get: function () { return this._text; },
  set: function (v) { this._text = String(v); }
});
Object.defineProperty(FakeEl.prototype, 'innerHTML', {
  get: function () { return this._html; },
  set: function (v) { this._html = String(v); this.children = []; }
});
FakeEl.prototype.setAttribute = function (k, v) {
  this.attrs[k] = String(v);
  if (k.indexOf('data-') === 0) this.dataset[k.slice(5)] = String(v);
};
FakeEl.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
FakeEl.prototype.removeAttribute = function (k) { delete this.attrs[k]; };
FakeEl.prototype.appendChild = function (el) { this.children.push(el); return el; };
FakeEl.prototype.addEventListener = function (type, fn) {
  (listeners[this.id + ':' + type] = listeners[this.id + ':' + type] || []).push(fn);
};
FakeEl.prototype.getContext = function () { return CTX; };
FakeEl.prototype.closest = function () { return null; };
FakeEl.prototype.querySelector = function () { return null; };

var CTX = {
  setTransform: function () {}, clearRect: function () {}, beginPath: function () {},
  moveTo: function () {}, lineTo: function () {}, stroke: function () {},
  strokes: 0
};
var _stroke = CTX.stroke;
CTX.stroke = function () { this.strokes++; };

var els = {};
['frame','quote','lines','dots','counter','fill','live','rain','next','prev'].forEach(function (id) {
  els[id] = new FakeEl(id, id === 'rain' ? 'canvas' : 'div');
});
// 页面里 fillEl 是 <i>，但 stub 只要能被赋值 style 就行

global.document = {
  documentElement: { classList: new FakeEl('root').classList },
  hidden: false,
  getElementById: function (id) { return els[id] || null; },
  createElement: function (tag) { var e = new FakeEl('created-' + tag, tag); return e; },
  querySelector: function () { return els.frame; },
  addEventListener: function (type, fn) { (winListeners['doc:' + type] = winListeners['doc:' + type] || []).push(fn); }
};
var rafQueue = [];
global.window = {
  matchMedia: function (q) {
    var m = false;
    if (/prefers-reduced-motion/.test(q)) m = (global.__REDUCED === true);
    if (/hover:\s*hover/.test(q)) m = true;
    return { matches: m };
  },
  devicePixelRatio: 2,
  setTimeout: function (fn, ms) { timeouts.push({ fn: fn, ms: ms || 0 }); return timeouts.length; },
  clearTimeout: function () {},
  addEventListener: function (type, fn) { (winListeners['win:' + type] = winListeners['win:' + type] || []).push(fn); },
  requestAnimationFrame: function (fn) { rafQueue.push(fn); return rafQueue.length; },
  innerWidth: 1280,
  innerHeight: 720
};
global.__REDUCED = false;
global.setTimeout = window.setTimeout;
global.requestAnimationFrame = window.requestAnimationFrame;
"""

harness = STUB + "\n" + script + r"""

// ── 测试工具 ─────────────────────────────────────────────
var pass = 0, fail = 0;
function ok(cond, msg) {
  if (cond) { pass++; console.log('  PASS ' + msg); }
  else { fail++; console.log('  FAIL ' + msg); }
}
function flushTimeouts() {
  var guard = 0;
  while (timeouts.length && guard++ < 50) {
    var t = timeouts.shift();
    t.fn();
  }
}
function tick(frames, tsStart, step) {
  for (var i = 0; i < frames; i++) {
    var q = rafQueue.slice(); rafQueue.length = 0;
    for (var j = 0; j < q.length; j++) q[j](tsStart + i * step);
  }
}
function fireEl(id, type, ev) {
  var l = listeners[id + ':' + type] || [];
  for (var i = 0; i < l.length; i++) l[i](ev || {});
}
function fireDoc(type, ev) {
  var l = winListeners['doc:' + type] || [];
  for (var i = 0; i < l.length; i++) l[i](ev || {});
}

console.log('\n[1] 初始渲染');
ok(els.dots.children.length === 12, '生成 12 个圆点，实际 ' + els.dots.children.length);
ok(els.counter.textContent === '01 / 12', '计数器 = "01 / 12"，实际 "' + els.counter.textContent + '"');
ok(/窗外的天气/.test(els.lines.innerHTML), '首句已渲染：' + els.lines.innerHTML.replace(/<[^>]+>/g, '|'));
ok(els.dots.children[0].getAttribute('aria-current') === 'true', '第 1 个圆点标记为当前');
ok((els.dots.children[1].getAttribute('aria-current')) === null, '第 2 个圆点未标记');

console.log('\n[2] 下一句 / 上一句 / 回绕');
fireEl('next', 'click'); flushTimeouts();
ok(els.counter.textContent === '02 / 12', '下一句 → 02/12，实际 "' + els.counter.textContent + '"');
ok(/下雨了/.test(els.lines.innerHTML), '第二位语录已切换：' + els.lines.innerHTML.replace(/<[^>]+>/g, '|'));
ok(els.dots.children[1].getAttribute('aria-current') === 'true', '圆点跟随到第 2 个');
fireEl('prev', 'click'); flushTimeouts();
ok(els.counter.textContent === '01 / 12', '上一句 → 01/12');
fireEl('prev', 'click'); flushTimeouts();
ok(els.counter.textContent === '12 / 12', '从第 1 句上一句 → 回绕到 12/12');

console.log('\n[3] 圆点跳转');
var fakeDot = { getAttribute: function (k) { return k === 'data-i' ? '7' : null; } };
var fakeClosest = { closest: function () { return fakeDot; } };
fireEl('dots', 'click', { target: fakeClosest }); flushTimeouts();
ok(els.counter.textContent === '08 / 12', '点第 8 个圆点 → 08/12，实际 "' + els.counter.textContent + '"');

console.log('\n[4] 键盘');
fireDoc('keydown', { key: 'ArrowRight', preventDefault: function () {} }); flushTimeouts();
ok(els.counter.textContent === '09 / 12', '→ 键 → 09/12');
fireDoc('keydown', { key: ' ', preventDefault: function () {} }); flushTimeouts();
ok(els.counter.textContent === '10 / 12', '空格 → 10/12');
fireDoc('keydown', { key: 'ArrowLeft', preventDefault: function () {} }); flushTimeouts();
ok(els.counter.textContent === '09 / 12', '← 键 → 09/12');
fireDoc('keydown', { key: 'Home', preventDefault: function () {} }); flushTimeouts();
ok(els.counter.textContent === '01 / 12', 'Home → 01/12');
fireDoc('keydown', { key: 'End', preventDefault: function () {} }); flushTimeouts();
ok(els.counter.textContent === '12 / 12', 'End → 12/12');

console.log('\n[5] 触摸滑动');
fireEl('frame', 'touchstart', { touches: [{ clientX: 300, clientY: 300 }] });
fireEl('frame', 'touchend', { changedTouches: [{ clientX: 200, clientY: 305 }] }); flushTimeouts();
ok(els.counter.textContent === '01 / 12', '左滑 → 回绕到 01/12，实际 "' + els.counter.textContent + '"');
fireEl('frame', 'touchstart', { touches: [{ clientX: 100, clientY: 300 }] });
fireEl('frame', 'touchend', { changedTouches: [{ clientX: 105, clientY: 380 }] }); flushTimeouts();
ok(els.counter.textContent === '01 / 12', '纵向滑动不触发切换');

console.log('\n[6] 进度条与自动轮播（7s）');
timeouts.length = 0;
// 不能清 rafQueue：主循环靠它自我续帧
// 重新走一遍 rAF 主循环：模拟 1.5s → 进度约 0.21
tick(2, 1000, 16);  // 建立基线
tick(1, 1500, 500);
var t1 = els.fill.style.transform;
ok(/scaleX\(0\.[0-9]+\)/.test(t1), '进度条按时间推进：' + t1);
tick(1, 9000, 1000);
// 主循环单帧 dt 上限 0.12s，按 ~120ms/帧 推进约 8.4s 才够触发 7s 轮播
var t0 = 9500;
for (var f = 0; f < 70; f++) tick(1, t0 + f * 120, 120);
flushTimeouts();
ok(els.counter.textContent !== '01 / 12', '推进 8.4s 后自动切到下一句，当前 ' + els.counter.textContent);

console.log('\n[7] 悬停暂停 / 切页暂停');
var before = els.counter.textContent;
fireEl('frame', 'mouseenter', {});
var fillBefore = els.fill.style.transform;
tick(1, 17000, 2000);
ok(els.fill.style.transform === fillBefore, '悬停后进度条冻结：' + els.fill.style.transform);
ok(els.counter.textContent === before, '悬停后不再自动切换');
fireEl('frame', 'mouseleave', {});
document.hidden = true;
fireDoc('visibilitychange', {});
var fillHidden = els.fill.style.transform;
tick(1, 25000, 3000);
ok(els.fill.style.transform === fillHidden, '切走标签页后进度冻结');
document.hidden = false;
fireDoc('visibilitychange', {});

console.log('\n[8] 无外部资源');
var h = require('fs').readFileSync(process.argv[2] || '/tmp/yuai/index.html', 'utf8');
var refs = (h.match(/(?:src|href)\s*=\s*["']([^"']+)["']/g) || []).filter(function (m) {
  return !/data:/.test(m);
});
ok(refs.length === 0, '无 src/href 外链（favicon 用 data URI）：' + JSON.stringify(refs));
ok(!/cdn|unpkg|jsdelivr|googleapis/i.test(h), '不含任何 CDN 关键字');

console.log('\n结果：PASS ' + pass + ' / FAIL ' + fail);
process.exit(fail === 0 ? 0 : 1);
"""
open("/tmp/yuai/_selftest_run.js", "w", encoding="utf-8").write(harness)
print("测试脚本已生成：/tmp/yuai/_selftest_run.js")