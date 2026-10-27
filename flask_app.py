"""
Testeur automatique de l'API Frankfurter — application Flask.

Routes :
  /             -> consignes de l'atelier
  /run          -> lance un run de tests (GET = réponse JSON, POST = bouton du dashboard)
  /dashboard    -> résultats du dernier run + historique
  /health       -> état de santé de la solution (bonus)
  /export.json  -> export JSON téléchargeable de l'historique (bonus)
"""
import json
from datetime import datetime, timedelta

from flask import Flask, Response, jsonify, redirect, render_template, request

import storage
from tester.runner import lancer_run

app = Flask(__name__)

# Anti-spam : pas plus d'un run toutes les 5 minutes
INTERVALLE_MIN = timedelta(minutes=5)


def secondes_depuis_dernier_run():
    dernier = storage.last_run()
    if not dernier:
        return None
    instant = datetime.fromisoformat(dernier["timestamp"])
    return (datetime.now(instant.tzinfo) - instant).total_seconds()


@app.get("/")
def consignes():
    return render_template("consignes.html")


@app.route("/run", methods=["GET", "POST"])
def run():
    ecart = secondes_depuis_dernier_run()
    if ecart is not None and ecart < INTERVALLE_MIN.total_seconds():
        attente = int(INTERVALLE_MIN.total_seconds() - ecart)
        if request.method == "POST":
            return redirect(f"/dashboard?attente={attente}")
        return jsonify({"status": "refused",
                        "reason": f"Un run a déjà eu lieu récemment. Réessayez dans {attente} s."}), 429

    resultat = lancer_run()
    resultat["id"] = storage.save_run(resultat)

    if request.method == "POST":
        return redirect("/dashboard")
    return jsonify(resultat)


@app.get("/dashboard")
def dashboard():
    runs = storage.list_runs(30)
    dernier = runs[0] if runs else None

    # Données de la courbe (du plus ancien au plus récent)
    tendance = [
        {"label": r["timestamp"][11:16],
         "avg": r["summary"]["latency_ms_avg"] or 0,
         "p95": r["summary"]["latency_ms_p95"] or 0,
         "failed": r["summary"]["failed"]}
        for r in reversed(runs)
    ]
    courbes = calculer_courbes(tendance)
    return render_template("dashboard.html", dernier=dernier, runs=runs,
                           courbes=courbes, attente=request.args.get("attente"))


def calculer_courbes(tendance, largeur=600, hauteur=160):
    """Transforme les latences en points d'un graphique SVG (polyline)."""
    if len(tendance) < 2:
        return None
    maxi = max(max(t["p95"] for t in tendance), 1)
    pas = largeur / (len(tendance) - 1)

    def points(cle):
        return " ".join(f"{round(i * pas, 1)},{round(hauteur - t[cle] / maxi * (hauteur - 10), 1)}"
                        for i, t in enumerate(tendance))

    return {"avg": points("avg"), "p95": points("p95"), "max": round(maxi),
            "debut": tendance[0]["label"], "fin": tendance[-1]["label"],
            "largeur": largeur, "hauteur": hauteur}


@app.get("/health")
def health():
    """L'application fonctionne-t-elle ? La base répond-elle ? Les runs sont-ils récents ?"""
    try:
        dernier = storage.last_run()
        base_ok = True
    except Exception as e:
        dernier, base_ok = None, False
        app.logger.error("Base inaccessible : %s", e)

    age = secondes_depuis_dernier_run() if base_ok else None
    etat = "ok"
    if not base_ok:
        etat = "error"
    elif dernier is None or age > 24 * 3600:
        etat = "degraded"  # pas de run depuis plus de 24 h

    return jsonify({
        "status": etat,
        "database": "ok" if base_ok else "error",
        "last_run": dernier["timestamp"] if dernier else None,
        "last_run_age_s": int(age) if age is not None else None,
        "last_run_available": dernier["summary"]["available"] if dernier else None,
    }), (200 if etat != "error" else 503)


@app.get("/export.json")
def export_json():
    contenu = json.dumps(storage.list_runs(500), ensure_ascii=False, indent=2)
    return Response(contenu, mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=runs.json"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
