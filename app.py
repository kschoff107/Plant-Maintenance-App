from flask import Flask
from flask_login import LoginManager
from config import Config
from database.init_db import init_database
from routes import (auth_bp, main_bp, spare_parts_bp, equipment_bp, location_bp,
                    work_orders_bp, maintenance_schedules_bp, meter_readings_bp,
                    orders_bp, master_data_bp, vendors_bp, reports_bp,
                    maintenance_reports_bp, order_reports_bp, get_user_by_id)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(spare_parts_bp)
app.register_blueprint(equipment_bp)
app.register_blueprint(location_bp)
app.register_blueprint(work_orders_bp)
app.register_blueprint(maintenance_schedules_bp)
app.register_blueprint(meter_readings_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(master_data_bp)
app.register_blueprint(vendors_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(maintenance_reports_bp)
app.register_blueprint(order_reports_bp)

# Initialize database on startup
with app.app_context():
    init_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
