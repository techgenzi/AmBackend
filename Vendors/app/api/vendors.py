import datetime

from flask import request, abort
from flask_restx import Resource
from ipss_utils.decorators import login_required
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text

from .. import ipss_db, db_client

from ..api_doc import type_filter
from ..models.vendors import Vendors

from ..routes.vendors import vendors_api_route, vendors_list_response, create_vendors_response, \
    update_vendors_model, update_vendors_response
from ..routes.vendors import create_vendors_model, get_vendors_response

# Primary key name
primary_key = 'vendorid'




@vendors_api_route.route('/')
class VendorsApi(Resource):
    per_page = 20

    @vendors_api_route.marshal_with(vendors_list_response)
    @vendors_api_route.doc(params=type_filter)
    @login_required()
    def get(self):
        """
        List of vendors with pagination
        TODO: Search vendors details
        :return:
        """
        current_user = request.args.get('current_user')
        user_id = current_user.get('user_id')
        query = Vendors.query.order_by(Vendors.vendorid.desc())
        if request.args.get('type', None):
            query = query.filter_by(type=request.args.get('type'))
        if request.args.get('vendorid', None):
            query = query.filter_by(vendorid=request.args.get('vendorid'))
        response = ipss_db.paginated_results(
            model=Vendors,
            query=query,
            primary_key=primary_key
        )
        return response

    @login_required()
    @vendors_api_route.expect(create_vendors_model)
    # @vendors_api_route.marshal_with(create_vendors_response)
    def post(self):
        """
        Create a vendor record and return the inserted id
        :return: Response
        """
        current_user = request.args.get('current_user')
        if not current_user:
            abort(401, "Unauthorized: No current user provided")

        compcode = current_user.get('company_id')
        data = request.json

        if not data:
            abort(400, "Bad Request: No data provided for creating a vendor record")

        data['user_id'] = current_user.get('userid')

        # Remove primary key if exists
        data.pop('vendorid', None)
        result=text('''
        select * from (SELECT
            CASE
                WHEN REPLACE(UPPER(vendor.emailid), ' ', '') = REPLACE(UPPER(:emailid), ' ', '') and emailid <>''THEN emailid
                --emailid = :emailid and emailid <>''THEN emailid
                ELSE NULL
            END AS "Email Id",
            CASE
                WHEN REPLACE(UPPER(vendor.gstno), ' ', '') = REPLACE(UPPER(:gstno), ' ', '') and gstno<>'' THEN gstno
                --gstno = :gstno and gstno<>'' THEN gstno
                when gstno='' then NULL
                ELSE NULL
            END AS "GST Number",
            CASE
                WHEN REPLACE(UPPER(vendor.mobileno), ' ', '') = REPLACE(UPPER(:mobileno), ' ', '') and mobileno<>'' THEN panno
                --mobileno = :mobileno and mobileno<>'' THEN panno
                ELSE NULL
            END AS "Mobile Number"
        FROM vendor 
        where deleted is not true and compcode=:compcode and 
        type=:ven_type
        ) as temps
    where "Email Id" is not null or "GST Number" is not null or "Mobile Number" is not null
    LIMIT 1;
        ''')
        result=query_to_dict(db_client.engine.execute(result,compcode=compcode,
                                                      ven_type=data.get('type',''),
                                                      mobileno=data.get('mobileno',''),
                                                      gstno=data.get('gstno',''),
                                                      emailid=data.get('emailid','')
                                                      ))
        if len(result):
            non_null_key = next((key for key, value in result[0].items() if value is not None), None)
            abort(409, f"This {non_null_key} is Already Exist")
        def check_duplicate(query, key_name, key_value,cust_type=''):
            result = db_client.engine.execute(query, {key_name: key_value, 'compcode': compcode,'cust_type':cust_type},
                                               )
            result_dict = query_to_dict(result)
            return len(result_dict) > 0

        if data.get('mobileno') is not None:
            if check_duplicate(text(
                    "SELECT * FROM vendor "
                    "WHERE REPLACE(UPPER(vendor.mobileno), ' ', '') = REPLACE(UPPER(:mobileno), ' ', '') AND "
                    "deleted = false AND compcode=:compcode "
                    "and type=:cust_type LIMIT 1"),
                    key_name='mobileno',key_value= data['mobileno'],cust_type=data.get('type','')):
                abort(409, "This Mobile Number is Already Exist")

        if data.get('emailid') is not None:
            if check_duplicate(text(
                    "SELECT * FROM vendor "
                    "WHERE REPLACE(UPPER(vendor.emailid), ' ', '') = REPLACE(UPPER(:emailid), ' ', '') AND "
                    "deleted = false AND compcode=:compcode and type=:cust_type LIMIT 1"),
                    'emailid', data['emailid'].upper(),cust_type=data.get('type','')):
                abort(409, "This Email Id is Already Exist")

        if data.get('gstno') is not None:
            if check_duplicate(text(
                    "SELECT * FROM vendor "
                    "WHERE REPLACE(UPPER(vendor.gstno), ' ', '') = REPLACE(UPPER(:gstno), ' ', '') AND "
                    "deleted = false AND compcode=:compcode and type=:cust_type LIMIT 1"),
                    'gstno', data['gstno'].upper(),cust_type=data.get('type','')):
                abort(409, "This GST Number is Already Exist")

        # Additional checks can be added if needed for other fields like PAN number

        # Assuming the following function for inserting records into the database
        result = ipss_db.insert_record(model=Vendors, values=data)

        return ipss_db.created_response(
            result=result,
            message="Vendor record has been created successfully",
            primary_key="vendorid"
        )


@vendors_api_route.route('/<vendors_id>/')
class VendorsUpdateApi(Resource):
    @staticmethod
    def update_record(data, vendors_id):
        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id')
        # data.pop('vendorid', None)
        vendor = Vendors.query.filter_by(vendorid=vendors_id).first().to_dict()
        print("aaa", vendor)
        vendor_type = vendor.get('type')
        print("vennn", vendor_type)
        # vendor
        # filtered_vendor = {key: value for key, value in data.items() if key not in vendor or data[key] != vendor[key]}
        # filtered_vendor.update({'type': vendor.get('type')})
        # print("asd", filtered_vendor)
        # check = DuplicationCheck(data=filtered_vendor, compcode=compcode)
        # if check:
        #     print("check", check)
        #     return check
        if 'emailid' in data and data['emailid'] is not None:
            email_id = data['emailid'].upper()
            value_query = text(
                "SELECT * FROM vendor "
                "WHERE REPLACE(UPPER(vendor.emailid), ' ', '') = REPLACE(UPPER(:emailid), ' ', '') "
                "AND deleted is not true AND vendor.vendorid != :vendorid AND vendor.type = :vendor_type AND compcode = :compcode LIMIT 1"
            )
            value_detail = query_to_dict(
                db_client.engine.execute(
                    value_query,
                    vendorid=vendors_id,
                    vendor_type=vendor_type,
                    emailid=email_id,
                    compcode=compcode
                )
            )
            if value_detail:
                return {"success": False, "message": "This Email Id is Already Exist"}, 409

            # Check for mobileno duplication
        if 'mobileno' in data and data['mobileno'] is not None:
            mobile_no = data['mobileno']
            mobile_query = text(
                "SELECT * FROM vendor "
                "WHERE REPLACE(vendor.mobileno, ' ', '') = REPLACE(:mobileno, ' ', '') "
                "AND deleted is not true AND vendor.vendorid != :vendorid AND vendor.type = :vendor_type AND compcode = :compcode LIMIT 1"
            )
            mobile_detail = query_to_dict(
                db_client.engine.execute(
                    mobile_query,
                    vendorid=vendors_id,
                    vendor_type=vendor_type,
                    mobileno=mobile_no,
                    compcode=compcode
                )
            )
            if mobile_detail:
                return {"success": False, "message": "This Mobile Number is Already Exist"}, 409

            # Check for gstno duplication
        if 'gstno' in data and data['gstno'] is not None:
            gst_no = data['gstno'].upper()
            gst_query = text(
                "SELECT * FROM vendor "
                "WHERE REPLACE(UPPER(vendor.gstno), ' ', '') = REPLACE(UPPER(:gstno), ' ', '') "
                "AND deleted is not true AND vendor.vendorid != :vendorid AND vendor.type = :vendor_type AND compcode = :compcode LIMIT 1"
            )
            gst_detail = query_to_dict(
                db_client.engine.execute(
                    gst_query,
                    vendorid=vendors_id,
                    vendor_type=vendor_type,
                    gstno=gst_no,
                    compcode=compcode
                )
            )
            if gst_detail:
                return {"success": False, "message": "This GST Number is Already Exist"}, 409

            # No duplicate entries found, update the record
        result = ipss_db.update_record(
            model=Vendors,
            condition=Vendors.vendorid == vendors_id,
            values=data
        )
        return result

    @vendors_api_route.marshal_with(get_vendors_response)
    @login_required()
    def get(self, vendors_id):
        """
        Read user record / single record
        :param vendors_id:
        :return:
        """
        current_user = request.args.get('current_user')
        user_id = current_user.get('user_id')
        user = Vendors.query.filter_by(vendorid=vendors_id).first()
        return user

    @vendors_api_route.expect(update_vendors_model)
    @vendors_api_route.marshal_with(update_vendors_response)
    @login_required()
    def put(self, vendors_id):
        """
        Update vendors record
        :return:
        """
        current_user = request.args.get('current_user')
        user_id = current_user.get('user_id')
        data = request.json
        response = self.update_record(data, vendors_id)
        return response

    @vendors_api_route.expect(update_vendors_model)
    @vendors_api_route.marshal_with(update_vendors_response)
    @login_required()
    def patch(self, vendors_id):
        """
        Partial Update vendors record
        :return:
        """
        current_user = request.args.get('current_user')
        user_id = current_user.get('user_id')
        data = request.json
        response = self.update_record(data, vendors_id)
        return response

    @vendors_api_route.marshal_with(update_vendors_response)
    @login_required()
    def delete(self, vendors_id):
        """
        Soft delete vendors record
        TODO: Make soft delete
        :return:
        """
        current_user = request.args.get('current_user')
        user_id = current_user.get('user_id')
        result = ipss_db.update_record(
            model=Vendors,
            condition=Vendors.vendorid == vendors_id,
            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result

@vendors_api_route.route('/drop_down/')
class VendorDropDown(Resource):

    @login_required()
    def get(self):

        current_user = request.args.get('current_user')
        compcode = current_user.get('company_id')
        type = request.args.get('type', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', start_date)

        sql_con = ''

        if type:
            sql_con += ' and type=:type '

        if start_date:
            sql_con += ' and cp.order_date::date between cast(:start_date as date) and cast(:end_date as date) '

        query = text(f'''
            select companyname,vendorid,contactname from vendor
            join customer_purchase cp on cp.customer_id=vendor.vendorid
            where compcode=:compcode and deleted is not true {sql_con}
            order by vendorid desc
        ''')

        result = query_to_dict(db_client.engine.execute(query, compcode=compcode,
                                                        type=type,
                                                        start_date=start_date,
                                                        end_date=end_date))

        return {'success': True, 'data': result}











#
#
# from .. import rest_api
# # from flask_restx import Api
# from werkzeug.datastructures import FileStorage
# # api = Api(app, title="Excel API")
#
# upload_parser = rest_api.parser()
# upload_parser.add_argument(
#     'file',
#     location='files',
#     type=FileStorage,
#     required=True
# )
#
# import pandas as pd
# import json
#
#
# def read_excel_safely(file):
#     filename = file.filename.lower()
#
#     if filename.endswith('.xlsx'):
#         return pd.read_excel(file, engine='openpyxl')
#
#     elif filename.endswith('.xls'):
#         return pd.read_excel(file, engine='xlrd')
#
#     elif filename.endswith('.csv'):
#         return pd.read_csv(file)
#
#     else:
#         raise ValueError("Unsupported file format")
#
# from datetime import datetime

# def transform_vendor_row(row, user_id, compcode, created_by):
#     return { # auto-generated if sequence/identity
#         "store_id": store_id,
#         "compcode": compcode,
#
#         "product_id": row.get("SUPPLIER ORGANIZATION"),
#         "contactname": row.get("CONTACT PERSON"),
#         "emailid": row.get("EMAIL"),
#         "mobileno": str(row.get("CONTACT NUMBER")) if row.get("CONTACT NUMBER") else None,
#         "gstno": row.get("GST Details"),
#
#         "bill_addline1": row.get("ADDRESS"),
#         "bill_pincode": int(row.get("PINCODE")) if row.get("PINCODE") else None,
#         "bill_country": "India",
#
#         # ✅ Store unmapped fields safely
#         "asset_attributes": {
#             "supplier_code": row.get("SUPPlIER ID"),
#             "source": "excel_import"
#         },
#
#         "created_by": created_by,
#         "created_on": datetime.utcnow(),
#         "deleted": False
#     }

#
# @vendors_api_route.route('/excel_upload')
# class EXCELUPLOAD(Resource):
#
#     @vendors_api_route.expect(upload_parser)
#     @vendors_api_route.doc(consumes=['multipart/form-data'])
#     def post(self):
#
#         # Read excel file
#         file = request.files.get("file")
#         if not file:
#             return {"error": "File missing"}, 400
#
#         try:
#             if file.filename.lower().endswith(".xlsx"):
#                 df = pd.read_excel(file, engine="openpyxl")
#             elif file.filename.lower().endswith(".csv"):
#                 df = pd.read_csv(file)
#             else:
#                 return {"error": "Unsupported file format"}, 400
#         except Exception as e:
#             return {"error": f"File read failed: {str(e)}"}, 400
#
#         df = df.where(pd.notnull(df), None)
#
#         excel_rows = df.to_dict(orient="records")
#
#         if not excel_rows:
#             return {"error": "Excel file empty"}, 400
#
#         # ---------- 2. Transform Excel → DB rows ----------
#         vendor_rows = []
#         now = datetime.utcnow()
#
#         # pprint(excel_rows)
#         # return
#
#         store_id = 1
#
#         query = text("""
#             INSERT INTO store_product (store_id, product_id, product_count, compcode, created_by, created_on)
#             SELECT :store_id, p.product_id, :product_count AS product_count, :compcode, :created_by, :created_on
#             FROM products p
#             WHERE p.sku_id = :product_code
#             ON CONFLICT (store_id, product_id)
#             DO UPDATE
#             SET product_count = store_product.product_count + EXCLUDED.product_count
#         """)
#
#         store_id = 1
#         compcode = 155
#         data = excel_rows
#         try:
#             for item in data:
#                 db_client.session.execute(
#                     query,
#                     {
#                         "store_id": store_id,
#                         "product_code": item["Product Code"],
#                         "product_count": item["Stock Qty"],
#                         'compcode': compcode,
#                         'created_by': "System",
#                         'created_on': now
#                     }
#                 )
#
#             db_client.session.commit()
#         except Exception as e:
#             db_client.session.rollback()
#             return {"error": str(e)}, 400
#         # for i, row in enumerate(excel_rows, start=1):
#         #     if not row.get("SUPPLIER ORGANIZATION"):
#         #         return {"error": f"Row {i}: SUPPLIER ORGANIZATION missing"}, 400
#         #
#         #     vendor_rows.append({
#         #         "compcode": 155,
#         #         "type": "Vendor",
#         #         "companyname": row.get("SUPPLIER ORGANIZATION"),
#         #         "contactname": row.get("CONTACT PERSON"),
#         #         "emailid": row.get("EMAIL"),
#         #         "mobileno": str(row.get("CONTACT NUMBER")) if pd.notna(row.get("CONTACT NUMBER")) else None,
#         #         "gstno": row.get("GST Details"),
#         #
#         #         "bill_addline1": row.get("ADDRESS"),
#         #         "bill_pincode": (
#         #             int(row["PINCODE"])
#         #             if pd.notna(row.get("PINCODE"))
#         #             else None
#         #         ),
#         #         "ship_pincode": (
#         #             int(row["PINCODE"])
#         #             if pd.notna(row.get("PINCODE"))
#         #             else None
#         #         ),
#         #         "bill_country": "India",
#         #
#         #         "asset_attributes": {
#         #             "supplier_code": row.get("SUPPlIER ID"),
#         #             "imported_via": "excel"
#         #         },
#         #
#         #         "created_by": "SYSTEM",
#         #         "created_on": now,
#         #         "deleted": False
#         #     })
#         #
#         # print(vendor_rows,len(vendor_rows))
#         # try:
#         #     db_client.session.bulk_insert_mappings(Vendors, vendor_rows)
#         #     db_client.session.commit()
#         # except Exception as e:
#         #     db_client.session.rollback()
#         #     return {
#         #         "error": str(e)
#         #     }
#
#
#         # ✅ return response (Swagger will show JSON)
#         return {
#             "message": "Excel uploaded successfully"
#         }, 200