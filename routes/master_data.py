from flask import Blueprint, render_template
from flask_login import login_required

master_data_bp = Blueprint('master_data', __name__, url_prefix='/master-data')


@master_data_bp.route('/')
@login_required
def index():
    """Master Data module index page"""
    return render_template('modules/master_data/index.html')
