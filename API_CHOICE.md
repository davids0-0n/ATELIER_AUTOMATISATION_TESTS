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

## Robustesse

- Timeout strict de 3 s sur chaque requête
- 1 retry maximum en cas de timeout, d'erreur réseau ou de réponse 5xx (pause de 1 s)
- Code 429 : attente selon l'en-tête `Retry-After` (plafonnée à 5 s) avant le retry
- Budget de 20 requêtes maximum par run
- Anti-spam côté Flask : 1 run toutes les 5 minutes maximum (réponse 429 sinon)
- Réutilisation de la connexion HTTP (`requests.Session`, keep-alive) pour éviter de refaire
  la poignée de main HTTPS à chaque appel

## Planification

Les tâches planifiées PythonAnywhere étant réservées aux comptes payants, l'exécution planifiée
est assurée par une GitHub Action (`.github/workflows/scheduled-run.yml`, cron toutes les 15 minutes)
qui appelle l'endpoint `/run`. L'anti-spam côté Flask garantit au maximum 1 run toutes les 5 minutes.

## Métriques QoS mesurées

- Latence moyenne et p95 (sur environ 14 appels par run : 9 tests + 5 appels de mesure)
- Taux d'échec des tests (tests FAIL / total)
- Taux d'erreurs HTTP non voulues (timeout, 429, 5xx)
- Disponibilité du dernier run (UP si `GET /latest` répond 200)

## Premiers résultats observés

- Premier run : 9/9 tests réussis, API disponible, 0 % d'erreur HTTP
- Latence moyenne d'environ 310 ms, p95 d'environ 1 500 ms
- Interprétation : avec 14 appels, le p95 correspond pratiquement à l'appel le plus lent.
  Le premier appel est plus lent car il ouvre la connexion HTTPS (DNS, TLS, proxy PythonAnywhere).
  Après l'ajout de `requests.Session`, la connexion est réutilisée et la latence se stabilise.
  Un p95 élevé ponctuel n'indique donc pas une dégradation de l'API : c'est la tendance
  sur plusieurs runs (courbe du dashboard) qui compte.
