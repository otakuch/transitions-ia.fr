"""
score_ia.py — Étape 3 : Scoring de l'exposition à l'IA

Envoie chaque fiche métier à un LLM et retourne un score d'exposition IA 0-10
avec un rationale en français.

Modèles supportés :
  - Claude (Anthropic) via ANTHROPIC_API_KEY
  - Gemini Flash via OpenRouter (OPENROUTER_API_KEY)

Résultats : data/scores.json

Usage :
    python score_ia.py
    python score_ia.py --limit 50       # Tester sur 50 métiers
    python score_ia.py --provider openrouter
"""

import argparse
import json
import os
import sys
import time
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATA_DIR = "data"

# ---------------------------------------------------------------------------
# Barème de scoring — calibré sur le contexte français
# ---------------------------------------------------------------------------
SCORING_RUBRIC = """
Tu es un expert en économie du travail et en IA. Évalue le score d'exposition à l'IA
pour un métier français sur une échelle de 0 à 10.

Ce score mesure dans quelle mesure l'IA va transformer ce métier au cours des 10 prochaines années,
en tenant compte à la fois de l'automatisation directe (l'IA fait le travail) et des effets indirects
(l'IA rend les travailleurs tellement productifs que moins d'emplois sont nécessaires).

Critères clés :
- Le travail est-il entièrement réalisable sur ordinateur depuis un bureau ? → exposition élevée
- Le travail nécessite-t-il une présence physique, une dextérité manuelle, ou une interaction humaine en temps réel ? → exposition faible
- Le travail implique-t-il principalement de traiter, analyser ou générer de l'information ? → exposition très élevée
- Le travail nécessite-t-il un jugement éthique, une empathie clinique, ou une responsabilité légale directe ? → exposition modérée

Étalonnage (exemples calibrants) :
  0-1 : Maçon, plombier, aide soignant à domicile, cuisinier de restauration rapide
  2-3 : Infirmier, électricien, chauffeur poids lourd, pompier
  4-5 : Médecin généraliste, enseignant du secondaire, commercial terrain
  6-7 : Comptable, ingénieur projet, manager RH, architecte
  8-9 : Développeur logiciel, analyste financier, juriste, rédacteur web
  10  : Transcripteur médical, opérateur de saisie, traducteur technique

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni explication supplémentaire :
{
  "score": <entier de 0 à 10>,
  "rationale": "<1-2 phrases en français expliquant le score>"
}
"""


def build_prompt(metier: dict) -> str:
    """Construit le prompt de scoring pour un métier."""
    appellations = ", ".join(metier.get("appellations", [])[:3])
    prompt = f"""Métier ROME : {metier['libelle']}
Code ROME : {metier['code_rome']}
Grand domaine : {metier['grand_domaine']}
Domaine professionnel : {metier['domaine']}"""
    if appellations:
        prompt += f"\nAppellations courantes : {appellations}"
    return prompt


def score_with_anthropic(metier: dict, client) -> dict:
    """Score un métier via l'API Anthropic (Claude)."""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku = rapide et économique pour ce cas
        max_tokens=256,
        system=SCORING_RUBRIC,
        messages=[{"role": "user", "content": build_prompt(metier)}],
    )
    raw = message.content[0].text.strip()
    result = json.loads(raw)
    return {
        "code_rome": metier["code_rome"],
        "slug": metier["slug"],
        "exposure": int(result["score"]),
        "rationale": result["rationale"],
    }


def score_with_openrouter(metier: dict, api_key: str) -> dict:
    """Score un métier via OpenRouter (Gemini Flash)."""
    import requests
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "google/gemini-flash-1.5",
            "messages": [
                {"role": "system", "content": SCORING_RUBRIC},
                {"role": "user", "content": build_prompt(metier)},
            ],
            "max_tokens": 256,
        },
        timeout=30,
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"].strip()
    # Nettoyage JSON si le modèle ajoute des backticks
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    result = json.loads(raw)
    return {
        "code_rome": metier["code_rome"],
        "slug": metier["slug"],
        "exposure": int(result["score"]),
        "rationale": result["rationale"],
    }


def load_existing_scores(path: str) -> dict:
    """Charge les scores déjà calculés (reprise sur interruption)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            scores = json.load(f)
        return {s["code_rome"]: s for s in scores}
    return {}


def save_scores(scores: dict, path: str):
    """Sauvegarde les scores."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(scores.values()), f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Score d'exposition IA des métiers ROME")
    parser.add_argument("--limit", type=int, default=None, help="Limiter à N métiers (test)")
    parser.add_argument("--provider", choices=["anthropic", "openrouter"], default="anthropic")
    parser.add_argument("--delay", type=float, default=0.3, help="Délai entre requêtes (secondes)")
    args = parser.parse_args()

    # Chargement des métiers enrichis
    metiers_path = os.path.join(DATA_DIR, "metiers_enrichis.json")
    if not os.path.exists(metiers_path):
        metiers_path = os.path.join(DATA_DIR, "metiers.json")
    if not os.path.exists(metiers_path):
        print("ERREUR : data/metiers_enrichis.json introuvable.")
        print("→ Lancez d'abord : python collect_rome.py && python enrich_stats.py")
        sys.exit(1)

    with open(metiers_path, encoding="utf-8") as f:
        metiers = json.load(f)

    if args.limit:
        metiers = metiers[:args.limit]
        print(f"Mode test : limité à {args.limit} métiers")

    # Chargement des scores existants (reprise)
    scores_path = os.path.join(DATA_DIR, "scores.json")
    existing = load_existing_scores(scores_path)
    print(f"{len(existing)} scores déjà calculés (reprise possible)")

    # Initialisation du provider
    if args.provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            print("ERREUR : pip install anthropic")
            sys.exit(1)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERREUR : ANTHROPIC_API_KEY manquant dans .env")
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)
        score_fn = lambda m: score_with_anthropic(m, client)
    else:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("ERREUR : OPENROUTER_API_KEY manquant dans .env")
            sys.exit(1)
        score_fn = lambda m: score_with_openrouter(m, api_key)

    print(f"\n=== Scoring IA — {len(metiers)} métiers ({args.provider}) ===\n")

    scores = dict(existing)
    errors = 0
    new_count = 0

    for i, metier in enumerate(metiers):
        code = metier["code_rome"]

        # Sauter si déjà scoré
        if code in scores:
            continue

        try:
            result = score_fn(metier)
            scores[code] = result
            new_count += 1

            bar = "█" * result["exposure"] + "░" * (10 - result["exposure"])
            print(f"[{i+1:4}/{len(metiers)}] {code} | {metier['libelle'][:40]:<40} | {bar} {result['exposure']:2}/10")

            # Sauvegarde toutes les 25 requêtes
            if new_count % 25 == 0:
                save_scores(scores, scores_path)
                print(f"  → Checkpoint : {len(scores)} scores sauvegardés")

            time.sleep(args.delay)

        except KeyboardInterrupt:
            print("\n\nInterrompu par l'utilisateur.")
            break
        except Exception as e:
            errors += 1
            print(f"[{i+1:4}/{len(metiers)}] ERREUR {code}: {e}")
            if errors > 10:
                print("Trop d'erreurs, arrêt.")
                break
            time.sleep(2)

    # Sauvegarde finale
    save_scores(scores, scores_path)

    # Statistiques
    all_scores = [s["exposure"] for s in scores.values()]
    if all_scores:
        moyenne = sum(all_scores) / len(all_scores)
        distribution = {i: all_scores.count(i) for i in range(11)}

        print(f"\n✓ {len(scores)} scores sauvegardés dans data/scores.json")
        print(f"  Score moyen : {moyenne:.1f}/10")
        print(f"  Distribution : {distribution}")

    print("\n→ Prochaine étape : python build_site.py")


if __name__ == "__main__":
    main()
