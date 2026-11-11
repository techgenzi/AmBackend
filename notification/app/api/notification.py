import datetime
from flask import request, session
from flask_jwt_extended import current_user
from flask_restx import Resource
# from .. import ipss_db
from ipss_utils.ipss_api_doc import list_api_params, search_params
from ipss_utils.ipss_db import query_to_dict
from ipss_utils.decorators import login_required
from sqlalchemy import text

# from sqlalchemy import and_, text
from ..routes.notification import notification_api_route, notification_company_list_response, \
    notification_company_model, notification_user_list_response, notification_user_model, \
    notification_user_message_list_response
from .. import ipss_db, db_client
from .errorhandling import map_sqlalchemy_error_to_http_status
from ..models.notification import NotificationCompany, NotificationUser, NotificationUserMessage


@notification_api_route.route('/notification_company')
class NotificationApi(Resource):
    per_page = 20
    @notification_api_route.marshal_with(notification_company_list_response)
    @notification_api_route.doc(params=list_api_params)
    @login_required()
    def get(self):
        """
        List of job_dc_order with pagination
        TODO: Search
        :return:
        """
        current_user = request.args.get('current_user')
        company_id = current_user.get('company_id')
        try:
            query = text('''
                select nc.id,nc.action_id,na.action_name,nc.deleted,
                 count(*) over() as total_count
                 from notification_company as nc 
                left join notification_action as na on nc.action_id = na.action_id
                where nc.deleted is not true and nc.company_id = :company_id
            ''')

            result = query_to_dict(db_client.engine.execute(query,
                                                            company_id= company_id))

            return {
                'success': True,
                'total_results': result[0]['total_count'] if result else 0,
                'results': result
            }

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)

    @login_required()
    @notification_api_route.expect(notification_company_model)
    def post(self):

        current_user = request.args.get('current_user')
        company_id = current_user.get('company_id')
        data = request.json
        s = db_client.session
        try:
            cc = {
                'company_id': company_id,
                'created_by': current_user.get('username'),
                'created_on': datetime.datetime.now()
            }

            updated_cc = {
                'modified_by': current_user.get('username'),
                'modified_on': datetime.datetime.now()
            }
            post_data = []
            update_data = []
            for item in data:
                if item.get('id'):
                    update_data.append({**item,**updated_cc})
                else:
                    post_data.append({**item,**cc})

            if post_data:
                s.bulk_insert_mappings(NotificationCompany, post_data)
            if update_data:
                s.bulk_update_mappings(NotificationCompany, update_data)
            s.commit()
            return {
                'success': True,
                'message': 'Notification company data saved successfully'
            }, 200
        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)

@notification_api_route.route('/notification_user')
class NotificationUserApi(Resource):

    @login_required()
    @notification_api_route.marshal_with(notification_user_list_response)
    def get(self):
        try:
            current_user = request.args.get('current_user')
            company_id = current_user.get('company_id')

            query = text('''
            select nu.id,nu.action_id,na.action_name,nu.user_id,e.username,nu.email,nu.deleted,
            count(*) over() as total_count
            from notification_user nu
            left join notification_action na on nu.action_id = na.action_id
            left join euser e on e.userid = nu.user_id
            where nu.company_id=:company_id and nu.deleted is not true
            ''')

            result = query_to_dict(db_client.engine.execute(query,
                                                            company_id=company_id))

            return {
                'total_results': result[0]['total_count'] if result else 0,
                'results': result
            }

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)


    @login_required()
    @notification_api_route.expect(notification_user_model)
    def post(self):

        current_user = request.args.get('current_user')
        company_id = current_user.get('company_id')
        data = request.json
        s = db_client.session
        try:
            cc = {
                'company_id': company_id,
                'created_by': current_user.get('username'),
                'created_on': datetime.datetime.now()
            }

            updated_cc = {
                'modified_by': current_user.get('username'),
                'modified_on': datetime.datetime.now()
            }
            post_data = []
            update_data = []
            for item in data:
                if item.get('id'):
                    update_data.append({**item,**updated_cc})
                else:
                    post_data.append({**item,**cc})

            if post_data:
                s.bulk_insert_mappings(NotificationUser, post_data)
            if update_data:
                s.bulk_update_mappings(NotificationUser, update_data)
            s.commit()
            return {
                'success': True,
                'message': 'Notification user data saved successfully'
            }, 200

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)


@notification_api_route.route('/notification_user_message')
class NotificationUserMessageApi(Resource):

    @login_required()
    @notification_api_route.marshal_with(notification_user_message_list_response)
    def get(self):
        try:
            current_user = request.args.get('current_user')
            company_id = current_user.get('company_id')
            user_id = current_user.get('userid')

            query = text('''
            select num.id,num.action_id,na.action_name,num.message,num.is_read,num.created_on,
            count(*) over() as total_count
            from notification_user_message num
            left join notification_action na on num.action_id = na.action_id
            where num.company_id=:company_id and num.user_id=:user_id and num.deleted is not true
            order by num.id desc
            ''')

            result = query_to_dict(db_client.engine.execute(query,
                                                            company_id=company_id,
                                                            user_id=user_id))

            return {
                'total_results': result[0]['total_count'] if result else 0,
                'results': result
            }

        except Exception as e:
            return map_sqlalchemy_error_to_http_status(e)

    @login_required()
    def patch(self):
        s = db_client.session
        try:
            current_user = request.args.get('current_user')
            data = request.json

            updated_cc = {
                'modified_by': current_user.get('username'),
                'modified_on': datetime.datetime.now(),
                'is_read': True
            }
            updated_data = []
            for item in data:
                if item.get('id'):
                    updated_data.append({**item,**updated_cc})

            if updated_data:
                s.bulk_update_mappings(NotificationUserMessage, updated_data)
                s.commit()

            return {
                'success': True,
                'message': 'Messages marked as read successfully'
            }, 200

        except Exception as e:
            s.rollback()
            return map_sqlalchemy_error_to_http_status(e)