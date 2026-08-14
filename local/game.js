// local/game.js — Canvas 무한 점프 러너 (Infra 안)
// 순수 정적: 이미지/오디오 에셋 0, 모든 그래픽은 Canvas 프리미티브로 절차적 드로잉.
// high score는 localStorage에 저장. 외부 의존성 0.
(function () {
  "use strict";
  var canvas = document.getElementById("game-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var W = canvas.width, H = canvas.height;

  var player = { x: 60, y: H - 40, w: 24, h: 24, vy: 0, onGround: true };
  var gravity = 0.7;
  var jump = -12;
  var obstacles = [];
  var speed = 4;
  var score = 0;
  var best = parseInt(localStorage.getItem("hub_game_best") || "0", 10);
  var running = false;
  var lastSpawn = 0;

  function reset() {
    player.y = H - 40; player.vy = 0; player.onGround = true;
    obstacles = []; score = 0; speed = 4; lastSpawn = 0;
  }

  function spawn() {
    var h = 20 + Math.random() * 30;
    obstacles.push({ x: W, y: H - h, w: 18, h: h });
  }

  function loop(ts) {
    if (!running) return;
    ctx.clearRect(0, 0, W, H);
    // ground
    ctx.fillStyle = "#2a2f3a";
    ctx.fillRect(0, H - 16, W, 16);

    // player
    ctx.fillStyle = "#c08bff";
    ctx.fillRect(player.x, player.y, player.w, player.h);

    // physics
    player.vy += gravity;
    player.y += player.vy;
    if (player.y >= H - 40) { player.y = H - 40; player.vy = 0; player.onGround = true; }

    // obstacles
    if (ts - lastSpawn > 900) { spawn(); lastSpawn = ts; }
    for (var i = obstacles.length - 1; i >= 0; i--) {
      var o = obstacles[i];
      o.x -= speed;
      ctx.fillStyle = "#7ed957";
      ctx.fillRect(o.x, o.y, o.w, o.h);
      // collision (AABB)
      if (player.x < o.x + o.w && player.x + player.w > o.x &&
          player.y < o.y + o.h && player.y + player.h > o.y) {
        gameOver(); return;
      }
      if (o.x + o.w < 0) obstacles.splice(i, 1);
    }

    score++;
    speed += 0.002;
    ctx.fillStyle = "#e6e6e6";
    ctx.font = "16px monospace";
    ctx.fillText("SCORE " + score, 10, 24);
    ctx.fillText("BEST " + best, 10, 44);

    requestAnimationFrame(loop);
  }

  function gameOver() {
    running = false;
    if (score > best) {
      best = score;
      localStorage.setItem("hub_game_best", String(best));
    }
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#ff7a90";
    ctx.font = "20px monospace";
    ctx.fillText("GAME OVER — SCORE " + score, 30, H / 2);
    ctx.fillStyle = "#e6e6e6";
    ctx.font = "13px monospace";
    ctx.fillText("스페이스로 재시작", 40, H / 2 + 24);
  }

  function start() {
    if (running) return;
    reset();
    running = true;
    requestAnimationFrame(loop);
  }

  document.addEventListener("keydown", function (e) {
    if (e.code === "Space") {
      if (!running && document.getElementById("view-game").classList.contains("active")) {
        start();
      } else if (player.onGround) {
        player.vy = jump; player.onGround = false;
      }
      e.preventDefault();
    }
  });

  // 게임 탭 활성화 시 첫 화면
  var gv = document.getElementById("view-game");
  if (gv) {
    var obs = new MutationObserver(function () {
      if (gv.classList.contains("active") && !running) {
        ctx.fillStyle = "#181b22"; ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = "#e6e6e6"; ctx.font = "14px monospace";
        ctx.fillText("스페이스로 시작", 40, H / 2);
      }
    });
    obs.observe(gv, { attributes: true, attributeFilter: ["class"] });
  }
})();
