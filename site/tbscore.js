/* Territory battle contribution scoring, shared by the Contribution and Effectiveness pages.
   TBScore.clean(settings, phases) -> {phases, weights};  TBScore.scoreTB(tbData, settings, tbIndex) -> {out: Map(id -> scores), ...} */
(function () {
  const median = a => { const v = a.filter(x => x != null).sort((x, y) => x - y), n = v.length; return n ? (n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2) : null; };
  const quant = (a, q) => { const v = a.filter(x => x != null).sort((x, y) => x - y); if (!v.length) return null; const i = (v.length - 1) * q, lo = Math.floor(i); return v[lo] + (v[Math.min(lo + 1, v.length - 1)] - v[lo]) * (i - lo); };
  const COMP = [["dep", "Deployment", "--c-dep"], ["cm", "Combat missions", "--c-cm"], ["spec", "Special missions", "--c-spec"], ["plat", "Platoons", "--c-plat"]];
  const DEFAULT_WEIGHTS = { dep: 25, cm: 25, spec: 25, plat: 25 };
  function clean(s, nPh) {
    const all = Array.from({ length: nPh }, (_, i) => i + 1);
    return {
      phases: (Array.isArray(s?.phases) && s.phases.length ? s.phases : all).map(Number).filter(p => p >= 1 && p <= nPh).sort((a, b) => a - b),
      weights: Object.fromEntries(COMP.map(([k]) => [k, Math.max(0, +(s?.weights?.[k] ?? DEFAULT_WEIGHTS[k]) || 0)])),
    };
  }
  function scoreTB(data, S, i) {
    const tbs = data.tbs, players = data.players;
    const t = tbs[i], inc = S.phases.filter(p => p <= t.phases), w = S.weights;
    const rows = players.map(p => ({ p, r: p.detail[String(i)] })).filter(x => x.r);
    // references from the whole guild in this TB
    const fullGP = {}, specRef = {};
    for (let ph = 1; ph <= t.phases; ph++) {
      const xs = rows.map(x => x.r.phases.find(y => y.p === ph)).filter(Boolean);
      fullGP[ph] = median(xs.filter(x => x.dep && x.gp > 0).map(x => x.gp)) || null;
      const anySpec = xs.some(x => x.spec > 0);
      specRef[ph] = anySpec ? Math.max(1, Math.round(quant(xs.filter(x => x.spec > 0).map(x => x.spec), 0.5))) : null;
    }
    const platRef = Math.max(1, quant(rows.map(x => x.r.platoons), 0.75) || 1);
    const out = new Map();
    rows.forEach(({ p, r }) => {
      const ownFull = Math.max(0, ...r.phases.filter(x => x.dep).map(x => x.gp));
      const ph = {};
      r.phases.forEach(x => {
        const ref = ownFull || fullGP[x.p];
        const dep = x.dep ? 100 : x.gp > 0 && ref ? Math.min(100, x.gp / ref * 100) : 0;
        const cm = Math.min(100, x.waves / (t.max_waves[x.p - 1] || 1) * 100);
        const spec = specRef[x.p] ? Math.min(100, x.spec / specRef[x.p] * 100) : null;
        const parts = [["dep", dep], ["cm", cm], ["spec", spec]].filter(([, v]) => v != null);
        const wsum = parts.reduce((a, [k]) => a + w[k], 0);
        ph[x.p] = { dep, cm, spec, waves: x.waves, score: wsum ? parts.reduce((a, [k, v]) => a + w[k] * v, 0) / wsum : null };
      });
      const incPh = inc.map(n => ph[n]).filter(Boolean);
      const maxW = inc.reduce((a, n) => a + (t.max_waves[n - 1] || 0), 0);
      const avg = k => { const v = incPh.map(x => x[k]).filter(v => v != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
      const comp = {
        dep: incPh.length ? avg("dep") : null,
        cm: maxW ? Math.min(100, incPh.reduce((a, x) => a + x.waves, 0) / maxW * 100) : null,
        spec: avg("spec"),
        plat: Math.min(100, r.platoons / platRef * 100),
      };
      const parts = COMP.map(([k]) => [k, comp[k]]).filter(([, v]) => v != null);
      const wsum = parts.reduce((a, [k]) => a + w[k], 0);
      const overall = wsum ? parts.reduce((a, [k, v]) => a + w[k] * v, 0) / wsum : 0;
      // each part's share of the overall score, for the stacked bars
      const share = Object.fromEntries(parts.map(([k, v]) => [k, wsum ? w[k] * v / wsum : 0]));
      out.set(p.id, { overall, comp, share, ph, platoons: r.platoons });
    });
    return { out, inc, platRef, specRef, fullGP };
  }
  window.TBScore = { scoreTB, clean, median, quant, COMP };
})();
