import json
import unittest

from ipss_utils.ipss_test import IpssTestCases

from app import create_app
import config

app = create_app(config.Config)

Created_to_data ={
  "joborderid": 10,
  "joborderproposalid": 1,
  "joborderno": "jo-001",
  "user_id": 1571656494371,
  "compcode": 1539147649705,
  "jo_status": "aceccpt",
  "type": "placement",
  "jo_doc": "2022-09-27 18:49:02.009317",
  "jo_valid_date": "2022-09-27 18:49:02.009317",
  "purchase_orderno": "poc -001",
  "jo_date": "2022-09-27 18:49:02.009317",
  "vendorid": 1,
  "companyname": "mani",
  "contactname": "tecgenzi",
  "emailid": "mani@gmail.com",
  "mobileno": "+91 8778411507",
  "ship_addline1": "90,saibaba colony",
  "ship_addline2": "raja anamalai road",
  "ship_district": "covai",
  "ship_pincode": "641011",
  "ship_city": "covai",
  "ship_state": "tamilnadu",
  "ship_country": "india",
  "jo_aql": "87.8",
  "description": "test data",
  "termsand_condition":"test"
  # "modified_by": "ithod@pgc.com",
  # "modified_on": "2022-09-27 18:49:02.009317",
  # "created_by": "ithod@pgc.com",
  # "created_on": "2022-09-27 18:49:02.009317",
  # "deleted": false,
  # "deleted_at": null
}


class AppTestCase(IpssTestCases):
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxOTgyNjE2NCwianRpIjoiMTYyMTg4ZGMtNWMzOS00Y2I4LTlhYWMtOTViMDRlZjc0MmYxIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6eyJ1c2VybmFtZSI6Iml0aG9kQHBnYy5jb20iLCJjb250cm9saWQiOjEsInByb2plY3RpZCI6IlRJUExQR0MiLCJmaW55ciI6IjIzLTI0IiwiZmlueXJfaWQiOjE2NDk2ODIyMDQ3NzgsImNvbXBjb2RlIjoiR0pJIiwiZGlzcGxheSI6IkdKIElOTk9WQVRJT05TIEFORCBURVhUSUxFIE5FVFdPUksgUFJJVkFURSBMSU1JVEVEIiwiY29tcG5hbWUiOiJHSiBJTk5PVkFUSU9OUyBBTkQgVEVYVElMRSBORVRXT1JLIFBSSVZBVEUgTElNSVRFRCIsImJicmFuY2giOiJTSVZBS0FTSSIsImFkZHJlc3MiOiIxLzQwNyxEUCAtMiwzJjQgU0lEQ08gSU5EVVNUUklBTCBFU1RBVEUsIFNVTEFLS0FSQUkiLCJnc3RubyI6IjMzQUFDQ0c2MTM2QzFaNCIsImNvbXBhbnlfaWQiOjE1MzkxNDc2NDk3MDUsInVzZXJpZCI6MTU3MTY1NjQ5NDM3MSwiZW1wX2lkIjpudWxsLCJ1c2VyX3JvbGUiOiJBZG1pbiJ9LCJuYmYiOjE3MTk4MjYxNjQsImV4cCI6MTcxOTkxMjU2NH0.eaU7N_AZ7oKVnDM7zyo17O4fZqCTdoppEfyWk9JJaIs"
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()
        super(AppTestCase, self).setUp()

    def test_list_job_Order(self):
        response = self.client.get(
            "/job_order/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_list_job_Order_single(self):
        response = self.client.get(
            "/job_order/10/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            }
        )
        assert response.status_code == 200

    def test_add_job_Order(self):
        response = self.client.post(
            "/job_order/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            },

            json=Created_to_data)
        assert response.status_code == 200

    def test_delete_job_Order(self):
        response = self.client.delete(
            "/job_order/2/",
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_patch_job_Order(self):
        response = self.client.patch(
            "/job_order/2/",
            json=Created_to_data,
            headers={
                'Authorization': f"Bearer {self.access_token}"
            })

        assert response.status_code == 200

    def test_put_job_Order(self):
        response = self.client.put(
            "/job_order/2/",
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
