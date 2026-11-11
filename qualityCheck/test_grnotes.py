import json
import unittest

from ipss_utils.ipss_test import IpssTestCases

from app import create_app
import config

app = create_app(config.Config)

Created_to_data = {
      # "grnotesid": 53,
      # "grn_no": "GRN-00001",
      # "user_id": 1571656494371,
      # "compcode": 1539147649705,

      "type": "palacement",
      "grndate": "2022-10-09 09:14:00",
      "inviceno": "1234",
      "inviceid": "test",
      "grn_description": "test"
    }


class AppTestCase(IpssTestCases):

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        super(AppTestCase, self).setUp()

    def test_list_GRNotes(self):
        response = self.client.get(
            "/grnotes/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_list_GRNotes_single(self):
        response = self.client.get(
            "/grnotes/1/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_add_GRNotes(self):
        response = self.client.post(
            "/grnotes/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            },

            json=Created_to_data)
        assert response.status_code == 200

    def test_delete_GRNotes(self):
        response = self.client.delete(
            "/grnotes/2/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_patch_GRNotes(self):
        response = self.client.patch(
            "/grnotes/2/",
            json=Created_to_data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_put_GRNotes(self):
        response = self.client.put(
            "/grnotes/2/",
            json=Created_to_data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200


if __name__ == "__main__":
    suite = unittest.TestSuite()
    unittest.main()
    suite.addTest(AppTestCase())
    unittest.TextTestRunner().run(suite)
