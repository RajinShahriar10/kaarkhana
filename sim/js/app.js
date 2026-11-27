(function () {
'use strict';
const T = THREE, R = Math.random, $ = id => document.getElementById(id);

/* ---------- renderer / fixed camera ---------- */
const renderer = new T.WebGLRenderer({ canvas: $('c'), antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
const scene = new T.Scene();
scene.background = new T.Color(0xaeb3b8); scene.fog = new T.Fog(0xaeb3b8, 55, 120);
const cam = new T.PerspectiveCamera(38, 1, .1, 150);
const TG = new T.Vector3(0, 1.0, -.2), PITCH = 35 * Math.PI / 180, DIR = new T.Vector3(0, Math.sin(PITCH), Math.cos(PITCH));
function fit() {
  const w = innerWidth, h = innerHeight; renderer.setSize(w, h); cam.aspect = w / h;
  const hf = 2 * Math.atan(Math.tan(cam.fov * Math.PI / 360) * cam.aspect);
  const d = Math.max(20, 19.8 / Math.tan(hf / 2));
  cam.position.copy(TG).addScaledVector(DIR, d); cam.lookAt(TG); cam.updateProjectionMatrix();
}
addEventListener('resize', fit); fit();

/* ---------- helpers ---------- */
const M = (c, r = .6, m = 0, o = {}) => new T.MeshStandardMaterial(Object.assign({ color: c, roughness: r, metalness: m }, o));
function box(w, h, d, mat, x, y, z, p) { const m = new T.Mesh(new T.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; (p || scene).add(m); return m; }
function cyl(rt, rb, h, mat, x, y, z, p, seg = 16) { const m = new T.Mesh(new T.CylinderGeometry(rt, rb, h, seg), mat); m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; (p || scene).add(m); return m; }
function sph(r, mat, x, y, z, p, sy = 1) { const m = new T.Mesh(new T.SphereGeometry(r, 20, 14), mat); m.position.set(x, y, z); m.scale.y = sy; m.castShadow = true; (p || scene).add(m); return m; }
function tex(w, h, fn, rep) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; fn(c.getContext('2d'), w, h);
  const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.wrapS = t.wrapT = T.RepeatWrapping;
  if (rep) t.repeat.set(rep[0], rep[1]); t.anisotropy = 8; return t;
}
const UNIT = new T.CylinderGeometry(1, 1, 1, 10), _up = new T.Vector3(0, 1, 0), _d = new T.Vector3();
function limb(m, p, q, r) { _d.subVectors(q, p); const L = _d.length(); m.position.copy(p).addScaledVector(_d, .5); m.scale.set(r, L, r); m.quaternion.setFromUnitVectors(_up, _d.normalize()); }

/* ---------- materials / textures ---------- */
const floorTex = tex(512, 512, (g, w, h) => {
  g.fillStyle = '#8e9091'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 9000; i++) { const v = 105 + R() * 70 | 0; g.fillStyle = `rgba(${v},${v},${v + 2},.35)`; g.fillRect(R() * w, R() * h, 1 + R() * 2, 1 + R() * 2); }
  for (let i = 0; i < 16; i++) { const x = R() * w, y = R() * h, r = 20 + R() * 60, gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, 'rgba(55,55,55,.2)'); gr.addColorStop(1, 'rgba(55,55,55,0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r); }
  g.strokeStyle = 'rgba(40,40,40,.75)'; g.lineWidth = 3; g.strokeRect(0, 0, w, h);
}, [22, 6]);
const wallTex = tex(512, 512, (g, w, h) => { g.fillStyle = '#dcd8cc'; g.fillRect(0, 0, w, h); for (let i = 0; i < 6000; i++) { g.fillStyle = `rgba(${120 + R() * 90 | 0},${120 + R() * 90 | 0},${110 + R() * 90 | 0},.12)`; g.fillRect(R() * w, R() * h, 2, 2); } }, [12, 1]);
const mSteel = M(0x9aa0a6, .35, .85), mDark = M(0x1c1d20, .7, .3), mMach = M(0xd9d4c3, .45, .4), mTop = M(0xeceeec, .45), mWhite = M(0xf4f4f0, .6);

/* ---------- environment ---------- */
const floor = new T.Mesh(new T.PlaneGeometry(90, 24), M(0xffffff, .88, 0, { map: floorTex })); floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0, 2.5); floor.receiveShadow = true; scene.add(floor);
const wall = new T.Mesh(new T.PlaneGeometry(90, 14), M(0xffffff, .95, 0, { map: wallTex })); wall.position.set(0, 7, -9.5); wall.receiveShadow = true; scene.add(wall);
box(90, 2.6, .12, M(0x3f6659, .8), 0, 1.3, -9.42); box(90, .08, .14, M(0xe9e5d8, .8), 0, 2.64, -9.41);
for (const wx of [-25, -15, -5, 5, 15, 25]) {
  box(5, 2.6, .05, new T.MeshBasicMaterial({ color: 0xeaf4ff }), wx, 5.6, -9.4);
  for (let k = -2; k <= 2; k++) box(.07, 2.7, .08, mDark, wx + k * 1.25, 5.6, -9.36);
  box(5.1, .1, .1, mDark, wx, 4.28, -9.36); box(5.1, .1, .1, mDark, wx, 6.92, -9.36);
}
(function () {
  const c = tex(256, 256, g => { g.fillStyle = '#fff'; g.beginPath(); g.arc(128, 128, 120, 0, 7); g.fill(); g.strokeStyle = '#222'; g.lineWidth = 10; g.stroke(); g.lineWidth = 4; for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; g.beginPath(); g.moveTo(128 + Math.sin(a) * 100, 128 - Math.cos(a) * 100); g.lineTo(128 + Math.sin(a) * 112, 128 - Math.cos(a) * 112); g.stroke(); } g.lineWidth = 8; g.beginPath(); g.moveTo(128, 128); g.lineTo(178, 100); g.stroke(); g.lineWidth = 5; g.beginPath(); g.moveTo(128, 128); g.lineTo(118, 38); g.stroke(); });
  const m = new T.Mesh(new T.CircleGeometry(.6, 32), new T.MeshBasicMaterial({ map: c })); m.position.set(0, 7.6, -9.35); scene.add(m);
  const b = tex(1024, 200, (g, w, h) => { g.fillStyle = '#143d8f'; g.fillRect(0, 0, w, h); g.fillStyle = '#fff'; g.font = 'bold 84px Segoe UI,Arial'; g.textAlign = 'center'; g.fillText('QUALITY FIRST · ZERO DEFECTS', w / 2, 125); });
  const bm = new T.Mesh(new T.PlaneGeometry(7, 1.36), new T.MeshBasicMaterial({ map: b })); bm.position.set(0, 3.9, -9.35); scene.add(bm);
})();
function rack(x) {
  const g = new T.Group(); g.position.set(x, 0, -8.7); scene.add(g);
  for (const px of [-1.4, 1.4]) for (const pz of [-.4, .4]) box(.08, 3.6, .08, M(0x2b57a3, .5, .3), px, 1.8, pz, g);
  for (let l = 0; l < 3; l++) { box(3, .06, 1, M(0xe07b1d, .5, .3), 0, .6 + l * 1.1, 0, g); for (let k = 0; k < 6; k++) cyl(.2, .2, .9, M([0x1b2a4a, 0xe9e9e6, 0x7a1f2b, 0x1f5a3a, 0x3a7bbf, 0xd9a21b][(k + l) % 6], .95), -1.2 + k * .48, .83 + l * 1.1, 0, g).rotation.x = Math.PI / 2; }
}
rack(-21.5); rack(21.5);
const yl = new T.Mesh(new T.PlaneGeometry(70, .14), M(0xf2c200, .8)); yl.rotation.x = -Math.PI / 2; yl.position.set(0, .01, 3.1); scene.add(yl);
for (let i = 0; i < 380; i++) { const m = new T.Mesh(new T.PlaneGeometry(.03 + R() * .12, .01), M([0xffffff, 0x1b2a4a, 0xb02020, 0xd9a21b][i % 4], 1)); m.rotation.x = -Math.PI / 2; m.rotation.z = R() * 6; m.position.set((R() - .5) * 40, .012, -3 + R() * 6.5); scene.add(m); }
scene.add(new T.HemisphereLight(0xffffff, 0x6d6f72, .62));
const sun = new T.DirectionalLight(0xfff1dc, 1.05); sun.position.set(-9, 22, 11); sun.castShadow = true;
sun.shadow.mapSize.set(3072, 3072); Object.assign(sun.shadow.camera, { left: -26, right: 26, top: 12, bottom: -12, near: 1, far: 60 }); sun.shadow.bias = -.0005; scene.add(sun);
for (const lx of [-16, -8, 0, 8, 16]) { const p = new T.PointLight(0xfff6e8, .55, 24, 1.4); p.position.set(lx, 5, 1); scene.add(p); }
const fans = [];
for (const fx of [-13.2, -4.4, 4.4, 13.2]) {
  const g = new T.Group(); g.position.set(fx, 6.4, -1); scene.add(g); cyl(.03, .03, 1.2, mDark, 0, .6, 0, g); cyl(.2, .2, .15, mDark, 0, 0, 0, g);
  const bl = new T.Group(); g.add(bl); for (let k = 0; k < 4; k++) { const a = new T.Group(); a.rotation.y = k * Math.PI / 2; bl.add(a); box(1.25, .025, .22, M(0xb78a5a, .6), .85, -.05, 0, a).rotation.z = .08; }
  fans.push(bl);
}

/* ---------- line configuration ---------- */
const NAMES = ['Shoulder Join', 'Collar Attach', 'Placket Make', 'Placket Attach', 'Sleeve Attach', 'Side Seam', 'Sleeve Hem', 'Bottom Hem', 'Buttonhole & Button', 'Bartack & QC'];
const N = NAMES.length, SLOW = 4;                         // 10 stations; ST5 (index 4) is the slow one
const TIMES = [4.2, 4.4, 4.0, 4.3, 8.6, 4.1, 3.8, 3.9, 3.7, 3.6];   // seconds per garment
const XS = Array.from({ length: N }, (_, i) => -13.5 + i * 3);            // machine x (flow: left -> right, operators face +x)
const ZM = -.35, ZN = -.05, ZW = -.15, SRC_X = -17.2, SNK_X = 17.6;
for (const x of XS) { box(3.2, .1, .5, M(0xcfcfcf, .5, .3), x, 5.9, -.3); for (const z of [-.45, -.15]) box(3.0, .04, .12, new T.MeshBasicMaterial({ color: 0xffffff }), x, 5.83, z); }
const VEST = M(0xf07d12, .85), SHIRT = [0x9db7d8, 0x2d2f36, 0x8fb0d8, 0xd8d8d8, 0x2b3a55, 0x9db7d8, 0x5a7d6b, 0xc9b79c, 0x7b8cc4, 0x3a3f4f], SKIN = [0xc68642, 0xe0ac86, 0x8d5524, 0xb9774e, 0xd9a07a, 0x8d5524, 0xe0ac86, 0xc68642, 0xb9774e, 0xd9a07a], SCARF = { 1: 0xd9c7a3, 4: 0x8a3b55, 7: 0x3f5f7a };

/* ---------- operators (face +x, seated, vest + mask) ---------- */
function mkWorker(i, p) {
  const g = new T.Group(); g.position.set(-.8, 0, ZW); g.rotation.y = Math.PI / 2; p.add(g);
  const shirt = M(SHIRT[i], .85), sk = M(SKIN[i], .7), pants = M(0x2a2f3d, .9);
  const w = { g, bl: 0, hw: 0, off: i * 1.7, sp: i === SLOW ? 4.6 : 3, sh: {}, up: {}, fo: {}, hand: {}, x0: XS[i] - .8, z0: ZW };
  const torso = new T.Mesh(new T.CapsuleGeometry(.2, .36, 6, 14), VEST); torso.scale.z = .75; torso.position.y = .92; torso.castShadow = true; g.add(torso);
  box(.4, .14, .26, pants, 0, .58, 0, g); cyl(.07, .075, .045, shirt, 0, 1.28, .01, g); cyl(.045, .05, .1, sk, 0, 1.31, .01, g);
  for (const s of [-1, 1]) {
    const th = new T.Mesh(UNIT, pants), sh = new T.Mesh(UNIT, pants); th.castShadow = sh.castShadow = true; g.add(th, sh);
    limb(th, new T.Vector3(s * .12, .58, 0), new T.Vector3(s * .13, .56, .42), .075); limb(sh, new T.Vector3(s * .13, .56, .42), new T.Vector3(s * .13, .08, .46), .06); box(.1, .06, .26, mDark, s * .13, .04, .52, g);
  }
  box(.5, .05, .46, mDark, 0, .5, -.02, g); box(.46, .3, .04, mDark, 0, .8, -.27, g); cyl(.03, .03, .45, mSteel, 0, .25, -.02, g, 8); box(.6, .03, .06, mDark, 0, .03, -.02, g); box(.06, .03, .6, mDark, 0, .03, -.02, g);
  const head = new T.Group(); head.position.set(0, 1.46, .02); g.add(head); sph(.118, sk, 0, 0, 0, head, 1.12);
  for (const s of [-1, 1]) { sph(.014, mDark, s * .042, .02, .105, head); box(.04, .007, .01, mDark, s * .045, .05, .108, head); }
  const mk = sph(.115, M(0xf2f6fa, .8), 0, -.05, .05, head); mk.scale.set(1, .5, .85);
  if (SCARF[i]) { const sc = M(SCARF[i], .9); sph(.133, sc, 0, .015, -.012, head, 1.12); const f = sph(.15, sc, 0, -.12, -.06, head); f.scale.set(.95, 1.2, .8); }
  else { const hr = new T.Mesh(new T.SphereGeometry(.127, 20, 14, 0, Math.PI * 2, 0, Math.PI * .5), M(0x111111, .6)); hr.position.set(0, .035, -.01); hr.scale.y = 1.1; hr.castShadow = true; head.add(hr); }
  w.head = head;
  for (const s of [-1, 1]) {
    w.sh[s] = new T.Vector3(s * .25, 1.17, 0); sph(.07, shirt, s * .25, 1.17, 0, g);
    w.up[s] = new T.Mesh(UNIT, shirt); w.fo[s] = new T.Mesh(UNIT, shirt); w.hand[s] = sph(.05, sk, 0, 0, 0, g); w.up[s].castShadow = w.fo[s].castShadow = true; g.add(w.up[s], w.fo[s]);
  }
  return w;
}
const _s = new T.Vector3(), _t = new T.Vector3(), _e = new T.Vector3(), _pole = new T.Vector3(), _h = new T.Vector3(), _tg = new T.Vector3();
function ik(w, s, tgt) {
  const A = .42, B = .46; _s.copy(w.sh[s]); _t.subVectors(tgt, _s); const L = Math.min(_t.length(), (A + B) * .995); _t.normalize();
  const ang = Math.acos(Math.max(-1, Math.min(1, (A * A + L * L - B * B) / (2 * A * L))));
  _pole.set(s * .6, -1, 0); _pole.addScaledVector(_t, -_pole.dot(_t)).normalize();
  _e.copy(_s).addScaledVector(_t, Math.cos(ang) * A).addScaledVector(_pole, Math.sin(ang) * A); _h.copy(_s).addScaledVector(_t, L);
  limb(w.up[s], _s, _e, .058); limb(w.fo[s], _e, _h, .045); w.hand[s].position.copy(_h);
}
function animWorker(w, st, dt, t) {
  const act = st.state === 'work' || st.state === 'pick' ? 1 : 0; w.bl += (act - w.bl) * Math.min(1, dt * 4);
  w.hw += ((st.hold ? 1 : 0) - w.hw) * Math.min(1, dt * 9);
  const b = w.bl, ph = t * w.sp + w.off, id = t * .6 + w.off, x = XS[st.i], sew = st.sewing ? 1 : .3, fz = st.state === 'work' ? (st.prog / st.dur - .5) * .2 : 0;
  for (const s of [-1, 1]) {
    const aX = x - .22 + .03 * Math.sin(ph * 1.3 + s) * sew, aY = 1.08 + .012 * Math.sin(ph * 2.1) * sew, aZ = (s < 0 ? .08 : -.3) + fz + .035 * Math.sin(ph * .7 + s * 2) * sew;
    const iX = x - .3 + .012 * Math.sin(id + s), iZ = s < 0 ? .05 : -.4;
    let X = iX + (aX - iX) * b, Y = .98 + (aY - .98) * b, Z = iZ + (aZ - iZ) * b;
    if (s < 0 && st.hold) { const p = st.hold.g.position; X += (p.x - .05 - X) * w.hw; Y += (p.y + .05 - Y) * w.hw; Z += (p.z + .08 - Z) * w.hw; }
    ik(w, s, _tg.set(-(Z - w.z0), Y, X - w.x0));
  }
  w.head.rotation.x = .06 + .3 * b + .03 * Math.sin(ph * .7);
  w.head.rotation.y = (1 - b) * (.55 * Math.sin(id * .8) + .2 * Math.sin(id * 2.3)) + b * .09 * Math.sin(ph * .3) + (st.hold ? -.35 * w.hw : 0);
  w.g.position.y = .004 * Math.sin(t * 1.6 + w.off);
}

/* ---------- loose cut garments (not folded, wrinkled) ---------- */
const PAL = [0x1b2a4a, 0xe9e9e6, 0x7a1f2b, 0x1f5a3a, 0x262626, 0x3a7bbf, 0xd9a21b, 0x5b2a6e, 0xc0c0bc], gmat = {};
const bodyTex = tex(256, 173, (g, w, h) => {
  const X = x => (x + .4) / .8 * w, Y = y => (.27 - y) / .54 * h; g.fillStyle = '#fff'; g.beginPath(); g.moveTo(X(-.2), Y(.27)); g.quadraticCurveTo(X(0), Y(.12), X(.2), Y(.27));
  [[.36, .19], [.4, 0], [.32, -.02], [.25, .04], [.25, -.27], [-.25, -.27], [-.25, .04], [-.32, -.02], [-.4, 0], [-.36, .19]].forEach(p => g.lineTo(X(p[0]), Y(p[1]))); g.closePath(); g.fill();
  g.strokeStyle = 'rgba(0,0,0,.2)'; g.lineWidth = 2; g.stroke(); g.beginPath(); g.moveTo(X(0), Y(.16)); g.lineTo(X(0), Y(.02)); g.stroke();
});
const sleeveTex = tex(128, 160, (g, w, h) => { g.fillStyle = '#fff'; g.beginPath(); g.moveTo(10, 20); g.lineTo(w - 10, 8); g.lineTo(w - 26, h - 12); g.lineTo(26, h - 6); g.closePath(); g.fill(); g.strokeStyle = 'rgba(0,0,0,.2)'; g.lineWidth = 2; g.stroke(); });
function wrinkled(w, h, amp) {
  const g = new T.PlaneGeometry(w, h, 16, 12), sd = R() * 10; g.rotateX(-Math.PI / 2); const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), e = Math.max(Math.abs(x) / (w / 2), Math.abs(z) / (h / 2)); p.setY(i, amp * (Math.sin(x * 11 + sd) + .8 * Math.sin(z * 14 + sd * 1.7) + .6 * Math.sin((x + z) * 7 + sd * .6)) + .03 * e * e * Math.sin(sd * 3 + x * 5) + (R() - .5) * .003); }
  g.computeVertexNormals(); return g;
}
const bodyGeo = Array.from({ length: 7 }, () => wrinkled(.8, .54, .01 + R() * .01)), sleeveGeo = Array.from({ length: 5 }, () => wrinkled(.3, .38, .008 + R() * .008));
const gm = (c, map) => { const k = c + '' + (map === bodyTex); return gmat[k] || (gmat[k] = M(c, .96, 0, { map, alphaTest: .5, side: T.DoubleSide })); };
let gid = 0;
function mkGarment(parent) {
  const g = new T.Group(), c = PAL[gid++ % PAL.length], n = 2 + (R() * 2 | 0);
  for (let k = 0; k < n; k++) { const m = new T.Mesh(bodyGeo[R() * bodyGeo.length | 0], gm(c, bodyTex)); m.position.set((R() - .5) * .14, .012 + k * .014, (R() - .5) * .12); m.rotation.y = (R() - .5) * 1.6; m.castShadow = m.receiveShadow = true; g.add(m); }
  for (let k = 0; k < 2; k++) { const m = new T.Mesh(sleeveGeo[R() * sleeveGeo.length | 0], gm(c, sleeveTex)); m.position.set((R() - .5) * .3, .02 + k * .02, (R() - .5) * .25); m.rotation.y = R() * 6.28; m.castShadow = m.receiveShadow = true; g.add(m); }
  g.rotation.y = R() * 6.28; (parent || scene).add(g); return { g, slot: -1 };
}

/* ---------- stations ---------- */
const stations = [], mHead = M(0x1a2a60, .5);
box(35, .05, .85, mTop, 0, .9, .525); box(35, .04, .04, mSteel, 0, .3, .92);
for (let k = 0; k < 12; k++) box(.05, .88, .05, mSteel, -16.5 + k * 3, .44, .92);
function buildStation(i) {
  const g = new T.Group(); g.position.x = XS[i]; scene.add(g);
  box(1.7, .05, .9, mTop, .2, .9, -.35, g); box(1.66, .08, .03, mSteel, .2, .83, -.78, g);
  for (const lx of [-.62, 1.0]) for (const lz of [-.76, .08]) box(.05, .88, .05, mSteel, lx, .44, lz, g);
  box(.3, .3, .3, M(0x2d4f7a, .6), 1.4, .15, -.55, g); // bin under next table gap
  const mg = new T.Group(); mg.position.set(0, .925, ZM); mg.rotation.y = Math.PI / 2; g.add(mg);
  box(.78, .015, .42, mSteel, 0, 0, 0, mg); box(.7, .09, .2, mMach, 0, .055, 0, mg); box(.16, .42, .2, mMach, .28, .27, 0, mg); box(.6, .13, .2, mMach, .06, .47, 0, mg); box(.14, .2, .18, mMach, -.26, .38, 0, mg); box(.05, .02, .12, mSteel, -.3, .1, 0, mg);
  const lb = new T.Mesh(new T.PlaneGeometry(.12, .045), new T.MeshBasicMaterial({ map: tex(128, 48, c => { c.fillStyle = '#16284f'; c.fillRect(0, 0, 128, 48); c.fillStyle = '#fff'; c.font = 'italic bold 30px Arial'; c.textAlign = 'center'; c.fillText('brother', 64, 35); }) })); lb.position.set(-.337, .4, 0); lb.rotation.y = -Math.PI / 2; mg.add(lb);
  const needle = new T.Group(); needle.position.set(-.3, 0, 0); mg.add(needle); cyl(.012, .012, .26, mSteel, 0, .3, 0, needle, 8); cyl(.003, .003, .1, mSteel, 0, .14, 0, needle, 6);
  cyl(.01, .01, .22, mSteel, -.34, .28, 0, mg, 8); box(.05, .03, .07, mSteel, -.34, .1, 0, mg);
  const wheel = new T.Group(); wheel.position.set(.45, .47, 0); mg.add(wheel); cyl(.075, .075, .03, mDark, 0, 0, 0, wheel, 20).rotation.z = Math.PI / 2; box(.035, .13, .012, mSteel, 0, 0, 0, wheel);
  box(.03, .02, .03, new T.MeshBasicMaterial({ color: 0xfff0b0 }), -.22, .38, .11, mg);
  box(.25, .14, .15, mDark, .4, -.125, 0, mg); const belt = new T.Mesh(UNIT, M(0x111111, .9)); mg.add(belt); limb(belt, new T.Vector3(.45, .47, 0), new T.Vector3(.4, -.1, 0), .008);
  // thread stand with cones + tray, instruction sheet on frame pole
  cyl(.11, .11, .015, mDark, .3, .932, -.7, g); cyl(.008, .008, .5, mSteel, .3, 1.18, -.7, g, 6);
  cyl(.03, .045, .12, M([0xeeeeee, 0xb02020][i % 2], .9), .3, 1.1, -.7, g); cyl(.03, .045, .12, M(0xeeeeee, .9), .3, 1.3, -.7, g);
  cyl(.02, .02, 1.0, mSteel, .95, 1.4, -.8, g, 8); box(1.3, .03, .03, mSteel, .45, 1.9, -.8, g);
  const sh = new T.Mesh(new T.PlaneGeometry(.34, .44), new T.MeshBasicMaterial({ map: tex(128, 160, c => { c.fillStyle = '#f4f6fa'; c.fillRect(0, 0, 128, 160); c.fillStyle = '#6a7a99'; for (let y = 14; y < 150; y += 9) c.fillRect(10, y, 40 + R() * 70, 3); }) })); sh.position.set(.7, 1.62, -.77); g.add(sh);
  const slow = i === SLOW;
  const sg = new T.Mesh(new T.PlaneGeometry(1.5, .38), new T.MeshBasicMaterial({ map: tex(384, 96, (c, w, h) => { c.fillStyle = slow ? '#b42318' : '#143d8f'; c.fillRect(0, 0, w, h); c.fillStyle = '#fff'; c.fillRect(0, 0, 86, h); c.fillStyle = slow ? '#b42318' : '#143d8f'; c.font = 'bold 44px Segoe UI,Arial'; c.textAlign = 'center'; c.fillText('ST' + (i + 1), 43, 63); c.fillStyle = '#fff'; c.font = 'bold ' + (NAMES[i].length > 14 ? 25 : 31) + 'px Segoe UI,Arial'; c.fillText(NAMES[i], 235, 60); }) }));
  sg.position.set(.2, 2.55, -.85); g.add(sg);
  const w = mkWorker(i, g);
  const st = { i, g, q: [], slots: [], cur: null, hold: null, prog: 0, dur: TIMES[i], state: 'idle', wait: R(), sewing: false, rate: 1, rtg: 1, rt: 0, stall: 0, stallAt: 0, w, needle, wheel, mg, ph: 0 };
  stations.push(st); return st;
}
for (let i = 0; i < N; i++) buildStation(i);
// cutting table (source) and finished crate (sink)
box(1.6, .06, 1.2, mTop, SRC_X, .9, .1); for (const a of [-.7, .7]) for (const b of [-.45, .65]) box(.05, .88, .05, mSteel, SRC_X + a, .44, b);
for (let k = 0; k < 6; k++) { const d = mkGarment(); d.g.position.set(SRC_X - .4 + (k % 3) * .4, .93 + (k >> 2) * .06, -.1 + (k % 2) * .4); }
box(1.5, .1, 1.3, M(0x2a2d33, .6), SNK_X, .3, 0); for (const sx of [-1, 1]) for (const sz of [-1, 1]) cyl(.07, .07, .05, mDark, SNK_X + sx * .6, .06, sz * .5, null, 12);
for (const [w, d, x, z] of [[1.5, .05, 0, .65], [1.5, .05, 0, -.65], [.05, 1.3, .75, 0], [.05, 1.3, -.75, 0]]) box(w, .6, d, M(0x1d5fa8, .55), SNK_X + x, .65, z);
// back-aisle bins heaped with garments + loose pieces lying on the transfer table
for (let k = 0; k < 8; k++) {
  const bx = -13.3 + k * 3.8; box(1.1, .6, .8, M([0x2b6cb0, 0x2f855a, 0xc05621][k % 3], .6), bx, .3, -1.9);
  for (let n = 0; n < 5; n++) { const d = mkGarment(); d.g.position.set(bx + (R() - .5) * .7, .6 + n * .05, -1.9 + (R() - .5) * .45); }
}
for (let k = 0; k < 22; k++) { const d = mkGarment(); d.g.position.set(-15.5 + k * 1.5 + R() * .5, .94 + R() * .02, .42 + R() * .4); }

/* ---------- garment flow ---------- */
const slotPos = (i, k) => new T.Vector3(XS[i] - 1.1 + (k % 2) * .5 + (R() - .5) * .1, .94 + (k >> 2) * .045, .3 + ((k >> 1) % 2) * .34 + (R() - .5) * .08);
const fabricPos = i => new T.Vector3(XS[i] - .1, 1.03, -.2);
function alloc(st) { let k = 0; while (st.slots[k]) k++; st.slots[k] = true; return k; }
const tweens = [];
function move(b, to, dur, arc, done) { tweens.push({ b, from: b.g.position.clone(), to, t: 0, dur, arc, done, ry: b.g.rotation.y, ryt: b.g.rotation.y + (R() - .5) * 1.0 }); }
function stepTweens(dt) {
  for (let n = tweens.length - 1; n >= 0; n--) {
    const w = tweens[n]; w.t = Math.min(1, w.t + dt / w.dur); const e = w.t * w.t * (3 - 2 * w.t);
    w.b.g.position.lerpVectors(w.from, w.to, e); w.b.g.position.y += Math.sin(Math.PI * w.t) * w.arc; w.b.g.rotation.y = w.ry + (w.ryt - w.ry) * e;
    if (w.t >= 1) { tweens.splice(n, 1); w.done && w.done(); }
  }
}
let running = false, stopped = false, speed = 1, simT = 0, anim = 0, spawnT = 0, nextSpawn = 2, finished = 0;
function spawn() {
  const b = mkGarment(), st = stations[0], k = alloc(st); b.slot = k; b.g.position.set(SRC_X + .3, 1.0, .1);
  move(b, new T.Vector3(XS[0] - 2.2, .95, .55), .8, .12, () => move(b, slotPos(0, k), .9, .06, () => st.q.push(b)));
}
const seed = [5, 3, 3, 2, 6, 2, 2, 1, 1, 1];
seed.forEach((n, i) => { const st = stations[i]; for (let k = 0; k < n; k++) { const b = mkGarment(), s = alloc(st); b.slot = s; b.g.position.copy(slotPos(i, s)); st.q.push(b); } });
function updateSim(dt) {
  simT += dt; spawnT += dt; if (spawnT >= nextSpawn) { spawnT = 0; nextSpawn = 3.3 + R() * 2.6; spawn(); }
  stepTweens(dt);
  for (const st of stations) {
    if (!st.cur) {
      if (st.wait > 0) st.wait -= dt;
      else if (st.q.length) {
        const b = st.q.shift(); st.cur = b; st.state = 'pick'; st.slots[b.slot] = false; st.hold = b;
        move(b, fabricPos(st.i), .7 + R() * .25, .1, () => { st.hold = null; st.state = 'work'; st.prog = 0; st.dur = TIMES[st.i] * (.8 + R() * .45); st.stall = R() < .12 ? 1.2 + R() * 2.8 : 0; st.stallAt = st.dur * (.2 + R() * .6); });
      } else st.state = 'idle';
    } else if (st.state === 'work') {
      if (st.stall > 0 && st.prog >= st.stallAt) { st.stall -= dt; st.sewing = false; }
      else {
        st.rt -= dt; if (st.rt <= 0) { st.rt = .5 + R() * 1.6; st.rtg = R() < .2 ? .15 : .8 + R() * .5; }
        st.rate += (st.rtg - st.rate) * Math.min(1, dt * 3); st.prog += dt * st.rate; st.sewing = true;
      }
      const f = st.cur.g.position; f.z = -.2 + (st.prog / st.dur - .5) * .2; f.y = 1.03 + (st.sewing ? .003 * Math.sin(simT * 45) : 0);
      if (st.prog >= st.dur) {
        const b = st.cur; st.cur = null; st.state = 'idle'; st.sewing = false; st.wait = .2 + R() * .7; st.hold = b;
        if (st.i < N - 1) { const nx = stations[st.i + 1], k = alloc(nx); b.slot = k; move(b, new T.Vector3(XS[st.i] + .5, .95, .5), .35, .15, () => { st.hold = null; move(b, slotPos(nx.i, k), .55 + R() * .2, .04, () => nx.q.push(b)); }); }
        else move(b, new T.Vector3(SNK_X + (R() - .5) * .8, .72 + Math.min(finished, 14) * .035, (R() - .5) * .7), 1.1, .5, () => { st.hold = null; finished++; });
      }
    }
  }
}
function updateVisuals(dt, t) {
  fans.forEach(f => f.rotation.y += dt * 6);
  for (const st of stations) { st.ph += dt * (st.sewing ? 60 * st.rate : 0); st.needle.position.y = .035 * Math.sin(st.ph); st.wheel.rotation.x = st.ph * .3; st.mg.position.z = ZM + (st.sewing ? (R() - .5) * .002 : 0); animWorker(st.w, st, dt, t); }
}
/* ---------- controls ---------- */
function play() { if (running || stopped) return; running = true; $('start').classList.add('hidden'); $('hud').classList.remove('hidden'); }
$('play').onclick = play;
addEventListener('keydown', e => {
  if (e.key === 'Escape' && running && !stopped) { stopped = true; running = false; $('stop').classList.remove('hidden'); }
  else if (e.key === 'Enter' || e.key === ' ') play();
  else if (e.key === 'r' || e.key === 'R') location.reload();
  else if (e.key === 'h' || e.key === 'H') $('hud').classList.toggle('hidden');
  else if ('123'.includes(e.key)) speed = +e.key;
});
let last = performance.now(), ct = 0;
(function loop(now) {
  requestAnimationFrame(loop); let dt = Math.min((now - last) / 1000, .05); last = now;
  if (!stopped) { dt *= speed; anim += dt; if (running) { updateSim(dt); ct += dt; if (ct > .25) { ct = 0; $('out').textContent = finished; $('clock').textContent = String(simT / 60 | 0).padStart(2, '0') + ':' + String(simT % 60 | 0).padStart(2, '0'); } } updateVisuals(dt, anim); }
  renderer.render(scene, cam);
})(last);
})();
