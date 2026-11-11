import json
import unittest
from app import create_app
import config

app = create_app(config.Config)


class TestData:
    USERNAME = "ithod@pgc.com"
    PASSWORD = "edp123"


class AppTestCase(unittest.TestCase, TestData):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        response = self.client.post("/users/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        self.access_token = response.json['access_token']

    def tearDown(self):
        self.ctx.pop()

    def test_list_users(self):
        response = self.client.get(
            "/users/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200


if __name__ == "__main__":
    unittest.main()
