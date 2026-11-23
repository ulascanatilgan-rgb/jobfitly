/* One-line gibbon animation, based on the user's hand-over-hand reference.
   No image downloads, no canvas dependencies, no mouse interactions.
   Both hands cycle continuously: one bears weight while the other reaches.
   The black rope flexes locally under whichever hand is carrying the load. */
(() => {
  'use strict';
  const band = document.getElementById('monkey-rope-band');
  const traveler = document.getElementById('gibbon-traveler');
  const svg = document.getElementById('gibbon-art');
  const rope = document.getElementById('gibbon-rope');
  const ropePath = document.getElementById('gibbon-rope-path');
  if (!band || !traveler || !svg || !rope || !ropePath) return;

  const parts = {};
  ['left-arm', 'right-arm', 'left-hand', 'right-hand', 'torso',
   'head', 'muzzle', 'eye', 'left-leg', 'right-leg', 'hip'].forEach(name => {
    parts[name] = document.getElementById('gibbon-' + name);
  });
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const cycleSeconds = 3.55;
  const travelSeconds = 24;
  const smooth = x => {
    const v = Math.max(0, Math.min(1, x));
    return v * v * (3 - 2 * v);
  };
  const pos = v => Number(v).toFixed(2);
  const point = (x, y) => pos(x) + ' ' + pos(y);
  let start = performance.now();
  let wasHidden = false;
  let width = 0;
  let scale = 1;
  let baseY = 22;
  let ropeWidth = 42;

  function resize() {
    width = band.clientWidth || window.innerWidth;
    scale = traveler.clientWidth / 220;
    baseY = band.clientHeight > 132 ? 21 : 18;
    ropeWidth = Math.max(33, 50 * scale);
    rope.setAttribute('viewBox', '0 0 ' + width + ' ' + band.clientHeight);
  }
  window.addEventListener('resize', resize, {passive: true});
  resize();

  // Grip: p 0..0.5 supports weight and slips backwards relative to the
  // forward-moving body; p 0.5..1 releases, swings ahead, and re-grips.
  function handPose(p, shift, phase, sway) {
    const front = 190;
    const back = front - shift;
    if (p < 0.5) {
      return {
        x: front - shift * (p / 0.5),
        y: 23.3 + Math.sin(phase * 2 * Math.PI) * 0.7,
        weight: 1
      };
    }
    const travel = (p - 0.5) / 0.5;
    const reach = smooth(travel);
    const height = Math.sin(Math.PI * travel);
    const weight = smooth((travel - 0.81) / 0.19);
    return {
      x: back + (front - back) * reach + Math.sin(Math.PI * travel) * 7,
      y: 23.3 + 48 * height + 4 * Math.sin(phase * Math.PI * 2 + sway),
      weight
    };
  }

  function limbPath(sx, sy, hx, hy, handed) {
    const dx = hx - sx, dy = hy - sy;
    const outer = handed === 'left' ? -4.5 : 4.5;
    const curve = handed === 'left' ? -13 : 12;
    // Paired flowing strokes recall the continuous contour in the source GIF,
    // rather than cartoon-looking straight stick limbs.
    return 'M' + point(sx - 3, sy) +
      ' C' + point(sx + dx * 0.33 + curve, sy - 11) +
      ' ' + point(hx - dx * 0.34 + curve * 0.45, hy + dy * 0.30 + 12) +
      ' ' + point(hx, hy) +
      ' C' + point(hx + outer, hy - 4.2) +
      ' ' + point(hx + outer * 1.5, hy - 1.9) +
      ' ' + point(hx + 1, hy + 1.2) +
      ' C' + point(hx - dx * 0.32 + curve * 0.4 + 4.5, hy + dy * 0.30 + 18) +
      ' ' + point(sx + dx * 0.3 + curve + 5.5, sy - 3.8) +
      ' ' + point(sx + 4, sy + 3.2);
  }

  function draw(el, path) { if (el) el.setAttribute('d', path); }

  function render(timestamp) {
    // When the landing page is visible, do not spend CPU animating hidden UI.
    if (document.hidden || document.getElementById('app')?.classList.contains('hidden')) {
      wasHidden = true;
      requestAnimationFrame(render);
      return;
    }
    if (wasHidden) { start = timestamp - ((timestamp - start) % (travelSeconds * 1000)); wasHidden = false; }

    const reduced = motion.matches;
    const elapsed = reduced ? travelSeconds * 0.42 : (timestamp - start) / 1000;
    const progress = (elapsed % travelSeconds) / travelSeconds;
    const left = -220 + progress * (width + 425);
    const phase = (elapsed % cycleSeconds) / cycleSeconds;
    const travelSpeed = (width + 425) / travelSeconds;
    const shift = Math.max(46, Math.min(116, travelSpeed * cycleSeconds * 0.5));
    const leftHand = handPose(phase, shift, phase, 0);
    const rightHand = handPose((phase + 0.5) % 1, shift, phase, 1.2);

    const swing = reduced ? 0.25 : Math.sin(phase * Math.PI * 2);
    const buoyancy = reduced ? 0 : Math.sin(phase * Math.PI * 4) * 2.3;
    const bx = 120 + swing * 10.5;
    const by = 82 + (reduced ? 0 : Math.cos(phase * Math.PI * 2) * 4 + buoyancy * 0.35);

    // Small local deflection (4–6 px) follows the weight transferred from
    // the supporting hand to the next, not an entire-screen sag.
    const strength = leftHand.weight + rightHand.weight;
    const gripLocal = strength
      ? (leftHand.x * leftHand.weight + rightHand.x * rightHand.weight) / strength
      : 130;
    const gripGlobal = left + gripLocal * scale;
    const sag = reduced ? 3.8 : 4.1 + 1.25 * Math.cos(phase * 2 * Math.PI);
    let path = 'M' + point(0, baseY);
    const count = Math.max(12, Math.ceil(width / 24));
    for (let i = 1; i <= count; i++) {
      const x = width * i / count;
      const distance = (x - gripGlobal) / (ropeWidth + 12);
      const depth = sag * Math.exp(-distance * distance * 0.95);
      path += ' L' + point(x, baseY + depth);
    }
    ropePath.setAttribute('d', path);

    // The grip points follow the dipped rope, so the fingers remain on it.
    const ropeAt = x => {
      const d = (left + x * scale - gripGlobal) / (ropeWidth + 12);
      return (baseY + sag * Math.exp(-0.95 * d * d)) / scale;
    };
    [leftHand, rightHand].forEach(hand => {
      const ropeHeight = ropeAt(hand.x);
      hand.y += ropeHeight - 23.3;
    });
    const lsx = bx - 12, rsx = bx + 12, shouldersY = by - 1;
    draw(parts['left-arm'], limbPath(lsx, shouldersY, leftHand.x, leftHand.y, 'left'));
    draw(parts['right-arm'], limbPath(rsx, shouldersY, rightHand.x, rightHand.y, 'right'));
    draw(parts['left-hand'],
      'M' + point(leftHand.x - 3.9, leftHand.y + 1) +
      ' Q' + point(leftHand.x - 8, leftHand.y - 5.1) +
      ' ' + point(leftHand.x - 1.7, leftHand.y - 6) +
      ' Q' + point(leftHand.x + 4.2, leftHand.y - 4.5) +
      ' ' + point(leftHand.x + 4.7, leftHand.y - 0.8));
    draw(parts['right-hand'],
      'M' + point(rightHand.x - 3.9, rightHand.y + 0.8) +
      ' Q' + point(rightHand.x - 7.5, rightHand.y - 5.3) +
      ' ' + point(rightHand.x - 1.8, rightHand.y - 6) +
      ' Q' + point(rightHand.x + 4.7, rightHand.y - 4.3) +
      ' ' + point(rightHand.x + 5.5, rightHand.y + 0.9));

    // Gibbon silhouette: small head, tapered torso, very long curved arms,
    // bent knees and hook-shaped toes. No cartoon ears, round eyes or tail.
    const headY = by - 20, eyeX = bx + 8.1;
    draw(parts.head,
      'M' + point(bx - 12, headY + 10) +
      ' C' + point(bx - 19, headY + 5) +
      ' ' + point(bx - 17, headY - 11) +
      ' ' + point(bx - 4, headY - 14) +
      ' C' + point(bx + 5, headY - 16) +
      ' ' + point(bx + 13, headY - 7) +
      ' ' + point(bx + 12, headY + 2) +
      ' Q' + point(bx + 11, headY + 9) +
      ' ' + point(bx + 5, headY + 13) +
      ' Q' + point(bx - 5, headY + 16) +
      ' ' + point(bx - 12, headY + 10));
    draw(parts.muzzle,
      'M' + point(bx + 9,headY + 1) +
      ' Q' + point(bx + 20,headY + 3) +
      ' ' + point(bx + 16,headY + 9) +
      ' Q' + point(bx + 11,headY + 12) +
      ' ' + point(bx + 6.5,headY + 9));
    if (parts.eye) {
      parts.eye.setAttribute('cx', pos(eyeX));
      parts.eye.setAttribute('cy', pos(headY - 1.8));
    }

    draw(parts.torso,
      'M' + point(bx - 12,by - 1) +
      ' C' + point(bx - 28,by + 11) +
      ' ' + point(bx - 24,by + 28) +
      ' ' + point(bx - 7,by + 33) +
      ' Q' + point(bx + 6,by + 39) +
      ' ' + point(bx + 16,by + 27) +
      ' C' + point(bx + 24,by + 16) +
      ' ' + point(bx + 17,by + 1) +
      ' ' + point(bx + 12,by - 2));
    const kick = reduced ? 1 : Math.sin(phase * 2 * Math.PI - 0.7) * 12;
    const kneeX1 = bx + 20 + kick * 0.4, kneeY1 = by + 52 - Math.abs(kick) * 0.12;
    const footX1 = bx + 38 + kick * 0.72, footY1 = by + 57 + kick * 0.22;
    const kneeX2 = bx - 17 - kick * 0.3, kneeY2 = by + 50 + Math.abs(kick) * 0.08;
    const footX2 = bx - 29 - kick * 0.67, footY2 = by + 61 - kick * 0.18;
    draw(parts['right-leg'],
      'M' + point(bx + 8,by + 30) +
      ' C' + point(bx + 28,by + 28) +
      ' ' + point(kneeX1 + 6,kneeY1 - 8) +
      ' ' + point(kneeX1,kneeY1) +
      ' Q' + point(footX1 - 6,footY1 + 3) +
      ' ' + point(footX1,footY1) +
      ' Q' + point(footX1 + 5,footY1 - 3) +
      ' ' + point(footX1 + 7,footY1 - 8) +
      ' Q' + point(footX1 + 2,footY1 - 7) +
      ' ' + point(footX1,footY1));
    draw(parts['left-leg'],
      'M' + point(bx - 5,by + 29) +
      ' C' + point(bx - 13,by + 35) +
      ' ' + point(kneeX2 + 5,kneeY2 - 12) +
      ' ' + point(kneeX2,kneeY2) +
      ' Q' + point(footX2 + 4,footY2 - 3) +
      ' ' + point(footX2,footY2) +
      ' Q' + point(footX2 - 6,footY2 - 2) +
      ' ' + point(footX2 - 6,footY2 - 7));
    draw(parts.hip,
      'M' + point(bx - 6,by + 32) +
      ' Q' + point(bx + 3,by + 40) +
      ' ' + point(bx + 13,by + 33));
    traveler.style.transform = 'translate3d(' + pos(reduced ? width * 0.40 : left) + 'px,0,0)';
    if (!reduced) requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();