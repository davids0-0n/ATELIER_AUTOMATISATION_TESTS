"""
Exécute tous les tests, puis calcule les métriques QoS d'un run.
"""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from tester.client import BudgetDepasse, Client
from tester.tests import TESTS

NOM_API = "Frankfurter"
NB_APPELS_LATENCE = 5      # appels supplémentaires pour mesurer la latence
SEUIL_P95_MS = 1000        # au-delà, on considère la latence "dégradée"


def percentile(valeurs, p):
    """Percentile par la méthode du rang le plus proche (ex. p=95)."""
    if not valeurs:
        return None
    triees = sorted(valeurs)
    rang = max(1, math.ceil(p / 100 * len(triees)))
    return triees[rang - 1]


def lancer_run():
    client = Client()
    resultats = []

    # 1) Les tests fonctionnels
    for test in TESTS:
        nom = test.__name__
        description = (test.__doc__ or "").strip()
        try:
            r = test(client)
            resultats.append({"name": nom, "description": description, "status": "PASS",
                              "latency_ms": r.get("latency_ms"), "http": r.get("status"),
                              "details": "OK" + (" (après 1 retry)" if r.get("retried") else "")})
        except AssertionError as e:
            dernier = client.appels[-1] if client.appels else {}
            resultats.append({"name": nom, "description": description, "status": "FAIL",
                              "latency_ms": dernier.get("latency_ms"), "http": dernier.get("status"),
                              "details": str(e) or "assertion échouée"})
        except BudgetDepasse as e:
            resultats.append({"name": nom, "description": description, "status": "ERROR",
                              "latency_ms": None, "http": None, "details": str(e)})
            break
        except Exception as e:  # bug inattendu : on le note sans faire planter le run
            resultats.append({"name": nom, "description": description, "status": "ERROR",
                              "latency_ms": None, "http": None,
                              "details": f"{e.__class__.__name__}: {e}"})

    # 2) Quelques appels de plus pour mesurer la latence
    for _ in range(NB_APPELS_LATENCE):
        try:
            client.get("/latest", {"from": "EUR"})
        except BudgetDepasse:
            break

    # 3) Métriques QoS
    latences = [a["latency_ms"] for a in client.appels if a["latency_ms"] is not None]
    nb_appels = len(client.appels)
    # Erreurs "HTTP" non voulues : timeout/réseau, 429 ou 5xx
    nb_erreurs_http = sum(1 for a in client.appels
                          if a["status"] is None or a["status"] == 429 or a["status"] >= 500)

    passed = sum(1 for t in resultats if t["status"] == "PASS")
    failed = len(resultats) - passed
    test_principal = next((t for t in resultats if t["name"] == "test_latest_statut_200"), None)
    disponible = bool(test_principal and test_principal["status"] == "PASS")

    latence_avg = round(sum(latences) / len(latences), 1) if latences else None
    latence_p95 = percentile(latences, 95)

    summary = {
        "passed": passed,
        "failed": failed,
        "total": len(resultats),
        "error_rate": round(failed / len(resultats), 3) if resultats else 1.0,
        "http_error_rate": round(nb_erreurs_http / nb_appels, 3) if nb_appels else 1.0,
        "latency_ms_avg": latence_avg,
        "latency_ms_p95": latence_p95,
        "available": disponible,
        "requests": nb_appels,
    }
    summary["verdict"] = interpreter(summary)

    return {
        "api": NOM_API,
        "timestamp": datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "summary": summary,
        "tests": resultats,
    }


def interpreter(s):
    """Une phrase lisible qui résume l'état de l'API pour ce run."""
    if not s["available"]:
        return "🔴 API indisponible : l'endpoint principal ne répond pas correctement."
    if s["failed"] > 0:
        return f"🟠 API disponible mais {s['failed']} test(s) en échec : le contrat n'est plus respecté."
    if s["latency_ms_p95"] is not None and s["latency_ms_p95"] > SEUIL_P95_MS:
        return f"🟠 Contrat respecté mais latence dégradée (p95 > {SEUIL_P95_MS} ms)."
    return "🟢 API disponible, contrat respecté et latence correcte."
