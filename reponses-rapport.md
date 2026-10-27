question 1:
En cas de succès, POST /payments retourne un objet JSON contenant l’identifiant de la transaction créée.
<br/>
question 2:
la requête contient dans son corps les informations de la carte de crédit:
``` json
{
    "cardNumber": 9999999999999,
    "cardCode": 123,
    "expirationDate": "2030-01-05"
}
```
![request-q2](image.png)

<br/>
Dans une architecture SOA, le format dépend du protocole utilisé. Un service SOA utilisant SOAP recevrait généralement ces informations dans une enveloppe XML plutôt qu’en JSON. Toutefois, un service SOA peut aussi exposer une API REST et accepter le même format JSON.

<br/>

La requête retourne le statut HTTP 200 OK et le corps:
``` json
{
  "is_paid": true,
  "order_id": 5,
  "payment_id": 5
}
```