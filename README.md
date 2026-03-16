# IA & Métiers Français — Observatoire des données

> Visualisation interactive de l'exposition à l'IA des métiers français (ROME 4.0 × EEC 2024), avec méthodologie pondérée multi-sources.

**[→ Démo live](https://votre-username.github.io/rome-ia-observatoire/)** · [data.gouv.fr](https://www.data.gouv.fr) · Licence Ouverte v2.0 · Snapshot : mars 2026

---

## 6 onglets interactifs

| Onglet | Contenu |
|--------|---------|
| **Treemap IA** | Carte proportionnelle aux effectifs EEC 2024, colorée par score d'exposition. Cliquer = détail + 3 pistes de réinvention |
| **Exposition → Emploi** | Timeline 2022–2025 des signaux observés en France et Europe |
| **Prédictions (8)** | Estimations pondérées sur déplacement d'emploi, adoption IA, productivité |
| **Productivité & IA** | Probabilités PTF 2025–35 selon 8 économistes (Aghion, Cette, Acemoglu, Brynjolfsson…) |
| **Usage IA France** | Adoption par tranche d'âge, fréquence, outils, tâches (Ipsos-CESI, Ifop-Jedha, Born AI) |
| **Méthodologie** | Sources, scoring pondéré T1×4/T2×2/T3×1/T4×0.5, calibration, limites, comparaison |

---

## Dataset démo — EEC 2024 + ROME 4.0

| Indicateur | Valeur |
|-----------|--------|
| Métiers (démo) | 54 — 13 domaines ROME |
| Emplois représentés | ~8,5M (EEC 2024) |
| Codes FAP 2021 | ✓ sur chaque fiche |
| Sources bibliographiques | 180+ |
| Snapshot | Mars 2026 |

---

## Structure

```
rome-ia-observatoire/
├── index.html              ← Standalone, zéro dépendance, D3.js CDN
├── pipeline/
│   ├── collect_rome.py     ← Collecte ROME 4.0 (data.gouv.fr)
│   ├── enrich_stats.py     ← Enrichissement EEC 2024 + BMO 2024 + salaires
│   ├── score_ia.py         ← Scoring LLM pondéré multi-sources
│   └── build_site.py       ← Génère data.json
├── .env.example
├── LICENSE                 ← MIT
└── .github/workflows/pages.yml
```

---

## Déploiement GitHub Pages

1. Forker le dépôt
2. **Settings → Pages → Source : GitHub Actions**
3. Push sur `main` → déploiement automatique

---

## Pipeline complet

```bash
pip install requests pandas tqdm python-dotenv anthropic

cp .env.example .env   # renseigner ANTHROPIC_API_KEY

python pipeline/collect_rome.py      # 1 584 fiches ROME
python pipeline/enrich_stats.py      # EEC 2024 + salaires + BMO
python pipeline/score_ia.py          # scoring pondéré (~3-8€ API)
python pipeline/build_site.py        # génère data/scores.json

python -m http.server 8000           # tester en local
```

---

## Méthode de scoring

| Tier | Poids | Type |
|------|-------|------|
| T1 | ×4 | Recherche peer-reviewed (NBER, NEJM, Science…) |
| T2 | ×2 | Institutionnel (McKinsey, BIS, IMF, France Stratégie…) |
| T3 | ×1 | Presse (Les Échos, Le Monde, FT, Reuters…) |
| T4 | ×0.5 | Expert / Opinion |

`score = Σ(val × tier_weight × recency_weight) / Σpoids`

La récence donne jusqu'à ×2 à une source 2025 vs 2022.

---

## Sources

ROME 4.0 (France Travail) · FAP 2021 (DARES) · EEC 2024 (INSEE) · Base Tous Salariés 2023 (INSEE) · BMO 2024 (DARES) · BIS WP 1239 · NBER w31161/w34851 · Ipsos-CESI · Ifop-Jedha · Born AI 2025

Méthodologie inspirée de [jobsdata.ai](https://jobsdata.ai/about) · Visualisation adaptée de [joshkale.github.io/jobs](https://joshkale.github.io/jobs/)

**Licence** : Code MIT · Données : Licence Ouverte v2.0 (Etalab)
