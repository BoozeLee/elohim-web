/* ghost-field.js — the phosphor field behind the ghost.
 *
 * A small canvas particle system: data-motes rising out of the monitor
 * stack, with a persistence trail so they read as light on a phosphor
 * tube rather than as dots on a dark background.
 *
 * Deliberately NOT the ghost. The ghost is SVG (crisp, themeable, free).
 * This is the atmosphere around it, and it is the only thing on the page
 * allowed to run a JS loop.
 *
 * Rules it obeys, from the design contract:
 *   - starts after first paint (never blocks the D-J21 boot gate)
 *   - pauses when off-screen or when the tab is hidden
 *   - DPR capped at 2
 *   - transform/opacity only; no layout reads inside the loop
 *   - honours prefers-reduced-motion by drawing one static composed frame
 */
(function () {
  "use strict";

  var TAU = Math.PI * 2;

  function GhostField(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d", { alpha: true });
    this.motes = [];
    this.w = 0;
    this.h = 0;
    this.dpr = 1;
    this.running = false;
    this.reduced = false;
    this.last = 0;
    this.visible = true;
    this.paused = false;
    this.tint = { r: 232, g: 184, b: 96 };
  }

  GhostField.prototype.setTheme = function (tint) {
    this.tint = tint;
  };

  /* Size the backing store to CSS pixels × DPR. Called on init and on
   * resize only — never from the animation loop. */
  GhostField.prototype.resize = function () {
    var rect = this.canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = Math.max(1, Math.round(rect.width));
    this.h = Math.max(1, Math.round(rect.height));
    this.dpr = dpr;
    this.canvas.width = Math.round(this.w * dpr);
    this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.seed();
  };

  /* Motes are born in a band along the bottom (the monitor stack) and
   * rise, fading as they go. Density scales with area but is capped, so a
   * 4K display does not turn into soup. */
  GhostField.prototype.seed = function () {
    var area = this.w * this.h;
    var target = Math.min(140, Math.max(36, Math.round(area / 9000)));
    this.motes.length = 0;
    for (var i = 0; i < target; i++) {
      this.motes.push(this.spawn(1));
    }
  };

  GhostField.prototype.spawn = function (initial) {
    return {
      x: Math.random() * this.w,
      /* Birth is biased low so motes appear to come out of the monitors
       * rather than materialise in mid-air. `initial` staggers the first
       * frame so the field is already populated on paint. */
      y: initial ? Math.random() * this.h : this.h + Math.random() * 40,
      r: 0.6 + Math.random() * 1.8,
      vy: 6 + Math.random() * 22,
      /* Lateral drift is a slow sine, not a random walk: motes should
       * look carried, not shaken. */
      phase: Math.random() * TAU,
      sway: 4 + Math.random() * 14,
      life: initial ? Math.random() : 0,
      span: 5 + Math.random() * 7,
    };
  };

  GhostField.prototype.step = function (dt) {
    var m, i;
    for (i = 0; i < this.motes.length; i++) {
      m = this.motes[i];
      m.life += dt;
      m.y -= m.vy * dt;
      m.phase += dt * 0.6;
      m.x += Math.cos(m.phase) * m.sway * dt;
      if (m.y < -20 || m.life > m.span) this.motes[i] = this.spawn(0);
    }
  };

  /* Phosphor persistence: instead of clearing, lay down a translucent
   * wash so each mote leaves a short tail. This is the single detail that
   * makes it read as a CRT instead of as confetti. */
  GhostField.prototype.paint = function (fade) {
    var ctx = this.ctx;
    var t = this.tint;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = "rgba(0,0,0," + fade + ")";
    ctx.fillRect(0, 0, this.w, this.h);
    ctx.globalCompositeOperation = "lighter";

    for (var i = 0; i < this.motes.length; i++) {
      var m = this.motes[i];
      var k = m.life / m.span;
      /* Fade in over the first 12% of life, out over the last 45%. */
      var a = k < 0.12 ? k / 0.12 : 1 - (k - 0.12) / 0.88;
      a = Math.max(0, Math.min(1, a)) * 0.55;
      ctx.fillStyle =
        "rgba(" + t.r + "," + t.g + "," + t.b + "," + a.toFixed(3) + ")";
      ctx.beginPath();
      ctx.arc(m.x, m.y, m.r, 0, TAU);
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";
  };

  GhostField.prototype.clear = function () {
    this.ctx.clearRect(0, 0, this.w, this.h);
  };

  GhostField.prototype.frame = function (now) {
    if (!this.running) return;
    var dt = this.last ? Math.min((now - this.last) / 1000, 0.05) : 0.016;
    this.last = now;
    if (!this.paused && this.visible) {
      this.step(dt);
      this.paint(dt > 0 ? Math.min(0.28, dt * 3.2) : 0.2);
    }
    this.raf = requestAnimationFrame(this.frame.bind(this));
  };

  GhostField.prototype.start = function () {
    if (this.running) return;
    this.running = true;
    this.last = 0;
    this.raf = requestAnimationFrame(this.frame.bind(this));
  };

  GhostField.prototype.stop = function () {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = null;
  };

  /* Reduced motion gets ONE composed frame — motes frozen mid-flight, the
   * field still populated, the still image still handsome. Not an empty
   * canvas; a good poster. */
  GhostField.prototype.freeze = function () {
    this.resize();
    this.clear();
    for (var i = 0; i < this.motes.length; i++) {
      var m = this.motes[i];
      m.y = this.h * (0.25 + 0.65 * Math.random());
      m.life = m.span * 0.4;
    }
    this.paint(1);
  };

  GhostField.prototype.attach = function () {
    var self = this;
    this.reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    var onResize = function () {
      self.resize();
      if (self.reduced) self.freeze();
    };
    window.addEventListener("resize", onResize, { passive: true });

    /* Stop burning frames when the stage is scrolled away or the tab is
     * backgrounded. On a laptop this is the difference between a page that
     * feels alive and one that heats the machine. */
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(
        function (entries) {
          self.visible = entries[0].isIntersecting;
        },
        { threshold: 0.01 }
      ).observe(this.canvas);
    }
    document.addEventListener("visibilitychange", function () {
      self.paused = document.hidden;
      if (!document.hidden) self.last = 0;
    });

    this.resize();
    if (this.reduced) {
      this.freeze();
      return;
    }
    /* After first paint, so this never competes with boot. */
    if ("requestIdleCallback" in window) {
      requestIdleCallback(function () { self.start(); }, { timeout: 1200 });
    } else {
      setTimeout(function () { self.start(); }, 60);
    }
  };

  window.GhostField = GhostField;
})();
