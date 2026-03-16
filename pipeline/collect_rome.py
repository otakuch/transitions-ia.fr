"""
collect_rome.py — Étape 1 : Collecte des fiches métiers ROME 4.0

Télécharge les fichiers CSV open data du ROME 4.0 depuis data.gouv.fr
et construit data/metiers.json avec la liste structurée des métiers.

Sources :
  - Arborescence ROME : https://www.data.gouv.fr/datasets/repertoire-operationnel-des-metiers-et-des-emplois-rome
  - Fichiers CSV : arborescence_principale_v4_utf8.csv, appellations_v4_utf8.csv

Usage :
    python collect_rome.py
"""

import json
import os
import sys
import time
import requests

# ---------------------------------------------------------------------------
# URLs des fichiers CSV du ROME 4.0 sur data.gouv.fr
# Licence Ouverte v2.0 — France Travail
# ---------------------------------------------------------------------------
ROME_DATASET_API = "https://www.data.gouv.fr/api/1/datasets/repertoire-operationnel-des-metiers-et-des-emplois-rome/"

# Fichiers CSV directs (stables, mis à jour par France Travail)
CSV_URLS = {
    "arborescence": "https://www.data.gouv.fr/fr/datasets/r/3a93a862-c027-4228-9491-3796219e3a3e",
    "appellations": "https://www.data.gouv.fr/fr/datasets/r/fe8a1f09-e417-4286-89f0-6ede523dd633",
    "textes":       "https://www.data.gouv.fr/fr/datasets/r/1e5b8e63-3e83-4c65-acf5-9dd71bd76e9e",
}

# Mapping des 14 grands domaines ROME
GRANDS_DOMAINES = {
    "A": "Agriculture et Pêche",
    "B": "Arts et Façonnage d'Ouvrages d'Art",
    "C": "Banque, Assurance, Immobilier",
    "D": "Commerce, Vente et Grande Distribution",
    "E": "Communication, Média et Multimédia",
    "F": "Construction, Bâtiment et Travaux Publics",
    "G": "Hôtellerie-Restauration, Tourisme et Loisirs",
    "H": "Industrie",
    "I": "Installation et Maintenance",
    "J": "Santé",
    "K": "Services à la Personne et à la Collectivité",
    "L": "Spectacle",
    "M": "Support à l'Entreprise",
    "N": "Transport et Logistique",
}

DATA_DIR = "data"


def fetch_csv_resource(url: str, label: str) -> list[dict]:
    """Télécharge un fichier CSV depuis data.gouv.fr et retourne les lignes."""
    print(f"  Téléchargement : {label}...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    response.encoding = "utf-8"

    import csv
    import io
    reader = csv.DictReader(io.StringIO(response.text), delimiter=";")
    rows = list(reader)
    print(f"  → {len(rows):,} lignes")
    return rows


def fetch_dataset_resources() -> dict:
    """Récupère la liste des ressources disponibles via l'API data.gouv.fr."""
    print("Interrogation de l'API data.gouv.fr...")
    try:
        resp = requests.get(ROME_DATASET_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        resources = {r["title"]: r["url"] for r in data.get("resources", [])}
        print(f"  → {len(resources)} ressources disponibles")
        return resources
    except Exception as e:
        print(f"  Avertissement : impossible de récupérer les ressources API ({e})")
        return {}


def build_metiers_list(arborescence_rows: list[dict]) -> list[dict]:
    """
    Construit la liste des métiers depuis l'arborescence ROME.

    Structure de arborescence_principale_v4_utf8.csv :
      code_rome | libelle_rome | code_domaine_professionnel | libelle_domaine | code_grand_domaine
    """
    metiers = []
    seen = set()

    for row in arborescence_rows:
        code = row.get("code_rome", "").strip()
        if not code or code in seen:
            continue
        seen.add(code)

        grand_domaine_code = code[0].upper() if code else "?"
        libelle = row.get("libelle_rome", row.get("libelle", "")).strip()
        domaine = row.get("libelle_domaine_professionnel", row.get("libelle_domaine", "")).strip()
        code_domaine = row.get("code_domaine_professionnel", row.get("code_domaine", "")).strip()

        # Génère un slug à partir du code ROME (ex: A1101 → a1101)
        slug = code.lower().replace(" ", "-")

        metiers.append({
            "code_rome": code,
            "libelle": libelle,
            "slug": slug,
            "grand_domaine_code": grand_domaine_code,
            "grand_domaine": GRANDS_DOMAINES.get(grand_domaine_code, "Autre"),
            "domaine": domaine,
            "code_domaine": code_domaine,
            "url_rome": f"https://candidat.francetravail.fr/metierscope/fiche-metier/{code}",
        })

    metiers.sort(key=lambda x: x["code_rome"])
    return metiers


def enrich_with_appellations(metiers: list[dict], appellation_rows: list[dict]) -> list[dict]:
    """Ajoute les appellations (intitulés d'emploi) à chaque fiche métier."""
    appels_by_rome = {}
    for row in appellation_rows:
        code = row.get("code_rome", "").strip()
        appel = row.get("libelle_appellation_court", row.get("libelle", "")).strip()
        if code and appel:
            appels_by_rome.setdefault(code, []).append(appel)

    for m in metiers:
        m["appellations"] = appels_by_rome.get(m["code_rome"], [])[:5]  # top 5

    return metiers


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n=== Collecte ROME 4.0 — data.gouv.fr ===\n")

    # 1. Récupération des fichiers CSV
    print("1. Chargement de l'arborescence principale...")
    try:
        arbo_rows = fetch_csv_resource(CSV_URLS["arborescence"], "arborescence_principale_v4")
    except Exception as e:
        print(f"  ERREUR : {e}")
        print("  → Vérifiez votre connexion ou mettez à jour les URLs dans CSV_URLS.")
        sys.exit(1)

    print("\n2. Chargement des appellations...")
    try:
        appel_rows = fetch_csv_resource(CSV_URLS["appellations"], "appellations_v4")
    except Exception as e:
        print(f"  ERREUR : {e}")
        appel_rows = []

    # 2. Construction de la liste des métiers
    print("\n3. Construction de la liste des métiers...")
    metiers = build_metiers_list(arbo_rows)
    metiers = enrich_with_appellations(metiers, appel_rows)

    # 3. Statistiques
    by_domaine = {}
    for m in metiers:
        by_domaine[m["grand_domaine"]] = by_domaine.get(m["grand_domaine"], 0) + 1

    print(f"\n   Total métiers : {len(metiers)}")
    print("\n   Répartition par grand domaine :")
    for gd, count in sorted(by_domaine.items(), key=lambda x: -x[1]):
        print(f"     {gd:<45} {count:>4} métiers")

    # 4. Sauvegarde
    output_path = os.path.join(DATA_DIR, "metiers.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metiers, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(metiers)} métiers sauvegardés dans {output_path}")
    print("\n→ Prochaine étape : python enrich_stats.py")


if __name__ == "__main__":
    main()
