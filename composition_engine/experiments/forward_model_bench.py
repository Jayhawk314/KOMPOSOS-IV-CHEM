"""Offline forward-model accuracy benchmark (leave-one-out).

Research harness to find what actually reduces formation-energy MAE before
touching production. Compares predictor variants on the SAME 179 KNOWN_EF
anchors under identical strict leave-one-out (held-out material removed by name
AND by near-identical composition, so duplicates like GeO2/GeO2_glass cannot leak
the answer).

Current production: IDW(k=5) over RAW composition vectors (every element an
orthogonal axis), MAE ~0.47 eV/atom. Hypothesis: a chemically-meaningful,
scale-invariant feature space (or a simple regularized model on physical
descriptors) pulls truly-similar materials together and cuts the error.

Run: python -m composition_engine.experiments.forward_model_bench
"""

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from composition_engine.formation_energy import KNOWN_EF
from composition_engine.parser import ELEMENT_TABLE, ELEMENT_ORDER, parse_formula

ANIONS = {"O", "S", "F", "Cl", "Br", "N", "I", "Se", "Te"}


def norm_frac(comp):
    tot = sum(comp.values()) or 1.0
    return {e: a / tot for e, a in comp.items()}


def frac_vector(comp):
    """Normalized element-fraction vector (scale-invariant)."""
    v = np.zeros(len(ELEMENT_ORDER))
    f = norm_frac(comp)
    for e, a in f.items():
        if e in ELEMENT_TABLE:
            v[ELEMENT_ORDER.index(e)] = a
    return v


def phys_features(comp):
    """Composition-weighted physical descriptors (Magpie-lite)."""
    f = norm_frac(comp)
    props = {"electronegativity": [], "group": [], "period": [],
             "atomic_mass": [], "ionic_radius": [], "common_oxidation": [],
             "atomic_number": []}
    weights = []
    for e, a in f.items():
        ed = ELEMENT_TABLE.get(e)
        if ed is None:
            continue
        weights.append(a)
        props["electronegativity"].append(ed.electronegativity)
        props["group"].append(ed.group)
        props["period"].append(ed.period)
        props["atomic_mass"].append(ed.atomic_mass)
        props["ionic_radius"].append(ed.ionic_radius)
        props["common_oxidation"].append(ed.common_oxidation)
        props["atomic_number"].append(ed.atomic_number)
    w = np.array(weights)
    if w.sum() == 0:
        return np.zeros(18)
    w = w / w.sum()
    feats = []
    for key in ("electronegativity", "group", "period", "atomic_mass",
                "ionic_radius", "common_oxidation", "atomic_number"):
        x = np.array(props[key])
        mean = float((w * x).sum())
        var = float((w * (x - mean) ** 2).sum())
        feats.append(mean)
        feats.append(var ** 0.5)
    # extra chemistry signals
    anion_frac = sum(a for e, a in f.items() if e in ANIONS)
    metal_frac = sum(a for e, a in f.items()
                     if e in ELEMENT_TABLE and ELEMENT_TABLE[e].electronegativity < 2.0)
    n_el = len([e for e in comp if e in ELEMENT_TABLE])
    ens = [ELEMENT_TABLE[e].electronegativity for e in comp if e in ELEMENT_TABLE]
    en_gap = (max(ens) - min(ens)) if len(ens) > 1 else 0.0
    feats += [anion_frac, metal_frac, float(n_el), en_gap]
    return np.array(feats)


def dominant_anion(comp):
    f = norm_frac(comp)
    best, ba = None, 0.0
    for e, a in f.items():
        if e in ANIONS and a > ba:
            best, ba = e, a
    return best


# ── Build dataset ───────────────────────────────────────────────────────────
DATA = []
for k in KNOWN_EF:
    comp = parse_formula(k.formula)
    DATA.append({
        "name": k.name, "formula": k.formula, "ef": k.ef_per_atom,
        "comp": comp, "fnorm": norm_frac(comp),
        "raw": np.array([comp.get(e, 0.0) for e in ELEMENT_ORDER]),
        "frac": frac_vector(comp), "phys": phys_features(comp),
        "anion": dominant_anion(comp),
    })

N = len(DATA)


def loo_mask(i, comp_dedup=True):
    """Indices to KEEP for fold i (strict LOO: drop self + near-duplicate comps)."""
    fi = DATA[i]["fnorm"]
    keep = []
    for j in range(N):
        if j == i:
            continue
        if comp_dedup:
            fj = DATA[j]["fnorm"]
            elems = set(fi) | set(fj)
            d = sum((fi.get(e, 0) - fj.get(e, 0)) ** 2 for e in elems) ** 0.5
            if d <= 0.02:        # near-identical composition -> would leak
                continue
        keep.append(j)
    return keep


def idw_predict(qkey, i, keep, k=5, anion_restrict=False):
    q = DATA[i][qkey]
    cand = keep
    if anion_restrict:
        same = [j for j in keep if DATA[j]["anion"] == DATA[i]["anion"]]
        if len(same) >= 3:
            cand = same
    dists = sorted(((float(np.linalg.norm(q - DATA[j][qkey])), j) for j in cand),
                   key=lambda t: t[0])[:k]
    if not dists:
        return 0.0
    w = [1.0 / (d + 0.01) for d, _ in dists]
    tw = sum(w)
    return sum((wi / tw) * DATA[j]["ef"] for wi, (_, j) in zip(w, dists))


def ridge_predict(qkey, i, keep, alpha=1.0, standardize=True):
    X = np.array([DATA[j][qkey] for j in keep])
    y = np.array([DATA[j]["ef"] for j in keep])
    xq = DATA[i][qkey].reshape(1, -1)
    if standardize:
        mu, sd = X.mean(0), X.std(0) + 1e-9
        X = (X - mu) / sd
        xq = (xq - mu) / sd
    from sklearn.linear_model import Ridge
    m = Ridge(alpha=alpha).fit(X, y)
    return float(m.predict(xq)[0])


def krr_predict(qkey, i, keep, alpha=1.0, gamma=None):
    X = np.array([DATA[j][qkey] for j in keep])
    y = np.array([DATA[j]["ef"] for j in keep])
    xq = DATA[i][qkey].reshape(1, -1)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    X = (X - mu) / sd
    xq = (xq - mu) / sd
    from sklearn.kernel_ridge import KernelRidge
    m = KernelRidge(alpha=alpha, kernel="rbf", gamma=gamma).fit(X, y)
    return float(m.predict(xq)[0])


def rf_predict(qkey, i, keep):
    X = np.array([DATA[j][qkey] for j in keep])
    y = np.array([DATA[j]["ef"] for j in keep])
    xq = DATA[i][qkey].reshape(1, -1)
    from sklearn.ensemble import RandomForestRegressor
    m = RandomForestRegressor(n_estimators=200, max_depth=8,
                              random_state=0, n_jobs=-1).fit(X, y)
    return float(m.predict(xq)[0])


def evaluate(name, fn, comp_dedup=True):
    errs = []
    for i in range(N):
        keep = loo_mask(i, comp_dedup)
        if not keep:
            continue
        pred = fn(i, keep)
        errs.append(abs(pred - DATA[i]["ef"]))
    errs = np.array(errs)
    print(f"  {name:34s} MAE {errs.mean():.3f} | RMSE {np.sqrt((errs**2).mean()):.3f} "
          f"| median {np.median(errs):.3f} | n={len(errs)}")
    return errs.mean()


def main():
    print("=" * 72)
    print("FORWARD MODEL (formation energy) -- LOO benchmark on 179 anchors")
    print("=" * 72)

    print("\n[A] Reproduce production (IDW raw, name-only LOO, NO comp-dedup):")
    evaluate("IDW(raw, k=5) prod-style", lambda i, keep: idw_predict("raw", i, keep, 5),
             comp_dedup=False)

    print("\n[B] Strict LOO (drop near-duplicate compositions) -- honest comparison:")
    evaluate("IDW(raw, k=5)        [baseline]", lambda i, keep: idw_predict("raw", i, keep, 5))
    evaluate("IDW(frac, k=5)", lambda i, keep: idw_predict("frac", i, keep, 5))
    evaluate("IDW(phys, k=5)", lambda i, keep: idw_predict("phys", i, keep, 5))
    evaluate("IDW(phys, k=5, anion-restrict)",
             lambda i, keep: idw_predict("phys", i, keep, 5, anion_restrict=True))
    evaluate("IDW(phys, k=8)", lambda i, keep: idw_predict("phys", i, keep, 8))
    evaluate("Ridge(frac, a=1)", lambda i, keep: ridge_predict("frac", i, keep, 1.0))
    evaluate("Ridge(phys, a=1)", lambda i, keep: ridge_predict("phys", i, keep, 1.0))
    evaluate("Ridge(phys, a=0.3)", lambda i, keep: ridge_predict("phys", i, keep, 0.3))
    evaluate("KRR(phys, rbf, a=0.3)", lambda i, keep: krr_predict("phys", i, keep, 0.3))
    evaluate("KRR(phys, rbf, a=1.0)", lambda i, keep: krr_predict("phys", i, keep, 1.0))
    evaluate("RandomForest(phys)", lambda i, keep: rf_predict("phys", i, keep))

    print("\n[D] Per-tier MAE (tier by raw-space min_dist, as production does):")
    # precompute raw min_dist per fold + predictions for baseline / KRR / RF / hybrid
    tiers = {"exact<0.05": [], "dense<0.2": [], "moderate<0.5": [], "sparse>=0.5": []}
    def tier_of(md):
        if md < 0.05: return "exact<0.05"
        if md < 0.2:  return "dense<0.2"
        if md < 0.5:  return "moderate<0.5"
        return "sparse>=0.5"
    rows_base, rows_krr, rows_rf, rows_hyb = {}, {}, {}, {}
    for t in tiers: rows_base[t]=[]; rows_krr[t]=[]; rows_rf[t]=[]; rows_hyb[t]=[]
    for i in range(N):
        keep = loo_mask(i, True)
        if not keep: continue
        md = min(float(np.linalg.norm(DATA[i]["raw"] - DATA[j]["raw"])) for j in keep)
        t = tier_of(md)
        truth = DATA[i]["ef"]
        eb = abs(idw_predict("raw", i, keep, 5) - truth)
        ek = abs(krr_predict("phys", i, keep, 0.3) - truth)
        er = abs(rf_predict("phys", i, keep) - truth)
        # hybrid: trust IDW when a close neighbour exists, else learned model
        hyb = idw_predict("raw", i, keep, 5) if md < 0.3 else krr_predict("phys", i, keep, 0.3)
        eh = abs(hyb - truth)
        rows_base[t].append(eb); rows_krr[t].append(ek); rows_rf[t].append(er); rows_hyb[t].append(eh)
    print(f"    {'tier':14s} {'n':>4s} {'IDW-raw':>9s} {'KRR':>9s} {'RF':>9s} {'hybrid':>9s}")
    allb=allk=allr=allh=[]
    import itertools
    flat = lambda d: list(itertools.chain.from_iterable(d.values()))
    for t in ("exact<0.05","dense<0.2","moderate<0.5","sparse>=0.5"):
        n=len(rows_base[t])
        if n==0: continue
        mb=np.mean(rows_base[t]); mk=np.mean(rows_krr[t]); mr=np.mean(rows_rf[t]); mh=np.mean(rows_hyb[t])
        print(f"    {t:14s} {n:4d} {mb:9.3f} {mk:9.3f} {mr:9.3f} {mh:9.3f}")
    print(f"    {'OVERALL':14s} {N:4d} {np.mean(flat(rows_base)):9.3f} {np.mean(flat(rows_krr)):9.3f} {np.mean(flat(rows_rf)):9.3f} {np.mean(flat(rows_hyb)):9.3f}")

    print("\n[C] Worst baseline errors (where IDW-raw fails):")
    rows = []
    for i in range(N):
        keep = loo_mask(i, True)
        if not keep:
            continue
        e = abs(idw_predict("raw", i, keep, 5) - DATA[i]["ef"])
        rows.append((e, DATA[i]["name"], DATA[i]["formula"], DATA[i]["ef"]))
    rows.sort(reverse=True)
    for e, nm, fo, ef in rows[:10]:
        print(f"    err {e:.2f}  {nm:14s} {fo:18s} true Ef={ef:+.2f}")


if __name__ == "__main__":
    main()
