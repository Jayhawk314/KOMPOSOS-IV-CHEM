# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Molecular Dynamics (MD) Runner - GROMACS Backend
===============================================

Actual implementation of MD simulation orchestration.
Resolves prepared GROMACS input bundles, runs subprocesses, and performs
basic trajectory stability analysis from GROMACS XVG outputs.
"""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class MDVerificationResult:
    viable: bool
    score: float
    confidence: float
    potential_energy_diff: float
    diffusion_coefficient: float
    detail: str
    verdict: str = "no_verdict"
    simulation_metadata: Dict = field(default_factory=dict)

    @property
    def measured_md(self) -> bool:
        """True only when a GROMACS trajectory produced analyzable signals."""
        return bool(self.simulation_metadata.get("measured_md"))

    def constraint_scores(self) -> Dict[str, float]:
        """Expose measured MD signals as scorer-like values for ZFC constraints."""
        analysis = self.simulation_metadata.get("analysis", {})
        if not analysis or analysis.get("measured_signals", 0) <= 0:
            return {}

        scores: Dict[str, float] = {}
        drift = analysis.get("relative_energy_drift")
        drift_threshold = analysis.get("energy_drift_threshold")
        if drift is not None and drift_threshold:
            scores["md_energy_stability"] = max(
                0.0,
                min(1.0, 1.0 - float(drift) / max(float(drift_threshold), 1e-12)),
            )

        diffusion = analysis.get("diffusion_coefficient_cm2_s")
        diffusion_threshold = analysis.get("diffusion_threshold_cm2_s")
        if diffusion is not None and diffusion_threshold:
            scores["md_diffusion_stability"] = max(
                0.0,
                min(1.0, 1.0 - float(diffusion) / max(float(diffusion_threshold), 1e-30)),
            )

        if scores:
            scores["md_analysis_confidence"] = max(0.0, min(1.0, float(self.confidence)))
        return scores

    def fuse_with_categorical(
        self,
        cat_score: float,
        cat_viable: bool,
        cat_confidence: float = 0.8,
        viability_threshold: float = 0.45,
    ) -> Dict:
        """Dempster-Shafer fusion of categorical and measured-MD evidence."""
        if not self.constraint_scores() or self.confidence < 0.5:
            return {
                "used": False,
                "fused_score": cat_score,
                "fused_viable": cat_viable,
                "reason": "No measured MD evidence available for Dempster-Shafer fusion.",
            }

        from categorical.dempster_shafer import MassFunction, combine

        theta = frozenset({"viable", "incompatible"})
        viable = frozenset({"viable"})
        incompatible = frozenset({"incompatible"})

        def evidence_mass(score: float, confidence: float) -> MassFunction:
            confidence = max(0.0, min(0.99, confidence))
            score = max(0.0, min(1.0, score))
            return MassFunction({
                viable: score * confidence,
                incompatible: (1.0 - score) * confidence,
                theta: 1.0 - confidence,
            })

        cat_mass = evidence_mass(cat_score, cat_confidence)
        md_mass = evidence_mass(self.score, self.confidence)
        try:
            fused, conflict = combine(cat_mass, md_mass)
        except ValueError:
            return {
                "used": True,
                "fused_score": 0.0,
                "fused_viable": False,
                "conflict": 1.0,
                "belief_viable": 0.0,
                "plausibility_viable": 0.0,
                "reason": "CAT and MD evidence are in total conflict.",
            }

        fused_score = fused.pignistic_probability("viable")
        return {
            "used": True,
            "fused_score": round(fused_score, 4),
            "fused_viable": fused_score >= viability_threshold,
            "conflict": round(conflict, 4),
            "belief_viable": round(fused.belief(viable), 4),
            "plausibility_viable": round(fused.plausibility(viable), 4),
            "cat_score": cat_score,
            "md_score": self.score,
        }


class GROMACSRunner:
    """
    Production-ready runner for GROMACS simulations.
    """

    def __init__(self, gmx_bin: str = "gmx", input_library_dir: Optional[str] = None):
        self.gmx_bin = gmx_bin
        default_library = Path(__file__).resolve().parent.parent / "data" / "gromacs_inputs"
        self.input_library_dir = Path(input_library_dir).resolve() if input_library_dir else default_library

    def _generate_mdp(self, temp_k: float = 298.15) -> str:
        """Generate a basic NVT equilibration MDP file."""
        return f"""
title       = Interface Equilibration
integrator  = md
nsteps      = 50000
dt          = 0.002
continuation = no
constraint_algorithm = lincs
constraints = h-bonds
cutoff-scheme = Verlet
ns_type     = grid
nstlist     = 10
rcoulomb    = 1.0
rvdw        = 1.0
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temp_k}
pcoupl      = no
gen_vel     = yes
gen_temp    = {temp_k}
"""

    def _generate_top(self, mat_a: str, mat_b: str) -> str:
        """Generate a skeletal topology file."""
        return f"""
[ defaults ]
; nbfunc comb-rule gen-pairs fudgeLJ fudgeQQ
1       2         yes       0.5     0.8

[ system ]
Interface: {mat_a} | {mat_b}

[ molecules ]
; Compound       nmols
{mat_a}          100
{mat_b}          100
"""

    def run_interface_simulation(self, 
                                mat_a: str, 
                                mat_b: str, 
                                conditions: Optional[Dict] = None
                                ) -> MDVerificationResult:
        """
        Execute a real GROMACS run in a temporary directory.
        """
        conditions = dict(conditions or {})
        temp_k = conditions.get('temperature_C', 25.0) + 273.15
        input_bundle = self._resolve_input_bundle(mat_a, mat_b, conditions)

        gmx_path = shutil.which(self.gmx_bin)
        if not gmx_path:
            return self._heuristic_fallback(
                mat_a,
                mat_b,
                temp_k,
                reason=f"GROMACS executable '{self.gmx_bin}' was not found on PATH.",
                input_status=input_bundle,
                engine="heuristic_fallback_no_gromacs",
            )

        if input_bundle.get("gro_path") and input_bundle.get("top_path"):
            run_conditions = dict(conditions)
            for key in ("gro_path", "top_path", "mdp_path", "index_path"):
                if input_bundle.get(key):
                    run_conditions[key] = input_bundle[key]
            return self._run_configured_gromacs(mat_a, mat_b, temp_k, run_conditions, gmx_path)

        return self._missing_inputs_no_verdict(mat_a, mat_b, temp_k, input_bundle)

    @staticmethod
    def _normalize_key(name: str) -> str:
        """Normalize material names for filesystem-safe input-bundle lookup."""
        chars = [ch.lower() if ch.isalnum() else "_" for ch in str(name)]
        normalized = "".join(chars).strip("_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized or "material"

    @staticmethod
    def _first_existing(directory: Path, exact_names: List[str], glob_pattern: str) -> Optional[Path]:
        for name in exact_names:
            path = directory / name
            if path.exists():
                return path
        matches = sorted(directory.glob(glob_pattern))
        return matches[0] if matches else None

    def _resolve_input_bundle(self, mat_a: str, mat_b: str, conditions: Dict) -> Dict:
        """Resolve real GROMACS inputs from explicit paths, an input dir, or the local library."""
        explicit_keys = ("gro_path", "top_path", "mdp_path", "index_path")
        if any(conditions.get(key) for key in explicit_keys):
            bundle = {
                "source": "explicit_paths",
                "gro_path": conditions.get("gro_path"),
                "top_path": conditions.get("top_path"),
                "mdp_path": conditions.get("mdp_path"),
                "index_path": conditions.get("index_path"),
                "required_inputs": [".gro", ".top"],
            }
            missing = []
            if not bundle["gro_path"]:
                missing.append("gro_path")
            if not bundle["top_path"]:
                missing.append("top_path")
            bundle["missing_required"] = missing
            return bundle

        checked_dirs: List[str] = []
        input_dir = conditions.get("input_dir")
        if input_dir:
            directory = Path(input_dir).expanduser().resolve()
            checked_dirs.append(str(directory))
            bundle = self._input_bundle_from_dir(directory, source="input_dir")
            bundle["checked_directories"] = checked_dirs
            if bundle.get("gro_path") and bundle.get("top_path"):
                return bundle
            return bundle

        library_root = Path(
            conditions.get("input_library_dir")
            or os.environ.get("KOMPOSOS_GROMACS_INPUT_DIR")
            or self.input_library_dir
        ).expanduser().resolve()
        a_key = self._normalize_key(mat_a)
        b_key = self._normalize_key(mat_b)
        pair_names = [
            f"{a_key}__{b_key}",
            f"{b_key}__{a_key}",
            f"{a_key}_{b_key}",
            f"{b_key}_{a_key}",
        ]
        for pair_name in pair_names:
            directory = library_root / pair_name
            checked_dirs.append(str(directory))
            bundle = self._input_bundle_from_dir(directory, source="input_library")
            if bundle.get("gro_path") and bundle.get("top_path"):
                bundle["checked_directories"] = checked_dirs
                return bundle

        return {
            "source": "missing",
            "gro_path": None,
            "top_path": None,
            "mdp_path": None,
            "index_path": None,
            "required_inputs": [".gro", ".top"],
            "missing_required": ["gro_path", "top_path"],
            "checked_directories": checked_dirs,
        }

    def _input_bundle_from_dir(self, directory: Path, source: str) -> Dict:
        if not directory.exists() or not directory.is_dir():
            return {
                "source": source,
                "directory": str(directory),
                "gro_path": None,
                "top_path": None,
                "mdp_path": None,
                "index_path": None,
                "required_inputs": [".gro", ".top"],
                "missing_required": ["gro_path", "top_path"],
            }

        gro_path = self._first_existing(
            directory,
            ["system.gro", "structure.gro", "conf.gro", "input.gro"],
            "*.gro",
        )
        top_path = self._first_existing(
            directory,
            ["topol.top", "topology.top", "system.top", "input.top"],
            "*.top",
        )
        mdp_path = self._first_existing(
            directory,
            ["run.mdp", "md.mdp", "nvt.mdp", "input.mdp"],
            "*.mdp",
        )
        index_path = self._first_existing(
            directory,
            ["index.ndx", "system.ndx", "input.ndx"],
            "*.ndx",
        )
        missing = []
        if gro_path is None:
            missing.append("gro_path")
        if top_path is None:
            missing.append("top_path")
        return {
            "source": source,
            "directory": str(directory),
            "gro_path": str(gro_path) if gro_path else None,
            "top_path": str(top_path) if top_path else None,
            "mdp_path": str(mdp_path) if mdp_path else None,
            "index_path": str(index_path) if index_path else None,
            "required_inputs": [".gro", ".top"],
            "missing_required": missing,
        }

    def _run_configured_gromacs(
        self,
        mat_a: str,
        mat_b: str,
        temp_k: float,
        conditions: Dict,
        gmx_path: str,
    ) -> MDVerificationResult:
        """Run GROMACS when the caller provides real structure/topology files."""
        gro_src = Path(conditions["gro_path"]).resolve()
        top_src = Path(conditions["top_path"]).resolve()
        mdp_src = Path(conditions["mdp_path"]).resolve() if conditions.get("mdp_path") else None
        index_src = Path(conditions["index_path"]).resolve() if conditions.get("index_path") else None
        timeout_s = int(conditions.get("timeout_s", 300))
        maxwarn = int(conditions.get("maxwarn", 0))
        nt = str(int(conditions.get("nt", 1)))

        missing = [
            str(path)
            for path in [gro_src, top_src, mdp_src, index_src]
            if path is not None and not path.exists()
        ]
        if missing:
            return self._missing_inputs_no_verdict(
                mat_a,
                mat_b,
                temp_k,
                {
                    "source": "configured_paths",
                    "gro_path": str(gro_src),
                    "top_path": str(top_src),
                    "mdp_path": str(mdp_src) if mdp_src is not None else None,
                    "index_path": str(index_src) if index_src is not None else None,
                    "required_inputs": [".gro", ".top"],
                    "missing_required": missing,
                },
            )

        start = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            gro_path = work / "structure.gro"
            top_path = work / "topol.top"
            mdp_path = work / "run.mdp"
            index_path = work / "index.ndx" if index_src is not None else None
            shutil.copy2(gro_src, gro_path)
            shutil.copy2(top_src, top_path)
            if mdp_src is not None:
                shutil.copy2(mdp_src, mdp_path)
            else:
                mdp_path.write_text(self._generate_mdp(temp_k), encoding="utf-8")
            if index_src is not None and index_path is not None:
                shutil.copy2(index_src, index_path)

            grompp_cmd = [
                gmx_path, "grompp",
                "-f", str(mdp_path),
                "-c", str(gro_path),
                "-p", str(top_path),
                "-o", "md.tpr",
            ]
            if maxwarn > 0:
                grompp_cmd.extend(["-maxwarn", str(maxwarn)])

            try:
                grompp = subprocess.run(
                    grompp_cmd,
                    cwd=work,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                mdrun = subprocess.run(
                    [gmx_path, "mdrun", "-deffnm", "md", "-nt", nt],
                    cwd=work,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                analysis = self._analyze_trajectory(work, gmx_path, timeout_s, conditions, index_path)
            except subprocess.TimeoutExpired as exc:
                return MDVerificationResult(
                    viable=False,
                    score=0.50,
                    confidence=0.0,
                    potential_energy_diff=0.0,
                    diffusion_coefficient=0.0,
                    detail=f"GROMACS execution timed out after {timeout_s}s: {exc}",
                    verdict="execution_failed",
                    simulation_metadata={
                        "engine": "GROMACS",
                        "mode": "configured_real_execution_timeout",
                        "measured_md": False,
                        "verdict": "execution_failed",
                    },
                )
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "")[-1000:]
                return MDVerificationResult(
                    viable=False,
                    score=0.50,
                    confidence=0.0,
                    potential_energy_diff=0.0,
                    diffusion_coefficient=0.0,
                    detail=f"GROMACS setup/run failed. This is an execution failure, not a material verdict. {stderr}",
                    verdict="execution_failed",
                    simulation_metadata={
                        "engine": "GROMACS",
                        "mode": "configured_real_execution_failed",
                        "returncode": exc.returncode,
                        "measured_md": False,
                        "verdict": "execution_failed",
                    },
                )

            elapsed = time.time() - start
            measured_md = analysis["measured_signals"] > 0
            mode = (
                "configured_real_execution_analyzed"
                if measured_md
                else "configured_real_execution_no_analysis"
            )
            verdict = "stable" if measured_md and analysis["viable"] else "unstable"
            if not measured_md:
                verdict = "no_verdict"
            return MDVerificationResult(
                viable=analysis["viable"],
                score=analysis["score"],
                confidence=analysis["confidence"],
                potential_energy_diff=analysis["relative_energy_drift"] or 0.0,
                diffusion_coefficient=analysis["diffusion_coefficient_cm2_s"] or 0.0,
                detail=(
                    "GROMACS execution completed and trajectory stability analysis "
                    f"ran on {analysis['measured_signals']} measured signal(s): "
                    f"{analysis['verdict_detail']}"
                ),
                verdict=verdict,
                simulation_metadata={
                    "engine": "GROMACS",
                    "mode": mode,
                    "measured_md": measured_md,
                    "verdict": verdict,
                    "elapsed_s": round(elapsed, 3),
                    "analysis": analysis,
                    "grompp_stdout_tail": (grompp.stdout or "")[-1000:],
                    "mdrun_stdout_tail": (mdrun.stdout or "")[-1000:],
                },
            )

    def _analyze_trajectory(
        self,
        work: Path,
        gmx_path: str,
        timeout_s: int,
        conditions: Dict,
        index_path: Optional[Path],
    ) -> Dict:
        """Extract GROMACS signals and classify trajectory stability."""
        extraction_notes: List[str] = []
        energy_series = self._extract_potential_energy_series(work, gmx_path, timeout_s, extraction_notes)
        msd_series = self._extract_msd_series(work, gmx_path, timeout_s, conditions, index_path, extraction_notes)
        result = self._classify_stability_signals(energy_series, msd_series, conditions)
        result["extraction_notes"] = extraction_notes
        result["energy_points"] = len(energy_series)
        result["msd_points"] = len(msd_series)
        return result

    def _extract_potential_energy_series(
        self,
        work: Path,
        gmx_path: str,
        timeout_s: int,
        notes: List[str],
    ) -> List[Tuple[float, float]]:
        edr_path = work / "md.edr"
        if not edr_path.exists():
            notes.append("No md.edr file found; potential-energy analysis skipped.")
            return []

        out_path = work / "potential.xvg"
        try:
            subprocess.run(
                [gmx_path, "energy", "-f", str(edr_path), "-o", str(out_path)],
                cwd=work,
                input="Potential\n0\n",
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            notes.append(f"Potential-energy extraction failed: {exc}")
            return []
        return self._parse_xvg_series(out_path)

    def _extract_msd_series(
        self,
        work: Path,
        gmx_path: str,
        timeout_s: int,
        conditions: Dict,
        index_path: Optional[Path],
        notes: List[str],
    ) -> List[Tuple[float, float]]:
        trajectory = work / "md.xtc"
        if not trajectory.exists():
            trajectory = work / "md.trr"
        tpr_path = work / "md.tpr"
        if not trajectory.exists() or not tpr_path.exists():
            notes.append("No md.xtc/md.trr plus md.tpr found; MSD analysis skipped.")
            return []

        out_path = work / "msd.xvg"
        cmd = [gmx_path, "msd", "-s", str(tpr_path), "-f", str(trajectory), "-o", str(out_path)]
        if index_path is not None:
            cmd.extend(["-n", str(index_path)])
        group = str(conditions.get("msd_group", "System"))
        try:
            subprocess.run(
                cmd,
                cwd=work,
                input=f"{group}\n",
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            notes.append(f"MSD extraction failed for group '{group}': {exc}")
            return []
        return self._parse_xvg_series(out_path)

    @staticmethod
    def _parse_xvg_series(path: Path) -> List[Tuple[float, float]]:
        """Parse a two-column GROMACS XVG time series, ignoring metadata lines."""
        if not path.exists():
            return []
        series: List[Tuple[float, float]] = []
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", "@")):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                series.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        return series

    @staticmethod
    def _linear_slope(series: List[Tuple[float, float]]) -> Optional[float]:
        """Least-squares slope for a time series."""
        if len(series) < 2:
            return None
        xs = [p[0] for p in series]
        ys = [p[1] for p in series]
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        denom = sum((x - x_mean) ** 2 for x in xs)
        if denom <= 0:
            return None
        return sum((x - x_mean) * (y - y_mean) for x, y in series) / denom

    @classmethod
    def _classify_stability_signals(
        cls,
        energy_series: List[Tuple[float, float]],
        msd_series: List[Tuple[float, float]],
        conditions: Optional[Dict] = None,
    ) -> Dict:
        """Classify MD stability from potential-energy drift and MSD slope."""
        conditions = conditions or {}
        energy_threshold = float(conditions.get("energy_drift_threshold", 0.05))
        diffusion_threshold = float(conditions.get("diffusion_threshold_cm2_s", 1e-8))

        relative_drift: Optional[float] = None
        energy_stable: Optional[bool] = None
        if len(energy_series) >= 2:
            window = max(1, len(energy_series) // 10)
            start = sum(v for _, v in energy_series[:window]) / window
            end = sum(v for _, v in energy_series[-window:]) / window
            denominator = max(abs(start), abs(end), 1.0)
            relative_drift = abs(end - start) / denominator
            energy_stable = relative_drift <= energy_threshold

        diffusion_cm2_s: Optional[float] = None
        diffusion_stable: Optional[bool] = None
        if len(msd_series) >= 2:
            slope_nm2_per_ps = cls._linear_slope(msd_series)
            if slope_nm2_per_ps is not None:
                diffusion_cm2_s = max(0.0, slope_nm2_per_ps / 6.0 * 100.0)
                diffusion_stable = diffusion_cm2_s <= diffusion_threshold

        measured = int(energy_stable is not None) + int(diffusion_stable is not None)
        if measured == 0:
            return {
                "viable": False,
                "score": 0.50,
                "confidence": 0.35,
                "measured_signals": 0,
                "energy_stable": None,
                "diffusion_stable": None,
                "relative_energy_drift": None,
                "diffusion_coefficient_cm2_s": None,
                "energy_drift_threshold": energy_threshold,
                "diffusion_threshold_cm2_s": diffusion_threshold,
                "verdict_detail": "execution completed, but no analyzable energy/MSD signals were produced.",
            }

        energy_score = 0.5
        if relative_drift is not None:
            energy_score = max(0.0, 1.0 - relative_drift / max(energy_threshold, 1e-12))
        diffusion_score = 0.5
        if diffusion_cm2_s is not None:
            diffusion_score = max(0.0, 1.0 - diffusion_cm2_s / max(diffusion_threshold, 1e-30))

        score = round(0.6 * energy_score + 0.4 * diffusion_score, 4)
        checks = [v for v in [energy_stable, diffusion_stable] if v is not None]
        viable = all(checks)
        confidence = 0.65 + 0.10 * measured
        if measured >= 2:
            confidence = 0.85

        detail_parts = []
        if relative_drift is not None:
            detail_parts.append(
                f"relative potential-energy drift={relative_drift:.3g} "
                f"(threshold {energy_threshold:.3g})"
            )
        if diffusion_cm2_s is not None:
            detail_parts.append(
                f"MSD diffusion={diffusion_cm2_s:.3g} cm^2/s "
                f"(threshold {diffusion_threshold:.3g})"
            )
        verdict = "stable" if viable else "unstable"
        return {
            "viable": viable,
            "score": score,
            "confidence": round(confidence, 3),
            "measured_signals": measured,
            "energy_stable": energy_stable,
            "diffusion_stable": diffusion_stable,
            "relative_energy_drift": relative_drift,
            "diffusion_coefficient_cm2_s": diffusion_cm2_s,
            "energy_drift_threshold": energy_threshold,
            "diffusion_threshold_cm2_s": diffusion_threshold,
            "verdict_detail": f"{verdict}; " + "; ".join(detail_parts),
        }

    def _missing_inputs_no_verdict(
        self,
        mat_a: str,
        mat_b: str,
        temp_k: float,
        input_status: Dict,
    ) -> MDVerificationResult:
        checked = input_status.get("checked_directories", [])
        checked_text = f" Checked input directories: {', '.join(checked)}." if checked else ""
        return MDVerificationResult(
            viable=False,
            score=0.50,
            confidence=0.0,
            potential_energy_diff=0.0,
            diffusion_coefficient=0.0,
            detail=(
                "No MD verdict: no GROMACS trajectory was executed because a complete "
                "input bundle was not provided. Supply gro_path/top_path or input_dir "
                "containing a .gro structure and .top topology; optional files are "
                ".mdp and .ndx."
                f"{checked_text}"
            ),
            verdict="no_verdict",
            simulation_metadata={
                "engine": "no_verdict_missing_gromacs_inputs",
                "mode": "missing_required_inputs",
                "measured_md": False,
                "verdict": "no_verdict",
                "requested_temperature_K": temp_k,
                "input_status": input_status,
            },
        )

    def _heuristic_fallback(
        self,
        mat_a: str,
        mat_b: str,
        temp_k: float,
        reason: str,
        input_status: Optional[Dict] = None,
        engine: str = "heuristic_fallback_no_gromacs",
    ) -> MDVerificationResult:
        """Return an honest no-verdict result when no MD trajectory was run."""
        is_sulfide = any(s in mat_a or s in mat_b for s in ["LGPS", "PS4", "S5"])
        is_oxide = any(o in mat_a or o in mat_b for o in ["NMC", "LCO", "O2", "O3"])

        if is_sulfide and is_oxide:
            return MDVerificationResult(
                viable=False,
                score=0.35,
                confidence=0.40,
                potential_energy_diff=0.82,
                diffusion_coefficient=1e-10,
                detail=(
                    "No MD verdict: no GROMACS trajectory was executed. "
                    "Heuristic risk hint: sulfide/oxide interfaces are high-risk. "
                    f"{reason}"
                ),
                verdict="no_verdict",
                simulation_metadata={
                    "engine": engine,
                    "mode": "no_measured_md",
                    "measured_md": False,
                    "verdict": "no_verdict",
                    "heuristic_risk_hint": True,
                    "requested_temperature_K": temp_k,
                    "reason": reason,
                    "input_status": input_status or {},
                },
            )

        return MDVerificationResult(
            viable=False,
            score=0.50,
            confidence=0.0,
            potential_energy_diff=0.0,
            diffusion_coefficient=0.0,
            detail=f"No MD verdict: no GROMACS trajectory was executed. {reason}",
            verdict="no_verdict",
            simulation_metadata={
                "engine": engine,
                "mode": "no_measured_md",
                "measured_md": False,
                "verdict": "no_verdict",
                "requested_temperature_K": temp_k,
                "reason": reason,
                "input_status": input_status or {},
            },
        )


class MDIntegrator:
    """Wrapper that delegates to the real GROMACSRunner."""
    def __init__(self):
        self.runner = GROMACSRunner()

    def should_verify(self, score: float, conf: float, domain: str) -> bool:
        return conf < 0.5 or 0.45 <= score <= 0.55

    def run_verification(self, a, b, domain, cond=None):
        return self.runner.run_interface_simulation(a, b, cond)
