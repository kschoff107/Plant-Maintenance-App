from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.maintenance_schedule import MaintenanceSchedule
from models.equipment import Equipment
from datetime import datetime, timedelta

maintenance_schedules_bp = Blueprint('maintenance_schedules', __name__, url_prefix='/maintenance-schedules')


def get_all_equipment():
    """Fetch all active equipment for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment WHERE status = 'Active' ORDER BY tag_number")
    rows = cursor.fetchall()
    conn.close()
    return [Equipment.from_row(row) for row in rows]


def get_latest_meter_reading(equipment_id):
    """Get the latest meter reading for an equipment"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reading_value, reading_unit FROM meter_readings
        WHERE equipment_id = ?
        ORDER BY recorded_at DESC LIMIT 1
    ''', (equipment_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'value': row['reading_value'], 'unit': row['reading_unit']}
    return None


def generate_schedule_id():
    """Generate next schedule ID (SCH-0001, SCH-0002, etc.)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT schedule_id FROM maintenance_schedules ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None or row['schedule_id'] is None:
        return 'SCH-0001'

    last_id = row['schedule_id']
    try:
        num = int(last_id.split('-')[1]) + 1
        return f'SCH-{num:04d}'
    except:
        return f'SCH-{datetime.now().strftime("%Y%m%d%H%M%S")}'


def generate_pm_work_order_number():
    """Generate next PM work order number for scheduled maintenance"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT work_order_number FROM work_orders WHERE work_order_number LIKE 'PM-%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return 'PM-0001'

    last_num = row['work_order_number']
    try:
        num = int(last_num.split('-')[1]) + 1
        return f'PM-{num:04d}'
    except:
        return f'PM-{datetime.now().strftime("%Y%m%d%H%M%S")}'


@maintenance_schedules_bp.route('/')
@login_required
def index():
    """Main maintenance schedule page"""
    return render_template('modules/maintenance_schedule/index.html')


@maintenance_schedules_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard showing overdue, due today, and upcoming maintenance"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')
    week_ahead = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    # Get all active schedules with equipment info and open work order status
    # Only consider work orders due today or earlier for Due Today display
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.description as equipment_desc,
               wo.id as open_wo_id,
               wo.work_order_number as open_wo_number,
               wo.status as open_wo_status,
               wo.due_date as open_wo_due_date
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        LEFT JOIN work_orders wo ON wo.maintenance_schedule_id = ms.id
            AND wo.status IN ('Open', 'In Progress', 'On Hold')
            AND wo.due_date <= ?
        WHERE ms.status = 'Active'
        ORDER BY ms.next_due_date ASC
    ''', (today,))
    rows = cursor.fetchall()

    # Group by schedule ID to handle multiple open work orders
    schedule_dict = {}
    for row in rows:
        schedule_id = row['id']
        if schedule_id not in schedule_dict:
            schedule = MaintenanceSchedule.from_row(row)
            schedule.equipment_tag = row['tag_number']
            schedule.equipment_desc = row['equipment_desc']
            schedule.open_work_orders = []
            schedule_dict[schedule_id] = schedule

        # Add open work order info if exists
        if row['open_wo_id']:
            schedule_dict[schedule_id].open_work_orders.append({
                'id': row['open_wo_id'],
                'number': row['open_wo_number'],
                'status': row['open_wo_status'],
                'due_date': row['open_wo_due_date']
            })

    overdue = []
    due_today = []
    upcoming = []

    for schedule_id, schedule in schedule_dict.items():
        # Check if any open work orders are overdue or due today
        has_overdue_wo = any(wo['due_date'] < today for wo in schedule.open_work_orders)
        has_due_today_wo = any(wo['due_date'] == today for wo in schedule.open_work_orders)

        # Get latest meter reading for meter-based schedules
        if schedule.is_meter_based():
            meter = get_latest_meter_reading(schedule.equipment_id)
            if meter:
                schedule.current_meter = meter['value']
                # Check for overdue by meter or work order
                if (schedule.next_due_meter and meter['value'] >= schedule.next_due_meter) or has_overdue_wo:
                    overdue.append(schedule)
                # Check for due today by work order
                elif has_due_today_wo:
                    due_today.append(schedule)
            continue

        # Time-based schedule checks - schedules can appear in multiple sections
        if schedule.is_time_based():
            added_to_overdue = False
            added_to_due_today = False
            added_to_upcoming = False

            # Has overdue work order - show in overdue section
            if has_overdue_wo:
                overdue.append(schedule)
                added_to_overdue = True

            # Has work order due today - show in due today
            if has_due_today_wo:
                due_today.append(schedule)
                added_to_due_today = True

            # Check next_due_date for additional categorization
            if schedule.next_due_date:
                # Overdue by date (only if not already in overdue)
                if schedule.next_due_date < today and not added_to_overdue:
                    overdue.append(schedule)
                # Due today by date - only if no open work orders exist
                # (if open WOs exist, schedule shows in Overdue/Due Today by WO, not by date)
                elif schedule.next_due_date == today and not added_to_due_today and not schedule.open_work_orders:
                    due_today.append(schedule)
                # Upcoming - show if next_due_date is in the future within 7 days
                # (only if no open work orders, otherwise handled by next_occurrence calculation)
                elif today < schedule.next_due_date <= week_ahead and not schedule.open_work_orders:
                    upcoming.append(schedule)
                    added_to_upcoming = True


    conn.close()

    return render_template('modules/maintenance_schedule/dashboard.html',
                           overdue=overdue, due_today=due_today, upcoming=upcoming)


@maintenance_schedules_bp.route('/list')
@login_required
def schedule_list():
    """List all maintenance schedules"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.description as equipment_desc
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        ORDER BY ms.status ASC, ms.name ASC
    ''')
    rows = cursor.fetchall()
    conn.close()

    schedules = []
    for row in rows:
        schedule = MaintenanceSchedule.from_row(row)
        schedule.equipment_tag = row['tag_number']
        schedule.equipment_desc = row['equipment_desc']
        schedules.append(schedule)

    return render_template('modules/maintenance_schedule/list.html', schedules=schedules)


@maintenance_schedules_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Create new maintenance schedule"""
    equipment_list = get_all_equipment()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        equipment_id = request.form.get('equipment_id', '').strip()
        schedule_type = request.form.get('schedule_type', 'time-based').strip()
        frequency = request.form.get('frequency', '').strip()
        initial_due_date = request.form.get('initial_due_date', '').strip()
        meter_interval = request.form.get('meter_interval', '').strip()
        meter_unit = request.form.get('meter_unit', '').strip()
        current_meter = request.form.get('current_meter', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        estimated_duration = request.form.get('estimated_duration', '').strip()
        instructions = request.form.get('instructions', '').strip()

        # Validation
        if not name:
            flash('Schedule name is required.', 'error')
            return render_template('modules/maintenance_schedule/add.html',
                                   equipment_list=equipment_list,
                                   schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                                   frequencies=MaintenanceSchedule.FREQUENCIES,
                                   priorities=MaintenanceSchedule.PRIORITIES)
        if not equipment_id:
            flash('Equipment is required.', 'error')
            return render_template('modules/maintenance_schedule/add.html',
                                   equipment_list=equipment_list,
                                   schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                                   frequencies=MaintenanceSchedule.FREQUENCIES,
                                   priorities=MaintenanceSchedule.PRIORITIES)

        equipment_id = int(equipment_id)
        estimated_duration = int(estimated_duration) if estimated_duration else None

        # Calculate next due based on schedule type
        next_due_date = None
        next_due_meter = None
        last_meter_reading = None

        if schedule_type == 'time-based':
            if not frequency:
                flash('Frequency is required for time-based schedules.', 'error')
                return render_template('modules/maintenance_schedule/add.html',
                                       equipment_list=equipment_list,
                                       schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                                       frequencies=MaintenanceSchedule.FREQUENCIES,
                                       priorities=MaintenanceSchedule.PRIORITIES)
            # Use initial due date if provided, otherwise calculate from today
            if initial_due_date:
                next_due_date = initial_due_date
            else:
                next_due_date = MaintenanceSchedule.calculate_next_due_date(frequency)
        else:  # meter-based
            if not meter_interval:
                flash('Meter interval is required for meter-based schedules.', 'error')
                return render_template('modules/maintenance_schedule/add.html',
                                       equipment_list=equipment_list,
                                       schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                                       frequencies=MaintenanceSchedule.FREQUENCIES,
                                       priorities=MaintenanceSchedule.PRIORITIES)
            meter_interval = int(meter_interval)
            current_meter = int(current_meter) if current_meter else 0
            last_meter_reading = current_meter
            next_due_meter = MaintenanceSchedule.calculate_next_due_meter(current_meter, meter_interval)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            schedule_id = generate_schedule_id()
            cursor.execute('''
                INSERT INTO maintenance_schedules (schedule_id, name, description, equipment_id, schedule_type,
                    frequency, meter_interval, meter_unit, last_meter_reading, next_due_date,
                    next_due_meter, priority, estimated_duration, instructions, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (schedule_id, name, description or None, equipment_id, schedule_type,
                  frequency or None, meter_interval if schedule_type == 'meter-based' else None,
                  meter_unit or None, last_meter_reading, next_due_date, next_due_meter,
                  priority, estimated_duration, instructions or None, current_user.id))
            conn.commit()
            conn.close()
            flash(f'Maintenance schedule "{schedule_id}" created successfully.', 'success')
            return redirect(url_for('maintenance_schedules.index'))
        except Exception as e:
            flash(f'Error creating schedule: {str(e)}', 'error')

    return render_template('modules/maintenance_schedule/add.html',
                           equipment_list=equipment_list,
                           schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                           frequencies=MaintenanceSchedule.FREQUENCIES,
                           priorities=MaintenanceSchedule.PRIORITIES)


@maintenance_schedules_bp.route('/view/<int:schedule_id>')
@login_required
def view_detail(schedule_id):
    """View schedule details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.description as equipment_desc
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        WHERE ms.id = ?
    ''', (schedule_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Schedule not found.', 'error')
        return redirect(url_for('maintenance_schedules.schedule_list'))

    schedule = MaintenanceSchedule.from_row(row)
    schedule.equipment_tag = row['tag_number']
    schedule.equipment_desc = row['equipment_desc']

    # Get latest meter reading if meter-based
    if schedule.is_meter_based():
        meter = get_latest_meter_reading(schedule.equipment_id)
        if meter:
            schedule.current_meter = meter['value']

    return render_template('modules/maintenance_schedule/view_detail.html', schedule=schedule)


@maintenance_schedules_bp.route('/change')
@login_required
def change_select():
    """Select schedule to change"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ms.*, e.tag_number
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        ORDER BY ms.name ASC
    ''')
    rows = cursor.fetchall()
    conn.close()

    schedules = []
    for row in rows:
        schedule = MaintenanceSchedule.from_row(row)
        schedule.equipment_tag = row['tag_number']
        schedules.append(schedule)

    return render_template('modules/maintenance_schedule/change_select.html', schedules=schedules)


@maintenance_schedules_bp.route('/change/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def change(schedule_id):
    """Edit maintenance schedule"""
    equipment_list = get_all_equipment()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM maintenance_schedules WHERE id = ?', (schedule_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Schedule not found.', 'error')
        return redirect(url_for('maintenance_schedules.change_select'))

    schedule = MaintenanceSchedule.from_row(row)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        equipment_id = request.form.get('equipment_id', '').strip()
        schedule_type = request.form.get('schedule_type', 'time-based').strip()
        frequency = request.form.get('frequency', '').strip()
        meter_interval = request.form.get('meter_interval', '').strip()
        meter_unit = request.form.get('meter_unit', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        estimated_duration = request.form.get('estimated_duration', '').strip()
        instructions = request.form.get('instructions', '').strip()
        status = request.form.get('status', 'Active').strip()

        # Validation
        if not name:
            flash('Schedule name is required.', 'error')
            conn.close()
            return render_template('modules/maintenance_schedule/change.html',
                                   schedule=schedule, equipment_list=equipment_list,
                                   schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                                   frequencies=MaintenanceSchedule.FREQUENCIES,
                                   priorities=MaintenanceSchedule.PRIORITIES,
                                   statuses=MaintenanceSchedule.STATUSES)

        equipment_id = int(equipment_id) if equipment_id else schedule.equipment_id
        estimated_duration = int(estimated_duration) if estimated_duration else None
        meter_interval = int(meter_interval) if meter_interval else None

        try:
            cursor.execute('''
                UPDATE maintenance_schedules
                SET name = ?, description = ?, equipment_id = ?, schedule_type = ?,
                    frequency = ?, meter_interval = ?, meter_unit = ?, priority = ?,
                    estimated_duration = ?, instructions = ?, status = ?
                WHERE id = ?
            ''', (name, description or None, equipment_id, schedule_type,
                  frequency or None, meter_interval, meter_unit or None,
                  priority, estimated_duration, instructions or None, status, schedule_id))
            conn.commit()
            conn.close()
            flash(f'Schedule "{name}" updated successfully.', 'success')
            return redirect(url_for('maintenance_schedules.index'))
        except Exception as e:
            conn.close()
            flash(f'Error updating schedule: {str(e)}', 'error')

    conn.close()
    return render_template('modules/maintenance_schedule/change.html',
                           schedule=schedule, equipment_list=equipment_list,
                           schedule_types=MaintenanceSchedule.SCHEDULE_TYPES,
                           frequencies=MaintenanceSchedule.FREQUENCIES,
                           priorities=MaintenanceSchedule.PRIORITIES,
                           statuses=MaintenanceSchedule.STATUSES)


@maintenance_schedules_bp.route('/create-work-order/<int:schedule_id>', methods=['POST'])
@login_required
def create_work_order(schedule_id):
    """Create a work order from a maintenance schedule"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get schedule
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.location
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        WHERE ms.id = ?
    ''', (schedule_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Schedule not found.', 'error')
        return redirect(url_for('maintenance_schedules.dashboard'))

    schedule = MaintenanceSchedule.from_row(row)
    equipment_tag = row['tag_number']
    equipment_location = row['location']

    # Generate PM work order number for scheduled maintenance
    wo_number = generate_pm_work_order_number()

    # Create work order
    wo_title = schedule.name
    wo_description = schedule.instructions or f"Preventive maintenance for {equipment_tag}"

    try:
        cursor.execute('''
            INSERT INTO work_orders (work_order_number, title, description, equipment_id,
                                     location_code, priority, status, created_by,
                                     maintenance_schedule_id, due_date)
            VALUES (?, ?, ?, ?, ?, ?, 'Open', ?, ?, ?)
        ''', (wo_number, wo_title, wo_description, schedule.equipment_id,
              equipment_location, schedule.priority, current_user.id,
              schedule.id, schedule.next_due_date or datetime.now().strftime('%Y-%m-%d')))

        # NOTE: Do NOT update next_due_date here.
        # The schedule stays in Due Today until the work order is completed.
        # next_due_date is advanced when the work order status changes to Completed.

        conn.commit()
        conn.close()
        flash(f'Work Order {wo_number} created successfully.', 'success')
    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f'Error creating work order: {str(e)}', 'error')

    return redirect(url_for('maintenance_schedules.dashboard'))
