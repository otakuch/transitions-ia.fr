"""
build_site.py — Étape 4 : Construction des données du site

Fusionne stats.csv + scores.json → site/data.json
Format compact optimisé pour le frontend treemap.

Usage :
    python build_site.py
"""

import csv
import json
import os
import statistics

DATA_DIR = "data"
SITE_DIR = "site"


def load_stats() -> dict:
    stats_path = os.path.join(DATA_DIR, "stats.csv")
    if not os.path.exists(stats_path):
        # Fallback sur metiers_enrichis.json
        fallback = os.path.join(DATA_DIR, "metiers_enrichis.json")
        if os.path.exists(fallback):
            with open(fallback, encoding="utf-8") as f:
                rows = json.load(f)
            return {r["code_rome"]: r for r in rows}
        return {}

    with open(stats_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {row["code_rome"]: row for row in reader}


def load_scores() -> dict:
    scores_path = os.path.join(DATA_DIR, "scores.json")
    if not os.path.exists(scores_path):
        return {}
    with open(scores_path, encoding="utf-8") as f:
        scores = json.load(f)
    return {s["code_rome"]: s for s in scores}


def load_metiers() -> list:
    for fname in ("metiers_enrichis.json", "metiers.json"):
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return []


def main():
    os.makedirs(SITE_DIR, exist_ok=True)

    print("\n=== Build site/data.json ===\n")

    metiers = load_metiers()
    stats = load_stats()
    scores = load_scores()

    if not metiers:
        print("ERREUR : aucun métier trouvé.")
        print("→ Lancez d'abord : python collect_rome.py")
        return

    print(f"  {len(metiers)} métiers, {len(stats)} stats, {len(scores)} scores")

    data = []
    for m in metiers:
        code = m["code_rome"]
        stat = stats.get(code, m)
        score = scores.get(code, {})

        # Valeurs numériques sécurisées
        def to_int(val, default=None):
            try:
                return int(val) if val not in (None, "", "None") else default
            except (ValueError, TypeError):
                return default

        entry = {
            "code": code,
            "libelle": m.get("libelle", ""),
            "slug": m.get("slug", code.lower()),
            "grand_domaine": m.get("grand_domaine", ""),
            "grand_domaine_code": m.get("grand_domaine_code", ""),
            "domaine": m.get("domaine", ""),
            "appellations": m.get("appellations", []),
            "url_rome": m.get("url_rome", f"https://candidat.francetravail.fr/metierscope/fiche-metier/{code}"),
            # Stats
            "salaire": to_int(stat.get("salaire_median_net_mensuel"), 2000),
            "effectifs": to_int(stat.get("effectifs_estimes"), 1000),
            "tension": to_int(stat.get("tension_recrutement_pct"), 50),
            "education": stat.get("niveau_education", ""),
            # Score IA
            "exposure": score.get("exposure"),
            "rationale": score.get("rationale", ""),
        }
        data.append(entry)

    # Statistiques globales
    all_exposures = [d["exposure"] for d in data if d["exposure"] is not None]
    all_salaires = [d["salaire"] for d in data if d["salaire"]]
    all_effectifs = [d["effectifs"] for d in data if d["effectifs"]]

    meta = {
        "total_metiers": len(data),
        "metiers_scores": len(all_exposures),
        "score_moyen": round(statistics.mean(all_exposures), 2) if all_exposures else None,
        "score_median": statistics.median(all_exposures) if all_exposures else None,
        "total_emplois": sum(all_effectifs),
        "salaire_moyen": round(statistics.mean(all_salaires)) if all_salaires else None,
        "source_rome": "ROME 4.0 — France Travail / data.gouv.fr",
        "source_salaires": "INSEE Base Tous Salariés 2023",
        "source_effectifs": "INSEE RP 2020 / DARES BMO 2024",
        "licence": "Licence Ouverte v2.0",
    }

    output = {"meta": meta, "metiers": data}

    output_path = os.path.join(SITE_DIR, "data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n✓ site/data.json généré")
    print(f"  {len(data)} métiers")
    print(f"  {len(all_exposures)} scores IA")
    print(f"  Total emplois représentés : {sum(all_effectifs):,}")
    if all_exposures:
        print(f"  Score moyen exposition IA : {meta['score_moyen']}/10")

    print("\n→ Ouvrez site/index.html ou lancez :")
    print("  cd site && python -m http.server 8000")


if __name__ == "__main__":
    main()
