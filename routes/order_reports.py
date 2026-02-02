from flask import Blueprint, render_template, request
from flask_login import login_required
from database.init_db import get_connection
from datetime import datetime, timedelta

order_reports_bp = Blueprint('order_reports', __name__, url_prefix='/reports/orders')


@order_reports_bp.route('/')
@login_required
def index():
    """Order Reports index page"""
    return render_template('modules/reports/orders/index.html')


@order_reports_bp.route('/delivery-performance')
@login_required
def delivery_performance():
    """Purchase Order Delivery Performance Report"""
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

    # Query POs that have received goods in the date range
    # Get first receipt date for each PO
    cursor.execute('''
        SELECT po.id, po.po_number, po.created_at, po.expected_delivery_date,
               po.status, po.closed_at, v.name as vendor_name,
               MIN(gr.received_at) as first_receipt_date
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        JOIN purchase_order_lines pol ON po.id = pol.purchase_order_id
        JOIN gr_receipts gr ON pol.id = gr.purchase_order_line_id
        WHERE DATE(gr.received_at) BETWEEN ? AND ?
        GROUP BY po.id
        ORDER BY gr.received_at DESC
    ''', (start_date.isoformat(), end_date.isoformat()))

    purchase_orders = cursor.fetchall()

    # Calculate metrics for each PO
    report_data = []
    on_time_count = 0
    late_count = 0
    total_days_to_first_receipt = 0
    total_days_to_complete = 0
    completed_count = 0

    for po in purchase_orders:
        created_date = datetime.strptime(po['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S').date()
        first_receipt_date = datetime.strptime(po['first_receipt_date'].split('.')[0], '%Y-%m-%d %H:%M:%S').date()

        days_to_first_receipt = (first_receipt_date - created_date).days
        total_days_to_first_receipt += days_to_first_receipt

        # Calculate days to complete if PO is closed
        days_to_complete = None
        completed_date_str = 'In Progress'
        if po['closed_at']:
            completed_date = datetime.strptime(po['closed_at'].split('.')[0], '%Y-%m-%d %H:%M:%S').date()
            days_to_complete = (completed_date - created_date).days
            total_days_to_complete += days_to_complete
            completed_count += 1
            completed_date_str = completed_date.strftime('%Y-%m-%d')

        # Determine if on time (based on first receipt vs expected delivery date)
        on_time = True
        days_variance = 0
        expected_delivery_date_str = 'N/A'
        if po['expected_delivery_date']:
            expected_delivery_date = datetime.strptime(po['expected_delivery_date'], '%Y-%m-%d').date()
            expected_delivery_date_str = expected_delivery_date.strftime('%Y-%m-%d')
            days_variance = (first_receipt_date - expected_delivery_date).days
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
            'id': po['id'],
            'po_number': po['po_number'],
            'vendor_name': po['vendor_name'] or 'N/A',
            'created_at': created_date.strftime('%Y-%m-%d'),
            'expected_delivery_date': expected_delivery_date_str,
            'first_receipt_date': first_receipt_date.strftime('%Y-%m-%d'),
            'completed_at': completed_date_str,
            'days_to_first_receipt': days_to_first_receipt,
            'days_to_complete': days_to_complete if days_to_complete else 'N/A',
            'status_label': status_label,
            'status_class': status_class,
            'days_variance': days_variance
        })

    # Calculate summary statistics
    total_pos = len(purchase_orders)
    on_time_percentage = (on_time_count / total_pos * 100) if total_pos > 0 else 0
    avg_days_to_first_receipt = (total_days_to_first_receipt / total_pos) if total_pos > 0 else 0
    avg_days_to_complete = (total_days_to_complete / completed_count) if completed_count > 0 else 0

    summary = {
        'total_pos': total_pos,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': round(on_time_percentage, 1),
        'avg_days_to_first_receipt': round(avg_days_to_first_receipt, 1),
        'avg_days_to_complete': round(avg_days_to_complete, 1)
    }

    conn.close()

    return render_template('modules/reports/orders/delivery_performance.html',
                          summary=summary,
                          purchase_orders=report_data,
                          period=period,
                          period_label=period_label,
                          start_date=start_date.isoformat(),
                          end_date=end_date.isoformat())


@order_reports_bp.route('/spend-analysis')
@login_required
def spend_analysis():
    """Financial/Spend Analysis Report"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get date range from request parameters
    period = request.args.get('period', 'last_30')
    custom_start = request.args.get('start_date', '')
    custom_end = request.args.get('end_date', '')

    # Calculate date range
    today = datetime.now().date()

    if period == 'last_30':
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)
        period_label = 'Last 30 Days'
    elif period == 'last_90':
        start_date = today - timedelta(days=90)
        end_date = today + timedelta(days=1)
        period_label = 'Last 90 Days'
    elif period == 'current_month':
        start_date = today.replace(day=1)
        end_date = today + timedelta(days=1)
        period_label = 'Current Month'
    elif period == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        period_label = f'{start_date.strftime("%b %d, %Y")} - {end_date.strftime("%b %d, %Y")}'
    else:
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)
        period_label = 'Last 30 Days'
        period = 'last_30'

    # Query POs in date range (exclude Cancelled)
    cursor.execute('''
        SELECT po.id, po.po_number, po.total_amount, po.order_date,
               po.status, v.name as vendor_name, v.vendor_id
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        WHERE DATE(po.order_date) BETWEEN ? AND ?
        AND po.status != 'Cancelled'
        ORDER BY po.order_date DESC
    ''', (start_date.isoformat(), end_date.isoformat()))

    purchase_orders = cursor.fetchall()

    # Calculate overall summary metrics
    total_spend = sum(po['total_amount'] for po in purchase_orders)
    total_pos = len(purchase_orders)
    avg_po_value = (total_spend / total_pos) if total_pos > 0 else 0

    # Calculate spend by vendor
    vendor_spend = {}
    for po in purchase_orders:
        vendor_name = po['vendor_name'] or 'Unknown Vendor'
        if vendor_name not in vendor_spend:
            vendor_spend[vendor_name] = {
                'vendor_name': vendor_name,
                'total_spend': 0,
                'po_count': 0,
                'po_numbers': []
            }
        vendor_spend[vendor_name]['total_spend'] += po['total_amount']
        vendor_spend[vendor_name]['po_count'] += 1
        vendor_spend[vendor_name]['po_numbers'].append(po['po_number'])

    # Convert to list and calculate percentages and averages
    vendor_data = []
    for vendor_name, data in vendor_spend.items():
        avg_vendor_po = data['total_spend'] / data['po_count']
        percentage = (data['total_spend'] / total_spend * 100) if total_spend > 0 else 0

        vendor_data.append({
            'vendor_name': vendor_name,
            'total_spend': round(data['total_spend'], 2),
            'po_count': data['po_count'],
            'avg_po_value': round(avg_vendor_po, 2),
            'percentage': round(percentage, 1)
        })

    # Sort by total spend descending
    vendor_data.sort(key=lambda x: x['total_spend'], reverse=True)

    summary = {
        'total_spend': round(total_spend, 2),
        'total_pos': total_pos,
        'avg_po_value': round(avg_po_value, 2)
    }

    conn.close()

    return render_template('modules/reports/orders/spend_analysis.html',
                          summary=summary,
                          vendors=vendor_data,
                          period=period,
                          period_label=period_label,
                          start_date=start_date.isoformat(),
                          end_date=end_date.isoformat())
