from flask import Blueprint, render_template
from flask_login import login_required

order_reports_bp = Blueprint('order_reports', __name__, url_prefix='/reports/orders')


@order_reports_bp.route('/')
@login_required
def index():
    """Order Reports index page"""
    return render_template('modules/reports/orders/index.html')
