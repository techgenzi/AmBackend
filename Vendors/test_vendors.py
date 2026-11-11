import json
import unittest

from ipss_utils.ipss_test import IpssTestCases

from app import create_app
import config

app = create_app(config.Config)

Created_to_vendors = {
      "type": "fullfillment",
      "companyname": "techgenzi",
      "contactname": "venkat",
      "emailid": "venki474@gmail.com",
      "mobileno": "8493949444",
      "gstno": "3dh78",
      "panno": "8gsff042k",
      "bill_addline1": "90, rajaannamalai road",
      "bill_addline2": "saibaba_colony",
      "bill_district": "coiambatture",
      "bill_pincode": 624401,
      "bill_city": "covai",
      "bill_state": "tamilnadu",
      "bill_country": "india",
      "ship_addline1": "90,raja annamalai road",
      "ship_addline2": "saibaba_colony",
      "ship_district": "covai",
      "ship_pincode": 641011,
      "ship_city": "coiambatture",
      "ship_state": "tamilnadu",
      "ship_country": "india"
    }


class AppTestCase(IpssTestCases):

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        super(AppTestCase, self).setUp()

    def test_list_vendors(self):
        response = self.client.get(
            "/vendors/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_list_vendors_single(self):
        response = self.client.get(
            "/vendors/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_add_vendors(self):
        response = self.client.post(
            "/vendors/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            },

            json=Created_to_vendors)
        assert response.status_code == 200

    def test_delete_vendors(self):
        response = self.client.delete(
            "/vendors/140116/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_patch_vendors(self):
        response = self.client.patch(
            "/vendors/140116/",
            json=Created_to_vendors,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_put_vendors(self):
        response = self.client.put(
            "/vendors/140116/",
            json=Created_to_vendors,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200




if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(AppTestCase())
    unittest.TextTestRunner().run(suite)
