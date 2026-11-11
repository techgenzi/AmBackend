import copy
import datetime

import requests
from flask import request
from flask_restx import Resource, abort

from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import text
from ..models.satge import Stage
from ipss_utils.decorators import login_required

from ..routes.stage import stage_api_route, single_stage_model, create_stage_response, stage_list_response, \
    update_stage_response
from .. import ipss_db, db_client
from ..floor_api_doc import search_filters

primary_key = 'floor_id'

def duplicate(table_name='',pkey={} ,data={}):
    sql_con = ''
    if data:
        for key, value in data.items():
            sql_con += f"{key} = :{key} and "

    if pkey:
        for key, value in pkey.items():
            sql_con += f"{key} != :{key} and "

    sql_query = text(f'''
    select * from {table_name} where {sql_con} deleted is not true
    ''')
    print(sql_query)
    val = query_to_dict(db_client.engine.execute(sql_query, **data, **pkey))
    if val:
        abort(409, "Already exist")
    return


@stage_api_route.route('/')
class StageApi(Resource):
    per_page = 20

    @stage_api_route.marshal_with(stage_list_response)
    @stage_api_route.doc(params={**list_api_params, **search_filters})
    @login_required()
    def get(self):
        """
        List of Products with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user', {})
        ccode = current_user.get('company_id')
        paged = int(request.args.get('paged')) if request.args.get('paged') else 1
        results_per_page = int(request.args.get('results_per_page')) if request.args.get(
            'results_per_page') else 20
        offset = (paged - 1) * results_per_page
        sql_con = ''
        stage_id = request.args.get('stage_id', None)
        if stage_id:
            sql_con += ' and stage_id=:stage_id '
        sql_query = text(f'''
               select * from stage
               where deleted is not true and compcode=:ccode {sql_con}
               order by stage_id desc
               limit :limit offset :offset
               ''')
        sql_query = query_to_dict(db_client.engine.execute(sql_query,
                                                           limit=results_per_page,
                                                           offset=offset,
                                                           ccode=ccode,
                                                           stage_id=stage_id
                                                           ))
        sql_count = text(f'''
               select count(*) from stage
               where deleted is not true and compcode=:ccode {sql_con}
               ''')
        sql_count = query_to_dict(db_client.engine.execute(sql_count,
                                                           ccode=ccode,
                                                           stage_id=stage_id
                                                           ))
        return {
            "total_results": sql_count[0].get('count', 0) if len(sql_count) else 0,
            "page": paged,
            "results_per_page": results_per_page,
            "results": sql_query
        }

    @login_required(permissions='stage.add')
    @stage_api_route.expect(single_stage_model)
    @stage_api_route.marshal_with(create_stage_response)
    def post(self):
        """
        Create Products record and return inserted id
        :return:
        """
        data = request.json
        stage_name = data.get('stage_name', None)
        cur = request.args.get('current_user', {})
        compcode = cur.get('company_id', None)
        duplicate(table_name='stage', data={'compcode': compcode, 'stage_name': stage_name})
        result = ipss_db.insert_record(model=Stage, values=data)
        return result


@stage_api_route.route('/<stage_id>/')
class StageUpdateApi(Resource):
    @staticmethod
    def update_record(data, stage_id):
        data.pop('stage_id', None)
        cur = request.args.get('current_user', {})
        stage_name = data.get('stage_name', None)
        compcode = cur.get('company_id', None)
        duplicate(table_name='stage', data={'compcode': compcode, 'stage_name': stage_name}, pkey={'stage_id': stage_id})
        result = ipss_db.update_record(
            model=Stage,
            condition=Stage.stage_id == stage_id,
            values=data
        )
        return result

    @stage_api_route.marshal_with(single_stage_model)
    @login_required(permissions='stage.view')
    def get(self, stage_id):
        """
        Read user record / single record
        :param id:
        :return:
        """

        user = Stage.query.filter_by(stage_id=int(stage_id)).first()
        return user

    @stage_api_route.expect(single_stage_model)
    @stage_api_route.marshal_with(update_stage_response)
    @login_required(permissions='stage.edit')
    def put(self, stage_id):
        """
        Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, stage_id)
        return response


    @stage_api_route.expect(single_stage_model)
    @stage_api_route.marshal_with(update_stage_response)
    @login_required(permissions='stage.edit')
    def patch(self, stage_id):
        """
        Partial Update Employees record
        :return:
        """
        data = request.json
        response = self.update_record(data, stage_id)
        return response

    @stage_api_route.marshal_with(update_stage_response)
    @login_required(permissions='stage.delete')
    def delete(self, stage_id):
        """
        Soft delete Products record
        TODO: Make soft delete
        :return:
        """

        result = ipss_db.update_record(
            model=Stage,
            condition=Stage.stage_id == stage_id,

            values={
                'deleted': True,
                'deleted_at': datetime.datetime.now()
            }
        )
        return result



@stage_api_route.route('/auto-post/')
class AutoPost(Resource):


    @login_required()
    def get(self):

        data = {"stages": [
    {
      "stage_id": 1,
      "target_per_hour": None,
      "rank_id": 1,
      "activities": [
        {
          "config_id": 1,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 2,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 3,
          "target_per_hour": None,
          "is_final_process": True
        }
      ]
    },
    {
      "stage_id": 2,
      "target_per_hour": None,
      "rank_id": 2,
      "activities": [
        {
          "config_id": 4,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 5,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 6,
          "target_per_hour": None,
          "is_final_process": True
        }
      ]
    },
    {
      "stage_id": 3,
      "target_per_hour": None,
      "rank_id": 3,
      "activities": [
        {
          "config_id": 7,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 8,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 9,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 10,
          "target_per_hour": None,
          "is_final_process": False
        },
        {
          "config_id": 11,
          "target_per_hour": None,
          "is_final_process": True
        }
      ]
    },
    {
      "stage_id": 4,
      "target_per_hour": None,
      "rank_id": 4,
      "activities": [
        {
          "config_id": 12,
          "target_per_hour": None,
          "is_final_process": True
        }
      ]
    },
    {
      "stage_id": 5,
      "target_per_hour": None,
      "rank_id": 5,
      "activities": [
        {
          "config_id": None,
          "target_per_hour": None,
          "is_final_process": False
        }
      ]
    },
    {
      "stage_id": 6,
      "target_per_hour": None,
      "rank_id": 6,
      "activities": [
        {
          "config_id": None,
          "target_per_hour": None,
          "is_final_process": False
        }
      ]
    },
    {
      "stage_id": 7,
      "target_per_hour": None,
      "rank_id": 7,
      "activities": [
        {
          "config_id": None,
          "target_per_hour": None,
          "is_final_process": False
        }
      ]
    }
  ]}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer eyJhbGciO"
                             "iJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmc"
                             "mVzaCI6ZmFsc2UsImlhdCI6MTc2ODE5ODMyOCwia"
                             "nRpIjoiMmU5N2ZlMDItMjk4OS00ZTNjLWIwN2YtYzU4"
                             "NGU1MmZkNmEwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6I"
                             "mZhY3RvcnloZWFkIiwibmJmIjoxNzY4MTk4MzI4LCJleH"
                             "AiOjE3NjgyODQ3MjgsInVzZXJuYW1lIjoiZmFjdG9yeW"
                             "hlYWQiLCJjb250cm9saWQiOjEsInByb2plY3RpZCI6bnV"
                             "sbCwiZmlueXIiOm51bGwsImZpbnlyX2lkIjowLCJjb21w"
                             "Y29kZSI6IkZlc3RvbiIsImRpc3BsYXkiOiJGZXN0YSIsIm"
                             "NvbXBuYW1lIjoiRmVzdG9uIFNFViBUZWNobm9sb2dpZXMiLCJ"
                             "iYnJhbmNoIjoiQ2hlbm5haSIsImFkZHJlc3MiOiI5Ny84MCwgVmF"
                             "uYWdhcmFtIEFtYmF0dHVyIFJkLENoZW5uYWlcbiIsImdzdG5vIj"
                             "pudWxsLCJjb21wYW55X2lkIjoxNTUsInRlbmFudF9pZCI6MTE"
                             "1LCJhdHRyaWJ1dGVzIjpudWxsLCJ1c2VyaWQiOjE1ODI1MzY5Nz"
                             "U3OTYsImVtcF9pZCI6bnVsbCwidXNlcl9yb2xlIjoiQWRtaW4ifQ.EY3eC"
                             "4-mbc62bx7BK6d7hKp6vvwCQKxHPpGw0LvNCu4"
        }
        url = "https://omniplus-api.techgenzi.com/am-prod_stages/"

        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": "Bearer YOUR_TOKEN_HERE"
        # }

        ans = {}

        for product_id in range(0, 347):
            payload = copy.deepcopy(data)
            payload["product_id"] = product_id

            try:
                response = requests.post(
                    url=url,
                    headers=headers,
                    json=payload,  # ✅ IMPORTANT
                    timeout=10
                )
                response_data = response.json()
                print(response_data, " product_id:",product_id)
                if response_data.get("Success") is True:
                    ans[product_id] = "Success"
                else:
                    ans[product_id] = "Failure"

            except Exception as e:
                ans[product_id] = f"Error: {str(e)}"

        return ans

######################################################################



