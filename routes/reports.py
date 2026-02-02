from flask import Blueprint, render_template
from flask_login import login_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    """Reports module index page"""
    return render_template('modules/reports/index.html')
