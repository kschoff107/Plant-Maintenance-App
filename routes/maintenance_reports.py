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


@maintenance_reports_bp.route('/equipment-cost')
@login_required
def equipment_cost():
    """Equipment Maintenance Cost Report"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get date range from request parameters
    period = request.args.get('period', 'all_time')
    custom_start = request.args.get('start_date', '')
    custom_end = request.args.get('end_date', '')

    # Calculate date range based on period selection
    today = datetime.now().date()
    date_filter = ""
    date_params = []

    if period == 'last_30':
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)
        period_label = 'Last 30 Days'
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params = [start_date.isoformat(), end_date.isoformat()]
    elif period == 'last_90':
        start_date = today - timedelta(days=90)
        end_date = today + timedelta(days=1)
        period_label = 'Last 90 Days'
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params = [start_date.isoformat(), end_date.isoformat()]
    elif period == 'current_year':
        start_date = today.replace(month=1, day=1)
        end_date = today + timedelta(days=1)
        period_label = 'Current Year'
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params = [start_date.isoformat(), end_date.isoformat()]
    elif period == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        period_label = f'{start_date.strftime("%b %d, %Y")} - {end_date.strftime("%b %d, %Y")}'
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params = [start_date.isoformat(), end_date.isoformat()]
    else:
        # Default to all time
        period_label = 'All Time'
        period = 'all_time'

    # Query equipment costs
    query = f'''
        SELECT e.id, e.tag_number, e.description, e.manufacturer, e.model_number,
               COUNT(DISTINCT wo.id) as work_order_count,
               COALESCE(SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity
                                 ELSE -wop.quantity END), 0) as parts_issued_count,
               SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity * wop.cost_per_unit
                        ELSE -wop.quantity * wop.cost_per_unit END) as total_parts_cost
        FROM equipment e
        LEFT JOIN work_orders wo ON e.id = wo.equipment_id
        LEFT JOIN work_order_parts wop ON wo.id = wop.work_order_id
        WHERE 1=1 {date_filter}
        GROUP BY e.id
        HAVING total_parts_cost > 0
        ORDER BY total_parts_cost DESC
    '''

    cursor.execute(query, date_params)
    equipment_data = cursor.fetchall()

    # Calculate summary statistics
    total_equipment = len(equipment_data)
    total_cost = sum(row['total_parts_cost'] or 0 for row in equipment_data)
    avg_cost_per_equipment = (total_cost / total_equipment) if total_equipment > 0 else 0

    # Prepare report data
    report_data = []
    for equip in equipment_data:
        total_cost_value = equip['total_parts_cost'] or 0
        wo_count = equip['work_order_count'] or 0
        avg_cost_per_wo = (total_cost_value / wo_count) if wo_count > 0 else 0

        report_data.append({
            'id': equip['id'],
            'tag_number': equip['tag_number'],
            'description': equip['description'],
            'manufacturer': equip['manufacturer'] or 'N/A',
            'model_number': equip['model_number'] or 'N/A',
            'work_order_count': wo_count,
            'parts_issued_count': equip['parts_issued_count'] or 0,
            'total_parts_cost': total_cost_value,
            'avg_cost_per_wo': avg_cost_per_wo
        })

    summary = {
        'total_equipment': total_equipment,
        'total_cost': total_cost,
        'avg_cost_per_equipment': avg_cost_per_equipment
    }

    conn.close()

    return render_template('modules/reports/maintenance/equipment_cost.html',
                          summary=summary,
                          equipment=report_data,
                          period=period,
                          period_label=period_label)


@maintenance_reports_bp.route('/equipment-work-orders/<int:equipment_id>')
@login_required
def equipment_work_orders(equipment_id):
    """AJAX endpoint: Get work order breakdown for equipment"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get date filter from query params (match parent report filters)
    period = request.args.get('period', 'all_time')
    custom_start = request.args.get('start_date', '')
    custom_end = request.args.get('end_date', '')

    # Calculate date filter (same logic as equipment_cost)
    today = datetime.now().date()
    date_filter = ""
    date_params = [equipment_id]

    if period == 'last_30':
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params.extend([start_date.isoformat(), end_date.isoformat()])
    elif period == 'last_90':
        start_date = today - timedelta(days=90)
        end_date = today + timedelta(days=1)
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params.extend([start_date.isoformat(), end_date.isoformat()])
    elif period == 'current_year':
        start_date = today.replace(month=1, day=1)
        end_date = today + timedelta(days=1)
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params.extend([start_date.isoformat(), end_date.isoformat()])
    elif period == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        date_filter = "AND DATE(wop.transacted_at) BETWEEN ? AND ?"
        date_params.extend([start_date.isoformat(), end_date.isoformat()])

    # Query work orders with parts breakdown
    query = f'''
        SELECT wo.id, wo.work_order_number, wo.title,
               DATE(MIN(wop.transacted_at)) as first_transaction_date,
               SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity * wop.cost_per_unit
                        ELSE -wop.quantity * wop.cost_per_unit END) as total_cost
        FROM work_orders wo
        JOIN work_order_parts wop ON wo.id = wop.work_order_id
        WHERE wo.equipment_id = ? {date_filter}
        GROUP BY wo.id
        HAVING total_cost > 0
        ORDER BY first_transaction_date DESC
    '''

    cursor.execute(query, date_params)
    work_orders = cursor.fetchall()

    # For each work order, get parts breakdown
    result = []
    for wo in work_orders:
        # Get parts for this work order
        parts_query = '''
            SELECT sp.description,
                   SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity
                            ELSE -wop.quantity END) as net_quantity,
                   AVG(CASE WHEN wop.transaction_type = 'issue' THEN wop.cost_per_unit END) as avg_cost,
                   SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity * wop.cost_per_unit
                            ELSE -wop.quantity * wop.cost_per_unit END) as part_total_cost
            FROM work_order_parts wop
            JOIN spare_parts sp ON wop.spare_part_id = sp.id
            WHERE wop.work_order_id = ?
            GROUP BY sp.id
            HAVING net_quantity > 0
            ORDER BY sp.description
        '''
        cursor.execute(parts_query, (wo['id'],))
        parts = cursor.fetchall()

        result.append({
            'id': wo['id'],
            'work_order_number': wo['work_order_number'],
            'title': wo['title'],
            'date': wo['first_transaction_date'],
            'total_cost': float(wo['total_cost']),
            'parts': [
                {
                    'description': p['description'],
                    'quantity': p['net_quantity'],
                    'avg_cost': float(p['avg_cost'] or 0),
                    'total_cost': float(p['part_total_cost'] or 0)
                }
                for p in parts
            ]
        })

    conn.close()

    # Calculate summary
    total_cost = sum(wo['total_cost'] for wo in result)
    avg_cost_per_wo = total_cost / len(result) if result else 0

    return {
        'work_orders': result,
        'summary': {
            'total_work_orders': len(result),
            'total_cost': total_cost,
            'avg_cost_per_wo': avg_cost_per_wo
        }
    }
