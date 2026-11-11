#
# import datetime
# import os
# import uuid
#
# import boto3
# from flask import request
# from flask_restx import Resource
# from ipss_utils.decorators import login_required
#
# from .. import ipss_db
# from ..models.grnotes import DocUpload
# from ..routes.s3upload import doc_upload_api_route, doc_upload_user_model
#
# BUCKET_NAME = os.environ.get('S3_BUCKET')
# session = boto3.session.Session()
# client = session.client('s3', endpoint_url=os.getenv("S3_ENDPOINT_URL"))
#
#
# @doc_upload_api_route.route('/')
# class UploadResource(Resource):
#
#     @doc_upload_api_route.expect(doc_upload_user_model, validate=True)
#     @login_required()
#     def post(self):
#         """
#         Create user record and return inserted ID
#         :return:
#         """
#         current_user = request.args.get('current_user')
#         user_id = current_user.get('user_id')
#         data = request.json
#         # Create random unique uuid4
#         file_key = uuid.uuid4()
#         today = datetime.datetime.now()
#         s3_key = os.getenv("S3_FOLDER", "techaton") + '/{:02d}'.format(today.year) + "/" + '{:02d}'.format(today.month) \
#                  + "/" + str(file_key) + '{:02d}'.format(today.second) + '{:02d}'.format(today.day)
#         data['captain_id'] = user_id
#         # Auto created at
#         data['created_on'] = datetime.datetime.now()
#         content_type = data.get('content_type')
#         data['s3_key'] = s3_key
#         result = ipss_db.insert_record(DocUpload, data)
#         media_id = result.get('primary_key_id')[0]
#         fields = {"acl": "public-read", "Content-Type": content_type}
#         conditions = [{"acl": "public-read"}, {"Content-Type": content_type}]
#
#         response = client.generate_presigned_post(
#             Bucket=BUCKET_NAME,
#             Key=str(s3_key),
#             Fields=fields,
#             Conditions=conditions)
#         # print(response)
#         return {
#             'media_key': s3_key,
#             'media_id': str(media_id),
#             's3_url': "https://{0}/".format(os.getenv("S3_BUCKET_DOMAIN")),
#             'data': response
#         }
