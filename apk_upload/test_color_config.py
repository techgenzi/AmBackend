import json
import unittest

from ipss_utils.ipss_test import IpssTestCases

from app import create_app
import config

app = create_app(config.Config)

Test_data = {
      "color_id": 1636349176086,
      "color_name": "Test Colour",
      "description": "This is a test color",
      "created_on": "2021-12-20 09:44:31",
      "created_by": "renuga@gjpgc.com",
      "modified_on": "2021-12-20 09:44:31",
      "modified_by": "renuga@gjpgc.com",
      "deleted": "",
      "deleted_at": ""
}


class AppTestCase(IpssTestCases):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        super(AppTestCase, self).setUp()

    def test_getall_color(self):
        response = self.client.get(
            "/color_config/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_singleget_color(self):
        response = self.client.get(
            "/color_config/1",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_post_color(self):
        response = self.client.post(
            "/color_config/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            },
            json=Test_data)
        assert response.status_code == 200

    def test_delete_color(self):
        response = self.client.delete(
            "/color_config/1",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_patch_color(self):
        response = self.client.patch(
            "/color_config/1",
            json=Test_data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_put_color(self):
        response = self.client.put(
            "/color_config/1",
            json=Test_data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(AppTestCase())
    unittest.TextTestRunner().run(suite)
