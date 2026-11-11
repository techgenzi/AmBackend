import datetime
from sqlalchemy import text
from ..models.notification import NotificationUserMessage
from flask_socketio import SocketIO
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader

REDIS_URL = os.getenv("REDIS_DB_URL", "redis://localhost:6379/0")

socketio = SocketIO(
    message_queue=REDIS_URL,
    channel="notification-service",
    async_mode="eventlet"
)


def send_email(data, emails, db_client, compcode, action):

    sender_mail = 'communications@techgenzi.com'

    smtp_query = text("""
            SELECT smtp_server, smtp_port, username, password
            FROM mail_configure
            WHERE compcode = :compcode
              AND enabled IS TRUE
              AND deleted IS NOT TRUE
        """)

    smtp_config = db_client.execute(smtp_query, {"compcode": compcode}).mappings().first()
    # print(smtp_config,"smtp_config")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # print(base_dir, "base_dis")
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(base_dir)),
        "template"
    )

    env = Environment(loader=FileSystemLoader(template_dir))

    template = ""
    subject = ""
    html_body = None

    if action == 'production_plan_creation':

        template = env.get_template("production_plan_creation.html")

        subject = f"Production Plan Created - {data.get('plan_unique')}"

        html_body = template.render(
            production_plan_id=data.get("production_plan_id"),
            plan_unique=data.get("plan_unique"),
            created_by=data.get("created_by")
        )

    try:
        server = smtplib.SMTP(
            smtp_config["smtp_server"],
            smtp_config["smtp_port"]
        )

        server.starttls()

        server.login(
            smtp_config["username"],
            smtp_config["password"]
        )

        for email in emails:
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = f"TechGenzi <{sender_mail}>"
                msg["To"] = email
                msg["Subject"] = subject

                text_body = f"""
                Production Plan Created

                Plan Number: {data.get('plan_unique')}
                Created By: {data.get('created_by')}

                Please log in to the application for more details.
                """

                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                server.sendmail(
                    sender_mail,
                    email,
                    msg.as_string()
                )

                print(f"Email sent to {email}")

            except Exception as e:
                print(f"Failed for {email}: {e}")

        server.quit()

    except Exception as e:
        print(f"SMTP connection failed: {e}")


def production_plan_creation(production_plan_id,plan_unique,company_id,db_client,username):
    data = {
        'production_plan_id': production_plan_id,
        'plan_unique': plan_unique,
        'created_by': username
    }

    query1 = text(f'''
        select action_id from notification_company 
        where action_id = 
        (
        select id from notification_action 
        where action_name = 'production_plan_creation'
        ) 
        and company_id = :company_id and deleted is not true
    ''')
    print("query1")
    result = db_client.execute(query1, {'company_id':company_id}).mappings().all()
    print("result",result)
    if result:
        action_id = result[0]['action_id']
        query2 = text(f'''
            select user_id,email from notification_user
            where action_id = :action_id and company_id = :company_id and deleted is not true
        ''')

        result2 = db_client.execute(query2, {
                                                         'action_id':action_id,
                                                         'company_id':company_id}).mappings().all()

        emails = []

        if result2:
            post_data = []
            print("result2",result2)
            for item in result2:
                if item.get('email'):
                    emails.append(item.get('email'))
                user_id = item.get('user_id')
                post_data.append({'user_id': user_id,
                                  'message':data,
                                  'is_read': False,
                                  'company_id': company_id,
                                  'action_id': action_id,
                                  'created_by': 'System',
                                  'created_on': datetime.datetime.now()
                                  })
                
                # Emit socket event
                try:
                    room = f"user_{user_id}"
                    socketio.emit('new_notification', {'flag': True}, room=room)
                    print(f"Emitted notification flag to room {room}")
                except Exception as e:
                    print(f"Failed to emit socket event: {e}")
            print("post_data",post_data)
            if post_data:
                db_client.bulk_insert_mappings(NotificationUserMessage, post_data)
                db_client.commit()

        if emails:
            send_email(data, emails, db_client=db_client, compcode=company_id,action="production_plan_creation")


def execution_qty_exceeded_notification(data, company_id, db_client):
    plan_unique = data.get('plan_unique')
    username = data.get('username')
    total_qty = data.get('total_qty')
    target_qty = data.get('target_qty')
    message_data = {
        'production_plan_id': data.get('production_plan_id'),
        'plan_unique': plan_unique,
        'title': 'Execution Quantity Exceeded',
        'description': f'Execution quantity ({total_qty}) has exceeded the planned quantity ({target_qty}) for plan {plan_unique}. Created by {username}.'
    }

    query1 = text(f'''
        select action_id from notification_company 
        where action_id = 
        (
        select action_id from notification_action 
        where action_name = 'execution_qty_exceeded'
        ) 
        and company_id = :company_id and deleted is not true
    ''')
    result = db_client.execute(query1, {'company_id': company_id}).mappings().all()
    if result:
        action_id = result[0]['action_id']
        query2 = text(f'''
            select user_id, email from notification_user
            where action_id = :action_id and company_id = :company_id and deleted is not true
        ''')

        result2 = db_client.execute(query2, {
            'action_id': action_id,
            'company_id': company_id
        }).mappings().all()

        if result2:
            post_data = []
            for item in result2:
                user_id = item.get('user_id')
                post_data.append({
                    'user_id': user_id,
                    'message': message_data,
                    'is_read': False,
                    'company_id': company_id,
                    'action_id': action_id,
                    'created_by': 'System',
                    'created_on': datetime.datetime.now()
                })
                
                try:
                    room = f"user_{user_id}"
                    socketio.emit('new_notification', {'flag': True}, room=room)
                except Exception as e:
                    print(f"Failed to emit socket event: {e}")
                    
            if post_data:
                db_client.bulk_insert_mappings(NotificationUserMessage, post_data)
                db_client.commit()
