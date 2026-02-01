import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'plant-maintenance-secret-key-change-in-production'
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'plant_maintenance.db')
