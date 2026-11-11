from flask_restx import fields


line_map = {
    'line_map_id': fields.Integer,
    'line_process_id': fields.Integer,
    'config_map_id': fields.Integer,
    'count': fields.Integer,
    'deleted': fields.Boolean
}


line_get = {
    'line_config_id': fields.Integer,
    'line_name': fields.String
}

line_model = {
    'line_map_id': fields.Integer,
    'emp_name': fields.String,
    'config_name': fields.String
}


line_get_list = {
    'line_process_id': fields.Integer,
    'line_map_id': fields.Integer,
    'config_map_id': fields.Integer,
    'config_id': fields.Integer,
    'stage_id': fields.Integer,
    'process_id':fields.Integer,
    'machine_id': fields.Integer,
    'activity_id': fields.Integer,
    'stage_name': fields.String,
    'machine_name': fields.String,
    'activity_name': fields.String,
    'process_name': fields.String,
    'count': fields.Integer,
    'deleted': fields.Boolean
}

employee_line = {
    'employee_line_id': fields.Integer,
    'line_map_id': fields.Integer,
    'employee_id': fields.Integer
}

line_search = {'line_config_id': {
        'type': int,
        'description': 'line config filter'
    },
'process_id': {
    'type': str,
    'description': 'filter by process_id '
},
'stage_id': {
    'type': int,
    'description': 'filter by stage_id'
}}

line_config_filter = {
    'line_config_id': {
        'type': str,
        'description': 'line config id to reset the particular line employee'
    }
}

employee_line = {
    'hremploymastid': fields.Integer,
    'fname': fields.String,
    'mname': fields.String,
    'lname': fields.String,
    'idcardno': fields.String,
    'line_config_id': fields.Integer,
    'line_name': fields.String,
    'line_map_id': fields.Integer,
    'employee_line_id': fields.Integer,
    'process_id': fields.Integer,
    'stage_id': fields.Integer,
    'stage_name': fields.String,
    'activity_id': fields.Integer,
    'machine_id': fields.Integer,
    'process_name': fields.String,
    'activity_name': fields.String,
    'machine_name': fields.String,
    'assigned': fields.Boolean,
    'in_execution': fields.Boolean,
    'data': fields.Raw
}

employee_filter = {
    'assigned': {
        'type': bool,
        'description': 'filter by assigned'
    },
    'line_map_id': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'results_per_page': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'paged': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'config_id': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'activity_id': {
        'type': int,
        'description': 'filter by activity id'
    },
    'line_config_id': {
        'type': int,
        'description': 'filter by line config id'
    },
    'process_id': {
        'type': str,
        'description': 'bulk filter comma separated value'
    },
    'stage_id': {
        'type': str,
        'description': 'bulk filter based on stage_id '
    },
    'know_activity_id': {
        'type': int,
        'description': 'filter by employee know_activity_id'
    },
    'emp_id': {
        'type': int,
        'description': 'filter by employee id'
    }
}


delete = {
    'data': fields.List(fields.Integer)
}


employee_report_filter = {
'results_per_page': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'paged': {
        'type': int,
        'description': 'filter by line_map_id'
    },
    'date': {
        'type': str,
        'description': 'filter by date'
    }
}

employee_report_field = {
    'employee_line_id': fields.Integer,
    'line_map_id': fields.Integer,
    'hremploymastid': fields.Integer,
    'idcardno': fields.String,
    'line_name': fields.String,
    'config_name': fields.String,
    'assigned': fields.Boolean,
    'fname': fields.String,
    'mname': fields.String,
    'lname': fields.String,
    'att': fields.Boolean
}
