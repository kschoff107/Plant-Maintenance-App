from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, username, password_hash, role, created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    def is_admin(self):
        return self.role == 'admin'

    def is_supervisor(self):
        return self.role in ['admin', 'supervisor']

    def is_technician(self):
        return self.role in ['admin', 'supervisor', 'technician']
