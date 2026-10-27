"""
topic_graph.py  --  Member 3: topic (concept) structure for the Junyi mathematics data.

HONESTY NOTE
------------
Member 2's exercise lookup only has a level-4 concept id (an anonymised hash) per exercise.
It has NO prerequisite relations and NO topic names.  Unless you pass a verified prerequisite
list (`prereq_edges`), this graph therefore uses DATA-DERIVED CURRICULUM LEVELS:

  * concepts are grouped by learning stage (elementary -> junior -> senior),
  * inside a stage they are ordered from easiest to hardest by their historical
    correct-answer rate (`concept_enc`, measured on the training period),
  * the ordered concepts are cut into `n_levels_per_stage` levels.

A concept on level L unlocks when enough concepts of level L-1 are mastered.
This is a HEURISTIC ordering, not a verified prerequisite graph, and the project report
must say so.  If real prerequisite pairs become available, pass them as `prereq_edges`;
they replace the heuristic completely.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

STAGE_RANK = {"elementary": 0, "junior": 1, "senior": 2}


@dataclass
class Concept:
    code: int
    label: str
    stage: str
    level: int
    base_rate: float                       # historical P(correct) for this concept
    ucids: List[str] = field(default_factory=list)   # easy -> hard
    title_en: Optional[str] = None         # English title (translated by Claude, see build_topic_titles.py)
    title_zh: Optional[str] = None         # original name taken from Info_Content.csv
    area_code: Optional[int] = None        # level-2 parent (1..10)
    area_name: Optional[str] = None
    group_code: Optional[int] = None       # level-3 parent (1..42)
    retiring: bool = False                 # Junyi marks the topic "即將下架" (being retired)

    @property
    def display_name(self) -> str:
        return self.title_en or f"{self.stage.title()} topic {self.code}"


class TopicGraph:
    def __init__(self, concepts: Dict[int, Concept], exercises: Dict[str, dict],
                 prereq_edges: Optional[List[Tuple[int, int]]] = None):
        self.concepts = concepts
        self.exercises = exercises          # ucid -> dict(concept, difficulty, stage, base_rate)
        self.explicit_edges = list(prereq_edges) if prereq_edges else None
        self.source = "verified-prerequisites" if self.explicit_edges else "heuristic-curriculum-levels"
        self.max_level = max(c.level for c in concepts.values())
        self.by_level: Dict[int, List[int]] = {}
        for c in concepts.values():
            self.by_level.setdefault(c.level, []).append(c.code)
        self._prereqs: Dict[int, List[int]] = {c: [] for c in concepts}
        for a, b in (self.explicit_edges or []):
            if b in self._prereqs:
                self._prereqs[b].append(a)

    # ------------------------------------------------------------------ building
    @classmethod
    def from_lookup(cls, lookup, prereq_edges=None, n_levels_per_stage: int = 3,
                    info_content=None, titles=None, area_names=None) -> "TopicGraph":
        """
        `lookup` = path to member2_exercise_lookup.csv or an already-loaded DataFrame.
        Optional enrichment (all three are optional, the graph works without them):
          info_content : path/DataFrame of Info_Content.csv  -> exercise names + level2/level3 parents
          titles       : path/DataFrame of data/topic_titles.csv -> topic titles (zh, en)
          area_names   : path to data/area_names.json (level2_id -> English name)
        """
        if isinstance(lookup, pd.DataFrame):
            lk = lookup.copy()
        else:
            lk = pd.read_csv(lookup, dtype={"ucid": str})
        lk["ucid"] = lk["ucid"].astype(str)

        rows = []
        for code, g in lk.groupby("concept_code"):
            stage = g["learning_stage"].mode().iloc[0]
            rows.append((int(code), g["concept_label"].iloc[0], stage, float(g["concept_enc"].iloc[0])))
        meta = pd.DataFrame(rows, columns=["code", "label", "stage", "base_rate"])
        meta["stage_rank"] = meta["stage"].map(STAGE_RANK).fillna(1).astype(int)

        level_of: Dict[int, int] = {}
        next_level = 0
        for rank in sorted(meta["stage_rank"].unique()):
            part = meta[meta["stage_rank"] == rank].sort_values(["base_rate", "code"], ascending=[False, True])
            n_groups = int(min(n_levels_per_stage, max(1, len(part) // 4)))
            for chunk in np.array_split(part["code"].to_numpy(), n_groups):
                for code in chunk:
                    level_of[int(code)] = next_level
                next_level += 1

        concepts = {
            int(r.code): Concept(int(r.code), r.label, r.stage, level_of[int(r.code)], float(r.base_rate))
            for r in meta.itertuples()
        }
        exercises = {}
        for r in lk.sort_values(["exercise_enc", "ucid"], ascending=[False, True]).itertuples():
            concepts[int(r.concept_code)].ucids.append(r.ucid)       # easy -> hard
            exercises[r.ucid] = {"concept": int(r.concept_code), "difficulty": r.difficulty,
                                 "stage": r.learning_stage, "base_rate": float(r.exercise_enc)}
        graph = cls(concepts, exercises, prereq_edges)
        if info_content is not None:
            graph._attach_info(info_content, titles, area_names)
        return graph

    @classmethod
    def from_project(cls, root, **kw) -> "TopicGraph":
        """Load everything from the project folder (models/ + data/)."""
        from pathlib import Path
        root = Path(root)
        return cls.from_lookup(root / "models" / "member2_exercise_lookup.csv",
                               info_content=root / "data" / "Info_Content.csv",
                               titles=root / "data" / "topic_titles.csv",
                               area_names=root / "data" / "area_names.json", **kw)

    def _attach_info(self, info_content, titles, area_names) -> None:
        import json
        from pathlib import Path
        ic = info_content if isinstance(info_content, pd.DataFrame) else pd.read_csv(info_content, dtype=str)
        ic = ic.copy()
        ic["ucid"] = ic["ucid"].astype(str)
        ic = ic.set_index("ucid")
        for u, e in self.exercises.items():
            if u in ic.index:
                e["name_zh"] = ic.at[u, "content_pretty_name"]
        # parents: level2 (area) and level3 (group), numbered by curriculum order
        par = {}
        for c in self.concepts.values():
            if c.ucids and c.ucids[0] in ic.index:
                par[c.code] = (ic.at[c.ucids[0], "level2_id"], ic.at[c.ucids[0], "level3_id"])
        order = sorted(par, key=lambda code: (self.concepts[code].level, code))
        area_no, group_no = {}, {}
        for code in order:
            l2, l3 = par[code]
            area_no.setdefault(l2, len(area_no) + 1)
            group_no.setdefault(l3, len(group_no) + 1)
        names = {}
        if area_names is not None:
            names = json.load(open(area_names, encoding="utf-8")) if not isinstance(area_names, dict) else area_names
        for code, (l2, l3) in par.items():
            c = self.concepts[code]
            c.area_code, c.group_code = area_no[l2], group_no[l3]
            c.area_name = names.get(l2)
        if titles is not None:
            t = titles if isinstance(titles, pd.DataFrame) else pd.read_csv(titles, encoding="utf-8-sig")
            for r in t.itertuples():
                c = self.concepts.get(int(r.concept_code))
                if c is not None and c.label == r.concept_label:
                    c.title_zh, c.title_en = r.title_zh, r.title_en
                    c.retiring = str(r.retiring_on_junyi).lower() == "true"
        # English-only exercise labels (the dataset's own exercise names are Traditional Chinese)
        for c in self.concepts.values():
            n = len(c.ucids)
            for k, u in enumerate(c.ucids, start=1):
                self.exercises[u]["label_en"] = f"{c.display_name} - exercise {k} of {n} ({self.exercises[u]['difficulty']})"

    # ------------------------------------------------------------------ queries
    def prereqs(self, code: int) -> List[int]:
        return self._prereqs[code]

    def concept_of(self, ucid: str) -> Optional[int]:
        ex = self.exercises.get(str(ucid))
        return ex["concept"] if ex else None

    def stage_start_level(self, stage: str) -> int:
        levels = [c.level for c in self.concepts.values() if c.stage == stage]
        return min(levels) if levels else 0

    def unlock_status(self, code: int, mastered: set, start_level: int = 0,
                      gate_fraction: float = 0.34) -> Tuple[bool, str]:
        """Returns (is_unlocked, human-readable detail)."""
        c = self.concepts[code]
        if self.explicit_edges is not None:
            pre = self._prereqs[code]
            if not pre:
                return True, "no prerequisites"
            missing = [p for p in pre if p not in mastered]
            if missing:
                return False, f"{len(missing)} prerequisite topic(s) not mastered yet"
            return True, f"all {len(pre)} prerequisite topic(s) mastered"
        if c.level <= start_level or c.level == 0:
            return True, "foundation level"
        prev = self.by_level.get(c.level - 1, [])
        done = sum(1 for p in prev if p in mastered)
        ok = done >= gate_fraction * len(prev)
        return ok, (f"{done} of {len(prev)} level-{c.level - 1} topics mastered "
                    f"(at least {gate_fraction:.0%} needed)")

    # ------------------------------------------------------------------ validation
    def validate(self) -> dict:
        out = {"self_loops": [], "unknown_nodes": [], "cycles": False,
               "duplicate_exercises": 0, "concepts_without_exercises": [],
               "exercise_stage_conflicts": 0}
        if self.explicit_edges:
            for a, b in self.explicit_edges:
                if a == b:
                    out["self_loops"].append(a)
                if a not in self.concepts or b not in self.concepts:
                    out["unknown_nodes"].append((a, b))
            indeg = {c: 0 for c in self.concepts}
            adj = {c: [] for c in self.concepts}
            for a, b in self.explicit_edges:
                if a in adj and b in indeg and a != b:
                    adj[a].append(b)
                    indeg[b] += 1
            queue = [c for c, d in indeg.items() if d == 0]
            seen = 0
            while queue:
                n = queue.pop()
                seen += 1
                for m in adj[n]:
                    indeg[m] -= 1
                    if indeg[m] == 0:
                        queue.append(m)
            out["cycles"] = seen != len(self.concepts)
        all_ids = [u for c in self.concepts.values() for u in c.ucids]
        out["duplicate_exercises"] = len(all_ids) - len(set(all_ids))
        out["concepts_without_exercises"] = [c.code for c in self.concepts.values() if not c.ucids]
        out["exercise_stage_conflicts"] = sum(
            1 for e in self.exercises.values() if e["stage"] != self.concepts[e["concept"]].stage)
        out["ok"] = not (out["self_loops"] or out["unknown_nodes"] or out["cycles"]
                         or out["duplicate_exercises"] or out["concepts_without_exercises"])
        out.update(source=self.source, n_concepts=len(self.concepts),
                   n_exercises=len(self.exercises), n_levels=self.max_level + 1)
        return out

    def export(self, out_dir, include_chinese: bool = False) -> dict:
        """Write topic_graph.json (areas -> topics -> exercises) and topic_map.csv (one row per exercise).
        English only by default; include_chinese=True adds the original Traditional Chinese names."""
        import json
        from pathlib import Path
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        note = ("The dataset has NO prerequisite information. 'level' is a data-derived curriculum order "
                "(heuristic) built from learning stage and historical difficulty; 'area'/'group' are the real "
                "level-2/level-3 hierarchy of Info_Content.csv. English titles are translated by Claude."
                if self.explicit_edges is None else "Prerequisites supplied by the team.")
        ordered = sorted(self.concepts.values(), key=lambda c: (c.level, c.code))

        def topic_dict(c):
            zh_t = {"title_zh": c.title_zh} if include_chinese else {}
            return {"concept_code": c.code, "name": c.display_name, **zh_t,
                    "concept_label": c.label, "stage": c.stage, "level": c.level,
                    "area_code": c.area_code, "group_code": c.group_code,
                    "base_rate": round(c.base_rate, 4), "n_exercises": len(c.ucids),
                    "retiring_on_junyi": c.retiring, "prerequisite_concepts": self._prereqs[c.code],
                    "exercises_easy_to_hard": [
                        {"ucid": u, "label": self.exercises[u].get("label_en"),
                         **({"name_zh": self.exercises[u].get("name_zh")} if include_chinese else {}),
                         "difficulty": self.exercises[u]["difficulty"]} for u in c.ucids]}
        areas = {}
        for c in ordered:
            a = areas.setdefault(c.area_code, {"area_code": c.area_code, "area_name": c.area_name, "topics": []})
            a["topics"].append(topic_dict(c))
        data = {"graph_source": self.source, "note": note, "n_concepts": len(self.concepts),
                "n_exercises": len(self.exercises), "n_levels": self.max_level + 1,
                "areas": [areas[k] for k in sorted(areas, key=lambda k: (k is None, k))]}
        (out / "topic_graph.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        df = pd.DataFrame([{"ucid": u, "exercise_label": self.exercises[u].get("label_en"),
                            **({"exercise_name_zh": self.exercises[u].get("name_zh"), "topic_title_zh": c.title_zh}
                               if include_chinese else {}),
                            "concept_code": c.code, "topic_title_en": c.display_name,
                            "area_code": c.area_code, "area_name": c.area_name, "group_code": c.group_code,
                            "stage": c.stage, "level": c.level, "difficulty": self.exercises[u]["difficulty"],
                            "exercise_base_rate": round(self.exercises[u]["base_rate"], 4)}
                           for c in ordered for u in c.ucids])
        df.to_csv(out / "topic_map.csv", index=False, encoding="utf-8-sig")
        return {"json": str(out / "topic_graph.json"), "csv": str(out / "topic_map.csv")}

    def to_dict(self) -> dict:
        return {"source": self.source,
                "levels": [{"level": lv, "concepts": [
                    {"code": c, "name": self.concepts[c].display_name,
                     "stage": self.concepts[c].stage, "n_exercises": len(self.concepts[c].ucids)}
                    for c in codes]} for lv, codes in sorted(self.by_level.items())]}
