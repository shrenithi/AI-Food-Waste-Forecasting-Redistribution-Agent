from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.ai_assistant_service import AIAssistantService
from services.notification_service import NotificationService
from models.database import Notification

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/assistant/chat', methods=['POST'])
@login_required
def assistant_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Message cannot be empty.'}), 400
        
    org = current_user.organization
    org_id = org.id if org else 1
    
    response = AIAssistantService.answer_query(org_id=org_id, user_prompt=message)
    return jsonify(response)

@api_bp.route('/notifications/unread-count')
@login_required
def unread_count():
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({'unread_count': count})

@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_read():
    NotificationService.mark_all_read(current_user.id)
    return jsonify({'success': True})
