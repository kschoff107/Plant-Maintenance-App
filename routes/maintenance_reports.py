from flask import Blueprint, render_template, request
from flask_login import login_required
from database.init_db import get_connection
from datetime import datetime, timedelta

maintenance_reports_bp = Blueprint('maintenance_reports', __name__, url_prefix='/reports/maintenance')


@maintenance_reports_bp.route('/')
@login_required
def index():
    """Maintenance Reports index page"""
    return render_template('modules/reports/maintenance/index.html')


@maintenance_reports_bp.route('/completion-performance')
@login_required
def completion_performance():
    """Work Order Completion Performance Metrics Report"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get date range from request parameters
    period = request.args.get('period', 'last_30')
    custom_start = request.args.get('start_date', '')
    custom_end = request.args.get('end_date', '')

    # Calculate date range based on period selection
    today = datetime.now().date()

    if period == 'last_30':
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)  # Include next day to handle UTC timezone
        period_label = 'Last 30 Days'
    elif period == 'last_90':
        start_date = today - timedelta(days=90)
        end_date = today + timedelta(days=1)  # Include next day to handle UTC timezone
        period_label = 'Last 90 Days'
    elif period == 'current_month':
        start_date = today.replace(day=1)
        end_date = today + timedelta(days=1)  # Include next day to handle UTC timezone
        period_label = 'Current Month'
    elif period == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        period_label = f'{start_date.strftime("%b %d, %Y")} - {end_date.strftime("%b %d, %Y")}'
    else:
        # Default to last 30 days
        start_date = today - timedelta(days=30)
        end_date = today
        period_label = 'Last 30 Days'
        period = 'last_30'

    # Query completed work orders in date range
    cursor.execute('''
        SELECT wo.id, wo.work_order_number, wo.title, wo.priority, wo.status,
               wo.created_at, wo.due_date, wo.completed_at,
               e.tag_number as equipment_tag,
               u.username as assigned_to
        FROM work_orders wo
        LEFT JOIN equipment e ON wo.equipment_id = e.id
        LEFT JOIN users u ON wo.assigned_to = u.id
        WHERE wo.status = 'Completed'
        AND DATE(wo.completed_at) BETWEEN ? AND ?
        ORDER BY wo.completed_at DESC
    ''', (start_date.isoformat(), end_date.isoformat()))

    work_orders = cursor.fetchall()

    # Calculate metrics for each work order
    report_data = []
    on_time_count = 0
    late_count = 0
    total_days_to_complete = 0

    for wo in work_orders:
        # Parse timestamps (strip microseconds if present)
        created_date = datetime.strptime(wo['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S').date()
        completed_date = datetime.strptime(wo['completed_at'].split('.')[0], '%Y-%m-%d %H:%M:%S').date()
        days_to_complete = (completed_date - created_date).days
        total_days_to_complete += days_to_complete

        # Determine if on time
        on_time = True
        days_variance = 0
        if wo['due_date']:
            due_date = datetime.strptime(wo['due_date'], '%Y-%m-%d').date()
            days_variance = (completed_date - due_date).days
            on_time = days_variance <= 0

        if on_time:
            on_time_count += 1
            status_label = 'On Time'
            status_class = 'on-time'
        else:
            late_count += 1
            status_label = f'{days_variance} days late'
            status_class = 'late'

        report_data.append({
            'id': wo['id'],
            'work_order_number': wo['work_order_number'],
            'title': wo['title'],
            'equipment_tag': wo['equipment_tag'] or 'N/A',
            'priority': wo['priority'],
            'created_at': created_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d') if wo['due_date'] else 'N/A',
            'completed_at': completed_date.strftime('%Y-%m-%d'),
            'days_to_complete': days_to_complete,
            'assigned_to': wo['assigned_to'] or 'Unassigned',
            'status_label': status_label,
            'status_class': status_class,
            'days_variance': days_variance
        })

    # Calculate summary statistics
    total_completed = len(work_orders)
    on_time_percentage = (on_time_count / total_completed * 100) if total_completed > 0 else 0
    avg_days_to_complete = (total_days_to_complete / total_completed) if total_completed > 0 else 0

    summary = {
        'total_completed': total_completed,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': round(on_time_percentage, 1),
        'avg_days_to_complete': round(avg_days_to_complete, 1)
    }

    conn.close()

    return render_template('modules/reports/maintenance/completion_performance.html',
                          summary=summary,
                          work_orders=report_data,
                          period=period,
                          period_label=period_label,
                          start_date=start_date.isoformat(),
                          end_date=end_date.isoformat())
