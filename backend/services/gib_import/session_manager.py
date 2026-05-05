import uuid
from datetime import datetime, timezone


class GibSessionManager:
    def __init__(self):
        self._sessions = {}

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _mask_username(username: str) -> str:
        if not username:
            return ''
        if len(username) <= 4:
            return username[:1] + '***'
        return f"{username[:2]}***{username[-2:]}"

    def connect(self, salesperson_id: str, username: str, cookies: dict):
        session_id = str(uuid.uuid4())
        self._sessions[salesperson_id] = {
            'session_id': session_id,
            'username_masked': self._mask_username(username),
            'cookies': cookies,
            'state': 'connected',
            'connected_at': self._now_iso(),
            'last_verified_at': self._now_iso(),
            'last_error': None,
        }
        return {k: v for k, v in self._sessions[salesperson_id].items() if k != 'cookies'}

    def get(self, salesperson_id: str):
        return self._sessions.get(salesperson_id)

    def mark_expired(self, salesperson_id: str, reason: str = 'session_expired'):
        session = self._sessions.get(salesperson_id)
        if not session:
            return {'state': 'not_connected'}
        session['state'] = 'expired'
        session['last_error'] = reason
        return {k: v for k, v in session.items() if k != 'cookies'}

    def disconnect(self, salesperson_id: str):
        session = self._sessions.pop(salesperson_id, None)
        if not session:
            return {'state': 'not_connected'}
        return {'state': 'disconnected', 'username_masked': session.get('username_masked')}

    def status(self, salesperson_id: str):
        session = self._sessions.get(salesperson_id)
        if not session:
            return {'state': 'not_connected'}
        return {k: v for k, v in session.items() if k != 'cookies'}


session_manager = GibSessionManager()
