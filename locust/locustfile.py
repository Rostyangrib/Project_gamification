import uuid
from datetime import datetime, timedelta
from locust import HttpUser, task, between
import random

USERS_CREDENTIALS = [
    {"email": "u1@user.com", "password": "rost_user"},
    {"email": "u2@user.com", "password": "rost_user"},
    {"email": "manager@work.com", "password": "999999"},
    {"email": "sss@ss.s", "password": "999999"},  # админ
]

ADMIN_EMAILS = {"sss@ss.s", "manager@work.com"}

class BookingSystemUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.credentials = random.choice(USERS_CREDENTIALS)
        self.is_admin = (self.credentials["email"] in ADMIN_EMAILS)
        self.access_token = None
        self.current_competition_id = None
        self.login()

    def login(self):
        resp = self.client.post("/login", json=self.credentials, name="/login AUTH")
        if resp.status_code == 200:
            try:
                self.access_token = resp.json().get("access_token")
            except Exception:
                resp.failure("Ошибка парсинга access_token")

    def _ensure_auth(self):
        if not self.access_token:
            self.login()

    @task(5)
    def get_tasks(self):
        self._ensure_auth()
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/tasks", headers=headers, name="/tasks (auth)")

    @task(3)
    def post_tasks(self):
        if not self.is_admin:
            return
        self._ensure_auth()
        if not self.access_token:
            return

        task_id = str(uuid.uuid4())[:8]
        title = f"Locust Task {task_id}"
        description = f"Auto-generated task for load testing — {task_id}"

        now = datetime.utcnow()
        due = now + timedelta(days=random.randint(1, 7))
        due_iso = due.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        payload = {
            "status_id": 1,
            "title": title,
            "description": description,
            "ai_analysis_metadata": {"source": "locust"},
            "estimated_points": 0,
            "due_date": due_iso
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.client.post("/task", json=payload, headers=headers, name="/task (create)")

    @task(3)
    def get_users_me(self):
        self._ensure_auth()
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            with self.client.get("/users/me", headers=headers, name="/users/me", catch_response=True) as resp:
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        self.current_competition_id = data.get("current_competition_id")
                    except Exception:
                        resp.failure("Не удалось распарсить /users/me")

    @task(2)
    def get_competitions(self):
        if not self.is_admin:
            return
        self._ensure_auth()
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/competitions", headers=headers, name="/competitions (admin)")

    @task(1)
    def post_competitions(self):
        if not self.is_admin:
            return
        self._ensure_auth()
        if not self.access_token:
            return

        comp_id = str(uuid.uuid4())[:8]
        title = f"Locust Competition {comp_id}"

        now = datetime.utcnow()
        start = now + timedelta(hours=random.randint(1, 24))
        end = start + timedelta(days=random.randint(3, 14))

        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        end_iso = end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        payload = {
            "title": title,
            "start_date": start_iso,
            "end_date": end_iso
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.client.post("/competitions", json=payload, headers=headers, name="/competitions (create admin)")

    @task(2)
    def get_leaderboard(self):
        self._ensure_auth()
        if self.access_token and self.current_competition_id:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            url = f"/leaderboard/{self.current_competition_id}"
            self.client.get(url, headers=headers, name="/leaderboard/{id}")

    @task(1)
    def get_users_only(self):
        if not self.is_admin:
            return
        self._ensure_auth()
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/users/only", headers=headers, name="/users/only (admin)")

    @task(1)
    def get_root(self):
        self.client.get("/", name="/ (public)")