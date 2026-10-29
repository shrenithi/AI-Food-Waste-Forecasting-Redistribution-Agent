import datetime
from models.database import db, Notification, User

class NotificationService:
    @staticmethod
    def send(user_id, title, message, notification_type='system', link_url=None):
        """Creates an in-app notification for a user."""
        try:
            notif = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                link_url=link_url,
                created_at=datetime.datetime.utcnow()
            )
            db.session.add(notif)
            db.session.commit()
            return notif
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def notify_organization_users(org_id, title, message, notification_type='system', link_url=None):
        """Notifies all members of a given organization."""
        from models.database import OrganizationMember
        members = OrganizationMember.query.filter_by(organization_id=org_id).all()
        for m in members:
            NotificationService.send(m.user_id, title, message, notification_type, link_url)

    @staticmethod
    def get_unread_count(user_id):
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def mark_all_read(user_id):
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
