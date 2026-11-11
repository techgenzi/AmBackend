from flask_restx import Namespace, Resource, fields

from ipss_utils.ipss_api_doc import create_record_response, update_record_response, list_response_model

from ..api_doc import notification_company, notification_user, notification_user_message

# Initialize API routes

notification_api_route = Namespace('Notification', path='/notification')

notification_company_model = notification_api_route.model('NotificationCompany', notification_company)

notification_company_list_response = notification_api_route.model('NotificationCompanyListResponse',
                                                                  {
                                                                      **list_response_model,
                                                                        'results': fields.List(fields.Nested(notification_company_model))
                                                                  })

notification_user_model = notification_api_route.model('NotificationUser', notification_user)

notification_user_list_response = notification_api_route.model('NotificationUserListResponse',{
    **list_response_model,
    'results': fields.List(fields.Nested(notification_user_model))
})

notification_user_message_model = notification_api_route.model('NotificationUserMessage', notification_user_message)

notification_user_message_list_response = notification_api_route.model('NotificationUserMessageListResponse',{
    **list_response_model,
    'results': fields.List(fields.Nested(notification_user_message_model))
})
