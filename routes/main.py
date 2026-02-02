from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.maintenance_schedule import MaintenanceSchedule
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)


def auto_create_due_work_orders():
    """Check for due maintenance schedules and auto-create work orders"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    # Get SCHEDULE system user ID
    cursor.execute("SELECT id FROM users WHERE username = 'SCHEDULE'")
    schedule_user_row = cursor.fetchone()
    if schedule_user_row is None:
        conn.close()
        return 0  # SCHEDULE user not found, cannot auto-create
    schedule_user_id = schedule_user_row['id']

    # Find all time-based schedules that are due (next_due_date <= today)
    # and don't already have an open work order
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.location
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        WHERE ms.status = 'Active'
        AND ms.schedule_type = 'time-based'
        AND ms.next_due_date IS NOT NULL
        AND ms.next_due_date <= ?
        AND NOT EXISTS (
            SELECT 1 FROM work_orders wo
            WHERE wo.maintenance_schedule_id = ms.id
            AND wo.status IN ('Open', 'In Progress', 'On Hold')
        )
    ''', (today,))

    due_schedules = cursor.fetchall()
    work_orders_created = 0

    for row in due_schedules:
        schedule = MaintenanceSchedule.from_row(row)
        equipment_tag = row['tag_number']
        equipment_location = row['location']

        # Generate PM work order number for scheduled maintenance
        cursor.execute("SELECT work_order_number FROM work_orders WHERE work_order_number LIKE 'PM-%' ORDER BY id DESC LIMIT 1")
        wo_row = cursor.fetchone()
        if wo_row is None:
            wo_number = 'PM-0001'
        else:
            try:
                num = int(wo_row['work_order_number'].split('-')[1]) + 1
                wo_number = f'PM-{num:04d}'
            except:
                wo_number = f'PM-{datetime.now().strftime("%Y%m%d%H%M%S")}'

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
                  equipment_location, schedule.priority, schedule_user_id,
                  schedule.id, schedule.next_due_date))

            # NOTE: Do NOT update next_due_date here.
            # The schedule stays in Due Today until the work order is completed.

            work_orders_created += 1
        except Exception as e:
            # Skip if error (e.g., duplicate)
            pass

    # Also check meter-based schedules that don't have an open work order
    cursor.execute('''
        SELECT ms.*, e.tag_number, e.location,
               (SELECT reading_value FROM meter_readings mr
                WHERE mr.equipment_id = ms.equipment_id
                ORDER BY mr.recorded_at DESC LIMIT 1) as current_reading
        FROM maintenance_schedules ms
        JOIN equipment e ON ms.equipment_id = e.id
        WHERE ms.status = 'Active'
        AND ms.schedule_type = 'meter-based'
        AND ms.next_due_meter IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM work_orders wo
            WHERE wo.maintenance_schedule_id = ms.id
            AND wo.status IN ('Open', 'In Progress', 'On Hold')
        )
    ''')

    meter_schedules = cursor.fetchall()

    for row in meter_schedules:
        current_reading = row['current_reading']
        if current_reading is None:
            continue

        schedule = MaintenanceSchedule.from_row(row)
        if current_reading < schedule.next_due_meter:
            continue

        equipment_tag = row['tag_number']
        equipment_location = row['location']

        # Generate PM work order number for scheduled maintenance
        cursor.execute("SELECT work_order_number FROM work_orders WHERE work_order_number LIKE 'PM-%' ORDER BY id DESC LIMIT 1")
        wo_row = cursor.fetchone()
        if wo_row is None:
            wo_number = 'PM-0001'
        else:
            try:
                num = int(wo_row['work_order_number'].split('-')[1]) + 1
                wo_number = f'PM-{num:04d}'
            except:
                wo_number = f'PM-{datetime.now().strftime("%Y%m%d%H%M%S")}'

        wo_title = schedule.name
        wo_description = schedule.instructions or f"Preventive maintenance for {equipment_tag}"

        try:
            cursor.execute('''
                INSERT INTO work_orders (work_order_number, title, description, equipment_id,
                                         location_code, priority, status, created_by,
                                         maintenance_schedule_id, due_date)
                VALUES (?, ?, ?, ?, ?, ?, 'Open', ?, ?, ?)
            ''', (wo_number, wo_title, wo_description, schedule.equipment_id,
                  equipment_location, schedule.priority, schedule_user_id,
                  schedule.id, today))

            # NOTE: Do NOT update next_due_meter here.
            # The schedule stays in Due Today until the work order is completed.

            work_orders_created += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()

    return work_orders_created


@main_bp.route('/')
@main_bp.route('/home')
@login_required
def home():
    # Auto-create work orders for due maintenance schedules
    wo_created = auto_create_due_work_orders()
    if wo_created > 0:
        flash(f'{wo_created} work order(s) auto-created for due maintenance schedules.', 'info')

    return render_template('home.html')

# Module routes - redirect to actual modules or placeholder pages
@main_bp.route('/maintenance-schedule')
@login_required
def maintenance_schedule():
    return redirect(url_for('maintenance_schedules.index'))

@main_bp.route('/orders')
@login_required
def orders():
    return redirect(url_for('orders.index'))

@main_bp.route('/organization')
@login_required
def organization():
    return render_template('modules/organization.html', module_name='Organization')
