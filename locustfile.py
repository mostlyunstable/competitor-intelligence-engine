import random
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Executed when a simulated user starts."""
        pass

    @task(3)
    def view_dashboard(self):
        """Simulates querying the dashboard stats endpoint."""
        self.client.get("/dashboard/stats")

    @task(2)
    def view_competitors(self):
        """Simulates fetching the list of competitors."""
        self.client.get("/competitors/?skip=0&limit=50")

    @task(1)
    def search_competitors(self):
        """Simulates searching for a competitor."""
        terms = ["stripe", "google", "github", "linear"]
        self.client.get(f"/competitors/?search={random.choice(terms)}")

    @task(1)
    def create_competitor(self):
        """Simulates adding a new competitor to trigger backend scraping and AI."""
        domains = [
            f"test-{random.randint(1000,9999)}.example.com",
            f"company-{random.randint(1000,9999)}.com"
        ]
        payload = {
            "name": f"Load Test Co {random.randint(1,10000)}",
            "domain": random.choice(domains)
        }
        self.client.post("/competitors/", json=payload)
