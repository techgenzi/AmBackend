from flask_restx import Namespace, fields

chat_agent_api_route = Namespace('chat_agent', path='/fabrico/chatAgent')

chat_message_model = chat_agent_api_route.model('chat_message', {
    'message_id': fields.Integer,
    'user_id': fields.Integer,
    'message': fields.String,
    'response': fields.String,
    'image_url': fields.String,
    'timestamp': fields.String,
    'compcode': fields.String,
})

send_message_model = chat_agent_api_route.model('send_message', {
    'message': fields.String(required=True, description="User prompt or inquiry"),
    'chat_history': fields.List(fields.Raw, required=False, description="Conversation history"),
    'session_id': fields.String(required=False, description="Session identifier"),
    'stream': fields.Boolean(required=False, default=False, description="Whether to stream response via SSE"),
    'image': fields.String(required=False, description="Base64 encoded image string (optional)"),
    'stage': fields.String(required=False, description="Staged execution ('tool_decision', 'synthesis', or 'judge')"),
    'tools': fields.List(fields.Raw, required=False, description="Client-supplied tools schema for dynamic tool decision"),
    'tool_calls': fields.List(fields.Raw, required=False, description="Tool calls or execution results passed to synthesis or judge stage"),
    'response': fields.String(required=False, description="Synthesized answer response for evaluation in judge stage"),
    'answer': fields.String(required=False, description="Synthesized answer response (alias) for evaluation in judge stage"),
    'message_id': fields.Integer(required=False, description="Message ID to persist evaluation/relevance score")
})

judge_evaluation_model = chat_agent_api_route.model('judge_evaluation', {
    'tool_calling_score': fields.Float(description="Score for tool calling decision (0.0 - 10.0)"),
    'tool_calling_feedback': fields.String(description="Detailed evaluation feedback for tool selection and parameters"),
    'answer_score': fields.Float(description="Score for answer response quality (0.0 - 10.0)"),
    'answer_feedback': fields.String(description="Detailed evaluation feedback for answer response clarity and correctness"),
    'overall_score': fields.Float(description="Composite evaluation score (0.0 - 10.0)"),
    'verdict': fields.String(description="Evaluation verdict (e.g. EXCELLENT, GOOD, ACCEPTABLE, NEEDS_IMPROVEMENT, POOR)"),
    'summary': fields.String(description="Executive summary of judge evaluation")
})

chat_response_model = chat_agent_api_route.model('chat_response', {
    'response': fields.String,
    'message_id': fields.Integer,
    'tools_used': fields.List(fields.String),
    'status': fields.String,
    'stage': fields.String,
    'evaluation': fields.Nested(judge_evaluation_model, required=False)
})

chat_log_item_model = chat_agent_api_route.model('chat_log_item', {
    'message_id': fields.Integer,
    'user_id': fields.Integer,
    'company_code': fields.Integer,
    'compcode': fields.String,
    'message': fields.String,
    'response': fields.String,
    'image_url': fields.String,
    'prompt_tokens': fields.Integer,
    'completion_tokens': fields.Integer,
    'token_cost': fields.Float,
    'relevance_score': fields.Float,
    'retry_attempts': fields.Integer,
    'provider': fields.String,
    'model': fields.String,
    'llm_url': fields.String,
    'tools_used': fields.List(fields.String),
    'created_on': fields.String,
    'timestamp': fields.String
})

chat_logs_response_model = chat_agent_api_route.model('chat_logs_response', {
    'primary_key': fields.String(default='message_id'),
    'total_results': fields.Integer,
    'page': fields.Integer,
    'results_per_page': fields.Integer,
    'results': fields.List(fields.Nested(chat_log_item_model))
})
