from ipss_utils.ipss_db import query_to_dict
from sqlalchemy import update, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from psycopg2.errors import UniqueViolation
from http import HTTPStatus
from flask import jsonify,request
import datetime
from .. import db_client


def get_current_user():
    current_user = request.args.get('current_user', {})
    return current_user.get('username')


def map_sqlalchemy_error_to_http_status(error: Exception):
    """Map SQLAlchemy errors to HTTP status codes and error messages."""

    orig = getattr(error, 'orig', None)

    # Unique constraint violation
    if orig and isinstance(orig, UniqueViolation):
        return {
            'success': False,
            'message': 'Duplicate data violation',
            'error': str(orig)
        }, 409

    # Integrity constraint violation (e.g., foreign key violation)
    elif isinstance(error, IntegrityError):
        return {

            'success': False,
            'message': 'Foreign key constraint',
            'error': str(error)
        }, 400

    # General SQLAlchemyError (catch-all for other database errors)
    elif isinstance(error, SQLAlchemyError):
        return {
            'success': False,
            'message': 'Database error: An internal server error occurred.',
            'error': str(error)
        }, 500

    # If the error doesn't match any specific type, return internal server error
    else:
        return {
            'success': False,
            'message': 'Unknown error occurred.',
            'error': str(error)
        }, 500


def update_local(model, condition, values):
    error = ""
    if hasattr(model, 'created_by') and hasattr(model, 'modified_by'):
        values["modified_by"] = get_current_user()

    # Add modified at
    if hasattr(model, 'modified_on'):
        values["modified_on"] = datetime.datetime.now()

    try:
        stmt = (
            update(model)
            .where(condition)
            .values(**values)
        )
        result = db_client.session.execute(stmt)
        db_client.session.commit()
    except SQLAlchemyError as e:
        error = str(e)
        db_client.session.flush()
        return map_sqlalchemy_error_to_http_status(e)
    return {
        'success': False if error else True,
        'error': error,
    }


def sequence(prefix,lastno,zeropadding,compcode,table):
    if not lastno:
        lastno = 0
    if not zeropadding:
        zeropadding = 6
    else:
        zeropadding = int(zeropadding)

    query = text(f''' select count(*) from {table} where compcode=:compcode ''')
    res = query_to_dict(db_client.engine.execute(query, compcode=compcode))
    count = 0
    if res:
        count = res[0].get('count')
    next_no = int(lastno)+count+1
    formatnum = str(int(next_no)).zfill(zeropadding)
    sequenc_num = f"{prefix}{formatnum}"
    return sequenc_num


