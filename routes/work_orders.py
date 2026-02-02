import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.work_order import WorkOrder
from models.work_order_part import WorkOrderPart
from models.equipment import Equipment
from models.location import Location
from models.spare_part import SparePart
from models.maintenance_schedule import MaintenanceSchedule
from datetime import datetime

work_orders_bp = Blueprint('work_orders', __name__, url_prefix='/work-orders')


def get_active_locations():
    """Fetch all active locations for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations WHERE status = 'Active' ORDER BY location_code")
    rows = cursor.fetchall()
    conn.close()
    return [Location.from_row(row) for row in rows]


def get_all_equipment():
    """Fetch all equipment for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment ORDER BY tag_number")
    rows = cursor.fetchall()
    conn.close()
    return [Equipment.from_row(row) for row in rows]


def get_all_users():
    """Fetch all users for assignment dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users ORDER BY username")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': row['id'], 'username': row['username'], 'role': row['role']} for row in rows]


def generate_work_order_number():
    """Generate next work order number"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT work_order_number FROM work_orders ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return 'WO-0001'

    last_num = row['work_order_number']
    try:
        num = int(last_num.split('-')[1]) + 1
        return f'WO-{num:04d}'
    except:
        return f'WO-{datetime.now().strftime("%Y%m%d%H%M%S")}'


@work_orders_bp.route('/')
@login_required
def index():
    """Main work orders page with module options"""
    return render_template('modules/work_orders/index.html')


@work_orders_bp.route('/report')
@login_required
def work_order_report():
    """Work Order Report - overview of all work orders"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT wo.*,
               e.tag_number as equipment_tag,
               e.description as equipment_desc,
               u1.username as assigned_to_name,
               u2.username as created_by_name
        FROM work_orders wo
        LEFT JOIN equipment e ON wo.equipment_id = e.id
        LEFT JOIN users u1 ON wo.assigned_to = u1.id
        LEFT JOIN users u2 ON wo.created_by = u2.id
        ORDER BY
            CASE wo.status
                WHEN 'Open' THEN 1
                WHEN 'In Progress' THEN 2
                WHEN 'On Hold' THEN 3
                WHEN 'Completed' THEN 4
                WHEN 'Cancelled' THEN 5
            END,
            CASE wo.priority
                WHEN 'Emergency' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
            END,
            wo.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    work_orders = []
    for row in rows:
        wo = WorkOrder.from_row(row)
        wo.equipment_tag = row['equipment_tag'] if 'equipment_tag' in row.keys() else None
        wo.equipment_desc = row['equipment_desc'] if 'equipment_desc' in row.keys() else None
        wo.assigned_to_name = row['assigned_to_name'] if 'assigned_to_name' in row.keys() else None
        wo.created_by_name = row['created_by_name'] if 'created_by_name' in row.keys() else None
        work_orders.append(wo)

    return render_template('modules/work_orders/work_order_report.html', work_orders=work_orders)


@work_orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
def add():
    """Create new work order"""
    locations = get_active_locations()
    equipment_list = get_all_equipment()
    users = get_all_users()
    spare_parts = get_all_spare_parts()
    wo_number = generate_work_order_number()

    if request.method == 'POST':
        work_order_number = request.form.get('work_order_number', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        equipment_id = request.form.get('equipment_id', '').strip()
        location_code = request.form.get('location_code', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        status = request.form.get('status', 'Open').strip()
        assigned_to = request.form.get('assigned_to', '').strip()
        due_date = request.form.get('due_date', '').strip()
        parts_to_consume = request.form.get('parts_to_consume', '[]')

        # Convert to proper types
        equipment_id = int(equipment_id) if equipment_id else None
        assigned_to = int(assigned_to) if assigned_to else None

        # Parse parts to consume
        try:
            parts_list = json.loads(parts_to_consume)
        except:
            parts_list = []

        # Validation
        if not work_order_number:
            flash('Work Order Number is required.', 'error')
            return render_template('modules/work_orders/add.html',
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, wo_number=wo_number,
                                   spare_parts=spare_parts)
        if not title:
            flash('Title is required.', 'error')
            return render_template('modules/work_orders/add.html',
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, wo_number=wo_number,
                                   spare_parts=spare_parts)

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Create work order
            cursor.execute('''
                INSERT INTO work_orders (work_order_number, title, description, equipment_id,
                                         location_code, priority, status, assigned_to, created_by, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (work_order_number, title, description or None, equipment_id,
                  location_code or None, priority, status, assigned_to, current_user.id,
                  due_date or None))
            wo_id = cursor.lastrowid

            # Issue parts if any
            parts_issued = 0
            for part in parts_list:
                part_id = int(part.get('id', 0))
                qty = int(part.get('quantity', 0))
                if part_id > 0 and qty > 0:
                    # Get current MAP and inventory data
                    cursor.execute('''
                        SELECT quantity_available, moving_average_price, total_inventory_value
                        FROM spare_parts WHERE id = ?
                    ''', (part_id,))
                    sp_row = cursor.fetchone()

                    if sp_row and sp_row['quantity_available'] >= qty:
                        current_MAP = sp_row['moving_average_price'] or 0
                        current_inv_value = sp_row['total_inventory_value'] or 0

                        # Calculate new inventory value after issue (MAP stays same)
                        new_inv_value = current_inv_value - (qty * current_MAP)

                        # Deduct from inventory and update value
                        cursor.execute('''
                            UPDATE spare_parts
                            SET quantity_available = quantity_available - ?,
                                total_inventory_value = ?
                            WHERE id = ?
                        ''', (qty, new_inv_value, part_id))

                        # Insert transaction record WITH cost_per_unit
                        cursor.execute('''
                            INSERT INTO work_order_parts (work_order_id, spare_part_id, quantity,
                                                          transaction_type, transacted_by, cost_per_unit)
                            VALUES (?, ?, ?, 'issue', ?, ?)
                        ''', (wo_id, part_id, qty, current_user.id, current_MAP))
                        parts_issued += 1

            conn.commit()
            conn.close()

            msg = f'Work Order "{work_order_number}" created successfully.'
            if parts_issued > 0:
                msg += f' {parts_issued} part(s) issued.'
            flash(msg, 'success')
            return redirect(url_for('work_orders.index'))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                flash('Work Order Number already exists.', 'error')
            else:
                flash(f'Error creating work order: {str(e)}', 'error')
            return render_template('modules/work_orders/add.html',
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, wo_number=wo_number,
                                   spare_parts=spare_parts)

    return render_template('modules/work_orders/add.html',
                           locations=locations, equipment_list=equipment_list,
                           users=users, priorities=WorkOrder.PRIORITIES,
                           statuses=WorkOrder.STATUSES, wo_number=wo_number,
                           spare_parts=spare_parts)


@work_orders_bp.route('/view/<int:wo_id>')
@login_required
def view_detail(wo_id):
    """View a single work order's details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT wo.*,
               e.tag_number as equipment_tag,
               e.description as equipment_desc,
               u1.username as assigned_to_name,
               u2.username as created_by_name,
               ms.schedule_id as schedule_id,
               ms.name as schedule_name
        FROM work_orders wo
        LEFT JOIN equipment e ON wo.equipment_id = e.id
        LEFT JOIN users u1 ON wo.assigned_to = u1.id
        LEFT JOIN users u2 ON wo.created_by = u2.id
        LEFT JOIN maintenance_schedules ms ON wo.maintenance_schedule_id = ms.id
        WHERE wo.id = ?
    ''', (wo_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Work Order not found.', 'error')
        return redirect(url_for('work_orders.work_order_report'))

    wo = WorkOrder.from_row(row)
    wo.equipment_tag = row['equipment_tag'] if 'equipment_tag' in row.keys() else None
    wo.equipment_desc = row['equipment_desc'] if 'equipment_desc' in row.keys() else None
    wo.assigned_to_name = row['assigned_to_name'] if 'assigned_to_name' in row.keys() else None
    wo.created_by_name = row['created_by_name'] if 'created_by_name' in row.keys() else None
    wo.schedule_id = row['schedule_id'] if 'schedule_id' in row.keys() else None
    wo.schedule_name = row['schedule_name'] if 'schedule_name' in row.keys() else None

    # Get issued parts summary
    issued_parts = get_issued_parts_for_work_order(wo_id)

    return render_template('modules/work_orders/view_detail.html', work_order=wo, issued_parts=issued_parts)


@work_orders_bp.route('/change')
@login_required
def change_select():
    """Select work order to change"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT wo.*, e.tag_number as equipment_tag
        FROM work_orders wo
        LEFT JOIN equipment e ON wo.equipment_id = e.id
        ORDER BY wo.work_order_number DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    work_orders = []
    for row in rows:
        wo = WorkOrder.from_row(row)
        wo.equipment_tag = row['equipment_tag'] if 'equipment_tag' in row.keys() else None
        work_orders.append(wo)

    return render_template('modules/work_orders/change_select.html', work_orders=work_orders)


@work_orders_bp.route('/change/<int:wo_id>', methods=['GET', 'POST'])
@login_required
def change(wo_id):
    """Change/edit work order"""
    locations = get_active_locations()
    equipment_list = get_all_equipment()
    users = get_all_users()
    spare_parts = get_all_spare_parts()
    issued_parts = get_issued_parts_for_work_order(wo_id)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM work_orders WHERE id = ?', (wo_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Work Order not found.', 'error')
        return redirect(url_for('work_orders.change_select'))

    wo = WorkOrder.from_row(row)

    if request.method == 'POST':
        work_order_number = request.form.get('work_order_number', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        equipment_id = request.form.get('equipment_id', '').strip()
        location_code = request.form.get('location_code', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        status = request.form.get('status', 'Open').strip()
        assigned_to = request.form.get('assigned_to', '').strip()
        due_date = request.form.get('due_date', '').strip()
        parts_to_consume = request.form.get('parts_to_consume', '[]')

        # Convert to proper types
        equipment_id = int(equipment_id) if equipment_id else None
        assigned_to = int(assigned_to) if assigned_to else None

        # Parse parts to consume
        try:
            parts_list = json.loads(parts_to_consume)
        except:
            parts_list = []

        # Set completed_at if status changed to Completed
        completed_at = None
        if status == 'Completed' and wo.status != 'Completed':
            completed_at = datetime.now()

        # Validation
        if not work_order_number:
            flash('Work Order Number is required.', 'error')
            conn.close()
            return render_template('modules/work_orders/change.html', work_order=wo,
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, spare_parts=spare_parts,
                                   issued_parts=issued_parts)
        if not title:
            flash('Title is required.', 'error')
            conn.close()
            return render_template('modules/work_orders/change.html', work_order=wo,
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, spare_parts=spare_parts,
                                   issued_parts=issued_parts)

        try:
            if completed_at:
                cursor.execute('''
                    UPDATE work_orders
                    SET work_order_number = ?, title = ?, description = ?, equipment_id = ?,
                        location_code = ?, priority = ?, status = ?, assigned_to = ?,
                        due_date = ?, completed_at = ?
                    WHERE id = ?
                ''', (work_order_number, title, description or None, equipment_id,
                      location_code or None, priority, status, assigned_to,
                      due_date or None, completed_at, wo_id))
            else:
                cursor.execute('''
                    UPDATE work_orders
                    SET work_order_number = ?, title = ?, description = ?, equipment_id = ?,
                        location_code = ?, priority = ?, status = ?, assigned_to = ?, due_date = ?
                    WHERE id = ?
                ''', (work_order_number, title, description or None, equipment_id,
                      location_code or None, priority, status, assigned_to,
                      due_date or None, wo_id))

            # Issue parts if any (only if work order is not Completed/Cancelled)
            parts_issued = 0
            if wo.status not in ['Completed', 'Cancelled']:
                for part in parts_list:
                    part_id = int(part.get('id', 0))
                    qty = int(part.get('quantity', 0))
                    if part_id > 0 and qty > 0:
                        # Get current MAP and inventory data
                        cursor.execute('''
                            SELECT quantity_available, moving_average_price, total_inventory_value
                            FROM spare_parts WHERE id = ?
                        ''', (part_id,))
                        sp_row = cursor.fetchone()

                        if sp_row and sp_row['quantity_available'] >= qty:
                            current_MAP = sp_row['moving_average_price'] or 0
                            current_inv_value = sp_row['total_inventory_value'] or 0

                            # Calculate new inventory value after issue (MAP stays same)
                            new_inv_value = current_inv_value - (qty * current_MAP)

                            # Deduct from inventory and update value
                            cursor.execute('''
                                UPDATE spare_parts
                                SET quantity_available = quantity_available - ?,
                                    total_inventory_value = ?
                                WHERE id = ?
                            ''', (qty, new_inv_value, part_id))

                            # Insert transaction record WITH cost_per_unit
                            cursor.execute('''
                                INSERT INTO work_order_parts (work_order_id, spare_part_id, quantity,
                                                              transaction_type, transacted_by, cost_per_unit)
                                VALUES (?, ?, ?, 'issue', ?, ?)
                            ''', (wo_id, part_id, qty, current_user.id, current_MAP))
                            parts_issued += 1

            # If work order completed and linked to a maintenance schedule, advance the schedule
            if status == 'Completed' and wo.status != 'Completed' and row['maintenance_schedule_id']:
                schedule_id = row['maintenance_schedule_id']
                cursor.execute('SELECT * FROM maintenance_schedules WHERE id = ?', (schedule_id,))
                schedule_row = cursor.fetchone()

                if schedule_row:
                    schedule = MaintenanceSchedule.from_row(schedule_row)
                    completed_date = datetime.now().strftime('%Y-%m-%d')

                    if schedule.is_time_based():
                        next_due = MaintenanceSchedule.calculate_next_due_date(schedule.frequency, completed_date)
                        cursor.execute('''
                            UPDATE maintenance_schedules
                            SET last_performed_date = ?, next_due_date = ?
                            WHERE id = ?
                        ''', (completed_date, next_due, schedule_id))
                    else:  # meter-based
                        cursor.execute('''
                            SELECT reading_value FROM meter_readings
                            WHERE equipment_id = ?
                            ORDER BY recorded_at DESC LIMIT 1
                        ''', (schedule.equipment_id,))
                        meter_row = cursor.fetchone()
                        current_reading = meter_row['reading_value'] if meter_row else schedule.last_meter_reading or 0
                        next_meter = MaintenanceSchedule.calculate_next_due_meter(current_reading, schedule.meter_interval)
                        cursor.execute('''
                            UPDATE maintenance_schedules
                            SET last_performed_date = ?, last_meter_reading = ?, next_due_meter = ?
                            WHERE id = ?
                        ''', (completed_date, current_reading, next_meter, schedule_id))

            conn.commit()
            conn.close()

            msg = f'Work Order "{work_order_number}" updated successfully.'
            if parts_issued > 0:
                msg += f' {parts_issued} part(s) issued.'
            flash(msg, 'success')
            return redirect(url_for('work_orders.index'))
        except Exception as e:
            conn.close()
            flash(f'Error updating work order: {str(e)}', 'error')
            return render_template('modules/work_orders/change.html', work_order=wo,
                                   locations=locations, equipment_list=equipment_list,
                                   users=users, priorities=WorkOrder.PRIORITIES,
                                   statuses=WorkOrder.STATUSES, spare_parts=spare_parts,
                                   issued_parts=issued_parts)

    conn.close()
    return render_template('modules/work_orders/change.html', work_order=wo,
                           locations=locations, equipment_list=equipment_list,
                           users=users, priorities=WorkOrder.PRIORITIES,
                           statuses=WorkOrder.STATUSES, spare_parts=spare_parts,
                           issued_parts=issued_parts)


@work_orders_bp.route('/api/equipment/<int:equip_id>/location')
@login_required
def get_equipment_location(equip_id):
    """API endpoint to get equipment location for auto-fill"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT location FROM equipment WHERE id = ?', (equip_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row['location']:
        return jsonify({'location_code': row['location']})
    return jsonify({'location_code': ''})


def get_all_spare_parts():
    """Fetch all spare parts for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM spare_parts ORDER BY description")
    rows = cursor.fetchall()
    conn.close()
    return [SparePart.from_row(row) for row in rows]


def get_issued_parts_for_work_order(wo_id):
    """Get all issued parts for a work order with net quantities and costs"""
    conn = get_connection()
    cursor = conn.cursor()
    # Get net quantity per spare part (issues minus returns) with weighted average cost
    cursor.execute('''
        SELECT sp.id as spare_part_id, sp.description, sp.storage_location, sp.storage_bin,
               SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity ELSE -wop.quantity END) as net_quantity,
               AVG(CASE WHEN wop.transaction_type = 'issue' THEN wop.cost_per_unit END) as avg_cost_per_unit,
               SUM(CASE WHEN wop.transaction_type = 'issue' THEN wop.quantity * wop.cost_per_unit
                        ELSE -wop.quantity * wop.cost_per_unit END) as total_cost
        FROM work_order_parts wop
        JOIN spare_parts sp ON wop.spare_part_id = sp.id
        WHERE wop.work_order_id = ?
        GROUP BY sp.id
        HAVING net_quantity > 0
        ORDER BY sp.description
    ''', (wo_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_parts_transaction_history(wo_id):
    """Get full transaction history for a work order"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT wop.*, sp.description as spare_part_desc, u.username as transacted_by_name
        FROM work_order_parts wop
        JOIN spare_parts sp ON wop.spare_part_id = sp.id
        LEFT JOIN users u ON wop.transacted_by = u.id
        WHERE wop.work_order_id = ?
        ORDER BY wop.transacted_at DESC
    ''', (wo_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@work_orders_bp.route('/view/<int:wo_id>/goods-issue', methods=['GET', 'POST'])
@login_required
def goods_issue(wo_id):
    """Goods issue page - issue spare parts to work order"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get work order
    cursor.execute('''
        SELECT wo.*, e.tag_number as equipment_tag, e.description as equipment_desc
        FROM work_orders wo
        LEFT JOIN equipment e ON wo.equipment_id = e.id
        WHERE wo.id = ?
    ''', (wo_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Work Order not found.', 'error')
        return redirect(url_for('work_orders.work_order_report'))

    wo = WorkOrder.from_row(row)
    wo.equipment_tag = row['equipment_tag'] if 'equipment_tag' in row.keys() else None
    wo.equipment_desc = row['equipment_desc'] if 'equipment_desc' in row.keys() else None

    # Check if work order allows issuing parts
    if wo.status in ['Completed', 'Cancelled']:
        conn.close()
        flash(f'Cannot issue parts to a {wo.status} work order.', 'error')
        return redirect(url_for('work_orders.view_detail', wo_id=wo_id))

    if request.method == 'POST':
        spare_part_id = request.form.get('spare_part_id', '').strip()
        quantity = request.form.get('quantity', '').strip()
        notes = request.form.get('notes', '').strip()

        # Validation
        if not spare_part_id:
            flash('Please select a spare part.', 'error')
        elif not quantity or not quantity.isdigit() or int(quantity) <= 0:
            flash('Please enter a valid quantity (positive integer).', 'error')
        else:
            spare_part_id = int(spare_part_id)
            quantity = int(quantity)

            # Check spare part stock
            cursor.execute('SELECT * FROM spare_parts WHERE id = ?', (spare_part_id,))
            sp_row = cursor.fetchone()

            if sp_row is None:
                flash('Spare part not found.', 'error')
            elif sp_row['quantity_available'] < quantity:
                flash(f'Insufficient stock. Only {sp_row["quantity_available"]} available.', 'error')
            else:
                try:
                    # Get current MAP and inventory value
                    current_MAP = sp_row['moving_average_price'] or 0
                    current_inv_value = sp_row['total_inventory_value'] or 0

                    # Calculate new inventory value after issue (MAP stays same)
                    new_inv_value = current_inv_value - (quantity * current_MAP)

                    # Deduct from inventory and update value
                    cursor.execute('''
                        UPDATE spare_parts
                        SET quantity_available = quantity_available - ?,
                            total_inventory_value = ?
                        WHERE id = ?
                    ''', (quantity, new_inv_value, spare_part_id))

                    # Insert transaction record WITH cost_per_unit
                    cursor.execute('''
                        INSERT INTO work_order_parts (work_order_id, spare_part_id, quantity,
                                                      transaction_type, transacted_by, notes, cost_per_unit)
                        VALUES (?, ?, ?, 'issue', ?, ?, ?)
                    ''', (wo_id, spare_part_id, quantity, current_user.id, notes or None, current_MAP))

                    conn.commit()
                    flash(f'Successfully issued {quantity} units of "{sp_row["description"]}".', 'success')
                except Exception as e:
                    conn.rollback()
                    flash(f'Error issuing parts: {str(e)}', 'error')

    conn.close()

    # Get data for display
    spare_parts = get_all_spare_parts()
    issued_parts = get_issued_parts_for_work_order(wo_id)
    transaction_history = get_parts_transaction_history(wo_id)

    return render_template('modules/work_orders/goods_issue.html',
                           work_order=wo, spare_parts=spare_parts,
                           issued_parts=issued_parts, transaction_history=transaction_history)


@work_orders_bp.route('/view/<int:wo_id>/goods-return/<int:part_id>', methods=['POST'])
@login_required
def goods_return(wo_id, part_id):
    """Return spare parts from work order back to inventory"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get work order
    cursor.execute('SELECT * FROM work_orders WHERE id = ?', (wo_id,))
    wo_row = cursor.fetchone()

    if wo_row is None:
        conn.close()
        flash('Work Order not found.', 'error')
        return redirect(url_for('work_orders.work_order_report'))

    wo = WorkOrder.from_row(wo_row)

    # Check if work order allows returning parts
    if wo.status in ['Completed', 'Cancelled']:
        conn.close()
        flash(f'Cannot return parts from a {wo.status} work order.', 'error')
        return redirect(url_for('work_orders.view_detail', wo_id=wo_id))

    # Get the net issued quantity for this part
    cursor.execute('''
        SELECT SUM(CASE WHEN transaction_type = 'issue' THEN quantity ELSE -quantity END) as net_qty
        FROM work_order_parts
        WHERE work_order_id = ? AND spare_part_id = ?
    ''', (wo_id, part_id))
    net_row = cursor.fetchone()
    net_issued = net_row['net_qty'] if net_row and net_row['net_qty'] else 0

    quantity = request.form.get('quantity', '').strip()
    notes = request.form.get('notes', '').strip()

    if not quantity or not quantity.isdigit() or int(quantity) <= 0:
        conn.close()
        flash('Please enter a valid quantity (positive integer).', 'error')
        return redirect(url_for('work_orders.goods_issue', wo_id=wo_id))

    quantity = int(quantity)

    if quantity > net_issued:
        conn.close()
        flash(f'Cannot return more than issued. Maximum returnable: {net_issued}.', 'error')
        return redirect(url_for('work_orders.goods_issue', wo_id=wo_id))

    # Get spare part for message
    cursor.execute('SELECT description FROM spare_parts WHERE id = ?', (part_id,))
    sp_row = cursor.fetchone()
    sp_desc = sp_row['description'] if sp_row else 'Unknown'

    try:
        # Calculate weighted average cost from all issues
        cursor.execute('''
            SELECT AVG(cost_per_unit) as avg_cost, SUM(quantity) as total_issued
            FROM work_order_parts
            WHERE work_order_id = ? AND spare_part_id = ? AND transaction_type = 'issue'
        ''', (wo_id, part_id))
        issue_summary = cursor.fetchone()
        weighted_avg_cost = issue_summary['avg_cost'] if issue_summary and issue_summary['avg_cost'] else 0

        # Get current inventory data
        cursor.execute('''
            SELECT quantity_available, moving_average_price, total_inventory_value
            FROM spare_parts WHERE id = ?
        ''', (part_id,))
        sp_inv_row = cursor.fetchone()
        current_qty = sp_inv_row['quantity_available'] or 0
        current_inv_value = sp_inv_row['total_inventory_value'] or 0

        # Calculate new values after return
        new_qty = current_qty + quantity
        new_inv_value = current_inv_value + (quantity * weighted_avg_cost)
        new_MAP = new_inv_value / new_qty if new_qty > 0 else 0

        # Add back to inventory
        cursor.execute('''
            UPDATE spare_parts
            SET quantity_available = ?,
                total_inventory_value = ?,
                moving_average_price = ?
            WHERE id = ?
        ''', (new_qty, new_inv_value, new_MAP, part_id))

        # Insert return transaction record WITH cost_per_unit
        cursor.execute('''
            INSERT INTO work_order_parts (work_order_id, spare_part_id, quantity,
                                          transaction_type, transacted_by, notes, cost_per_unit)
            VALUES (?, ?, ?, 'return', ?, ?, ?)
        ''', (wo_id, part_id, quantity, current_user.id, notes or None, weighted_avg_cost))

        conn.commit()
        flash(f'Successfully returned {quantity} units of "{sp_desc}".', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error returning parts: {str(e)}', 'error')

    conn.close()
    return redirect(url_for('work_orders.goods_issue', wo_id=wo_id))
