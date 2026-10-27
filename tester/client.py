"""
Client HTTP "prudent" pour tester l'API.

- timeout strict (3 s)
- 1 seul retry maximum (sur timeout, erreur réseau, 429 ou 5xx)
- gestion du 429 : on attend (Retry-After, plafonné) avant de réessayer
- mesure de la latence de chaque appel
- budget de requêtes par run (anti-spam : 20 max)
"""
import time

import requests

BASE_URL = "https://api.frankfurter.app"
TIMEOUT_S = 3
MAX_RETRY = 1
MAX_REQUESTS_PAR_RUN = 20
ATTENTE_MAX_429_S = 5


class BudgetDepasse(Exception):
    """Levée si un run essaie de faire plus de requêtes que le budget."""


class Client:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.nb_requetes = 0
        self.appels = []  # historique de tous les appels (pour la QoS)

    def _une_requete(self, chemin, params):
        if self.nb_requetes >= MAX_REQUESTS_PAR_RUN:
            raise BudgetDepasse(f"Budget de {MAX_REQUESTS_PAR_RUN} requêtes atteint")
        self.nb_requetes += 1
        debut = time.perf_counter()
        reponse = requests.get(self.base_url + chemin, params=params, timeout=TIMEOUT_S)
        latence_ms = round((time.perf_counter() - debut) * 1000, 1)
        return reponse, latence_ms

    def get(self, chemin, params=None):
        """
        Fait un GET et renvoie un dictionnaire :
        {"status": 200, "latency_ms": 123.4, "json": {...}, "content_type": "...",
         "error": None, "retried": False}
        """
        resultat = {"chemin": chemin, "status": None, "latency_ms": None, "json": None,
                    "content_type": None, "error": None, "retried": False}

        for tentative in range(MAX_RETRY + 1):
            try:
                reponse, latence_ms = self._une_requete(chemin, params)
            except BudgetDepasse:
                raise
            except requests.Timeout:
                resultat["error"] = f"timeout (> {TIMEOUT_S} s)"
                resultat["status"] = None
            except requests.RequestException as e:
                resultat["error"] = f"erreur réseau : {e.__class__.__name__}"
                resultat["status"] = None
            else:
                resultat["status"] = reponse.status_code
                resultat["latency_ms"] = latence_ms
                resultat["content_type"] = reponse.headers.get("Content-Type", "")
                resultat["error"] = None
                try:
                    resultat["json"] = reponse.json()
                except ValueError:
                    resultat["json"] = None

                # 429 : l'API nous demande de ralentir -> on attend avant le retry
                if reponse.status_code == 429 and tentative < MAX_RETRY:
                    attente = reponse.headers.get("Retry-After", "1")
                    try:
                        attente = min(float(attente), ATTENTE_MAX_429_S)
                    except ValueError:
                        attente = 1
                    time.sleep(attente)
                    resultat["retried"] = True
                    continue

                # 5xx : erreur côté serveur -> un retry après une courte pause
                if reponse.status_code >= 500 and tentative < MAX_RETRY:
                    time.sleep(1)
                    resultat["retried"] = True
                    continue

                break  # réponse "normale" (2xx, 3xx ou 4xx attendu) : on s'arrête

            # On arrive ici après un timeout ou une erreur réseau
            if tentative < MAX_RETRY:
                resultat["retried"] = True
                time.sleep(1)

        self.appels.append({k: v for k, v in resultat.items() if k != "json"})
        return resultat
