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
#         media_id = 1
#         v = ipss_db.document_upload(data.get('content_type'), media_id)
#         return v
