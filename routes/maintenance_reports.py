from flask import Blueprint, render_template
from flask_login import login_required

maintenance_reports_bp = Blueprint('maintenance_reports', __name__, url_prefix='/reports/maintenance')


@maintenance_reports_bp.route('/')
@login_required
def index():
    """Maintenance Reports index page"""
    return render_template('modules/reports/maintenance/index.html')
