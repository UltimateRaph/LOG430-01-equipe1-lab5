"""Measure the creation and deletion of disposable Store Manager users."""

from random import randint
from uuid import uuid4

from locust import HttpUser, between, task


class StoreManagerUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_and_delete_user(self):
        payload = {
            "name": "Compte test Locust",
            "email": f"labo07-locust-{uuid4().hex}@example.com",
            "user_type_id": randint(1, 3),
        }
        with self.client.post("/users", json=payload, catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Création : HTTP {response.status_code}")
                return
            try:
                user_id = response.json()["user_id"]
            except (ValueError, KeyError, TypeError):
                response.failure("Identifiant absent dans la réponse de création")
                return
            if type(user_id) is not int or user_id < 1:
                response.failure("Identifiant invalide dans la réponse de création")
                return

        with self.client.delete(
            f"/users/{user_id}", name="/users/{id}", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Suppression : HTTP {response.status_code}")
                return
            try:
                deleted = response.json()["deleted"]
            except (ValueError, KeyError, TypeError):
                response.failure("Résultat absent dans la réponse de suppression")
                return
            if deleted is not True:
                response.failure("Suppression non confirmée")
