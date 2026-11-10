import random
import uuid

from locust import HttpUser, task, between


class UserLifecycleTest(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_and_delete_user(self):
        payload = {
            "name": "Test Locust",
            "email": f"locust-{uuid.uuid4()}@example.com",
            "user_type_id": random.randint(1, 3)
        }

        with self.client.post(
            "/users",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure(
                    f"Création échouée : HTTP {response.status_code} - {response.text}"
                )
                return

            try:
                user_id = response.json().get("user_id")
                if not isinstance(user_id, int) or user_id <= 0:
                    response.failure("Réponse sans user_id valide")
                    return
            except (ValueError, AttributeError):
                response.failure(f"Création échouée : HTTP {response.status_code} - {response.text}")
                return

        with self.client.delete(
            f"/users/{user_id}",
            name="/users/{id}",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Suppression échouée : HTTP {response.status_code} - {response.text}"
                )
                return

            try:
                if response.json().get("deleted") is not True:
                    response.failure(f"Suppression échouée : HTTP {response.status_code} - {response.text}")
            except (ValueError, AttributeError):
                response.failure(f"Suppression échouée : HTTP {response.status_code} - {response.text}")