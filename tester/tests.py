"""
Les tests de l'API Frankfurter ("Testing as Code").

Chaque test est une fonction qui reçoit le client HTTP.
- Si une assertion échoue -> le test est FAIL (le message explique pourquoi).
- Si tout passe -> le test est PASS.
Chaque test renvoie la réponse utilisée (pour récupérer la latence).

Tous les tests sont NON DESTRUCTIFS : uniquement des GET (lecture).
"""
import re

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def est_nombre(valeur):
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


# ---------------------------------------------------------------
#  A. Tests "Contrat" (fonctionnels)
# ---------------------------------------------------------------

def test_latest_statut_200(client):
    """GET /latest renvoie le code 200."""
    r = client.get("/latest", {"from": "EUR"})
    assert r["error"] is None, r["error"]
    assert r["status"] == 200, f"statut {r['status']} au lieu de 200"
    return r


def test_latest_content_type_json(client):
    """GET /latest renvoie du JSON (Content-Type)."""
    r = client.get("/latest", {"from": "EUR"})
    assert r["error"] is None, r["error"]
    assert "application/json" in (r["content_type"] or ""), \
        f"Content-Type = {r['content_type']}"
    return r


def test_latest_schema(client):
    """GET /latest : champs obligatoires présents et bons types."""
    r = client.get("/latest", {"from": "EUR"})
    assert r["error"] is None, r["error"]
    data = r["json"]
    assert isinstance(data, dict), "la réponse n'est pas un objet JSON"
    for champ in ("amount", "base", "date", "rates"):
        assert champ in data, f"champ manquant : {champ}"
    assert est_nombre(data["amount"]), "amount n'est pas un nombre"
    assert isinstance(data["base"], str), "base n'est pas une chaîne"
    assert isinstance(data["date"], str) and DATE_REGEX.match(data["date"]), \
        f"date au mauvais format : {data['date']}"
    assert isinstance(data["rates"], dict) and data["rates"], "rates vide ou pas un objet"
    for devise, taux in data["rates"].items():
        assert est_nombre(taux), f"le taux de {devise} n'est pas un nombre"
    return r


def test_base_respectee(client):
    """GET /latest?from=USD : la base est USD et USD n'est pas dans rates."""
    r = client.get("/latest", {"from": "USD"})
    assert r["status"] == 200, f"statut {r['status']}"
    data = r["json"] or {}
    assert data.get("base") == "USD", f"base = {data.get('base')}"
    assert "USD" not in data.get("rates", {}), "USD ne devrait pas être dans rates"
    return r


def test_conversion_montant(client):
    """GET /latest?amount=10&from=EUR&to=USD : un seul taux, montant = 10."""
    r = client.get("/latest", {"amount": 10, "from": "EUR", "to": "USD"})
    assert r["status"] == 200, f"statut {r['status']}"
    data = r["json"] or {}
    assert data.get("amount") == 10, f"amount = {data.get('amount')}"
    assert list(data.get("rates", {}).keys()) == ["USD"], \
        f"rates = {list(data.get('rates', {}).keys())}"
    return r


def test_liste_devises(client):
    """GET /currencies : objet {code: nom} contenant EUR et USD."""
    r = client.get("/currencies")
    assert r["status"] == 200, f"statut {r['status']}"
    data = r["json"]
    assert isinstance(data, dict), "la réponse n'est pas un objet"
    assert "EUR" in data and "USD" in data, "EUR ou USD absent"
    assert all(isinstance(nom, str) for nom in data.values()), "un nom n'est pas une chaîne"
    return r


def test_historique(client):
    """GET /2024-01-02 : taux historiques à la bonne date."""
    r = client.get("/2024-01-02", {"from": "EUR", "to": "USD"})
    assert r["status"] == 200, f"statut {r['status']}"
    data = r["json"] or {}
    assert data.get("date") == "2024-01-02", f"date = {data.get('date')}"
    assert est_nombre(data.get("rates", {}).get("USD")), "taux USD absent"
    return r


# ---------------------------------------------------------------
#  Cas d'entrée invalide -> erreur attendue
# ---------------------------------------------------------------

def test_devise_invalide(client):
    """GET /latest?from=XXX : une devise inconnue doit renvoyer une erreur 4xx."""
    r = client.get("/latest", {"from": "XXX"})
    assert r["error"] is None, r["error"]
    assert r["status"] in (400, 404, 422), \
        f"statut {r['status']} au lieu d'une erreur 400/404/422"
    return r


def test_route_inconnue(client):
    """GET /route-qui-nexiste-pas : doit renvoyer 404."""
    r = client.get("/route-qui-nexiste-pas")
    assert r["error"] is None, r["error"]
    assert r["status"] == 404, f"statut {r['status']} au lieu de 404"
    return r


# Liste des tests exécutés à chaque run (ordre d'exécution)
TESTS = [
    test_latest_statut_200,
    test_latest_content_type_json,
    test_latest_schema,
    test_base_respectee,
    test_conversion_montant,
    test_liste_devises,
    test_historique,
    test_devise_invalide,
    test_route_inconnue,
]
