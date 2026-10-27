# API Choice

- Étudiant : David Kouakou
- API choisie : Frankfurter (taux de change de la Banque centrale européenne)
- URL base : https://api.frankfurter.app
- Documentation officielle / README : https://frankfurter.dev
- Auth : None
- Endpoints testés :
  - GET /latest?from=EUR — derniers taux de change à partir de l'euro
  - GET /latest?from=USD — derniers taux à partir du dollar (base respectée)
  - GET /latest?amount=10&from=EUR&to=USD — conversion d'un montant
  - GET /currencies — liste des devises disponibles
  - GET /2024-01-02?from=EUR&to=USD — taux historiques à une date donnée
  - GET /latest?from=XXX — devise invalide (erreur attendue)
  - GET /route-qui-nexiste-pas — route inconnue (404 attendu)
- Hypothèses de contrat (champs attendus, types, codes) :
  - /latest et /{date} : code 200, Content-Type `application/json`, objet avec
    `amount` (nombre), `base` (string, code devise), `date` (string AAAA-MM-JJ),
    `rates` (objet { code devise : nombre }), la devise de base n'apparaît pas dans `rates`
  - /currencies : code 200, objet { code devise (string) : nom (string) } contenant EUR et USD
  - devise inconnue : erreur 4xx (400, 404 ou 422)
  - route inexistante : 404
- Limites / rate limiting connu : pas de limite documentée ; on reste raisonnable
  (20 requêtes max par run, 1 run toutes les 5 minutes maximum, timeout 3 s, 1 retry max)
- Risques (instabilité, downtime, CORS, etc.) :
  - taux mis à jour une fois par jour ouvré (vers 16 h CET) : les valeurs changent, on ne teste donc que les types
  - pas de taux le week-end et les jours fériés : la date renvoyée peut être antérieure à la date du jour
  - service gratuit maintenu par un particulier : interruption possible
  - un compte gratuit PythonAnywhere ne peut joindre que les sites de sa whitelist (api.frankfurter.app y figure)
