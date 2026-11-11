import json
import unittest

from ipss_utils.ipss_test import IpssTestCases

from app import create_app
import config

app = create_app(config.Config)

data = {


        "prodId": "5",
        "skuId": 1,
        "collectedPersonId": 1,
        "collectedAmout": "450",
        "desc": "No",
        "reason": "No",
        "isReturn": False

}


class AppTestCase(IpssTestCases):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        super(AppTestCase, self).setUp()

    def test_list_bank(self):
        response = self.client.get(
            "/inventory/InventoryRgistry/",

            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_single_get_bank(self):
        response = self.client.get(
            "/inventory/InventoryRgistry/1/",

            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        print(response.json)
        print(response.status_code)
        assert response.status_code == 200

    def test_create_bank(self):
        response = self.client.post(
            "/inventory/InventoryRgistry/",
            json=data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_delete_bank(self):
        response = self.client.delete(
            "/inventory/InventoryRgistry/1/",

            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_patch_bank(self):
        response = self.client.patch(
            "/inventory/InventoryRgistry/1/",
            json=data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_put_bank(self):
        response = self.client.put(
            "/inventory/InventoryRgistry/1/",
            json=data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(AppTestCase())
    unittest.TextTestRunner().run(suite)

