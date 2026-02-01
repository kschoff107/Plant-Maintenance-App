from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from database.init_db import get_connection
from models.equipment import Equipment
from models.location import Location

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')


def get_active_locations():
    """Fetch all active locations for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations WHERE status = 'Active' ORDER BY location_code")
    rows = cursor.fetchall()
    conn.close()
    return [Location.from_row(row) for row in rows]


def validate_location_code(location_code):
    """Check if location code exists in locations table"""
    if not location_code:
        return True  # Empty location is allowed
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM locations WHERE location_code = ?", (location_code,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


@equipment_bp.route('/')
@login_required
def index():
    """Main equipment page with module options"""
    return render_template('modules/equipment/index.html')


@equipment_bp.route('/list')
@login_required
def equipment_list():
    """Equipment List - overview of all equipment"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment ORDER BY tag_number')
    rows = cursor.fetchall()
    conn.close()

    equipment = [Equipment.from_row(row) for row in rows]
    return render_template('modules/equipment/equipment_list.html', equipment=equipment)


@equipment_bp.route('/master-data')
@login_required
def master_data():
    """Master Data menu with Add, Change, View options"""
    return render_template('modules/equipment/master_data.html')


@equipment_bp.route('/master-data/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new equipment"""
    locations = get_active_locations()

    if request.method == 'POST':
        tag_number = request.form.get('tag_number', '').strip()
        description = request.form.get('description', '').strip()
        manufacturer = request.form.get('manufacturer', '').strip()
        model_number = request.form.get('model_number', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        location = request.form.get('location', '').strip()
        installation_date = request.form.get('installation_date', '').strip()
        status = request.form.get('status', 'Active').strip()

        # Validation
        if not tag_number:
            flash('Tag Number is required.', 'error')
            return render_template('modules/equipment/add.html', statuses=Equipment.STATUSES, locations=locations)
        if not description:
            flash('Description is required.', 'error')
            return render_template('modules/equipment/add.html', statuses=Equipment.STATUSES, locations=locations)
        if location and not validate_location_code(location):
            flash(f'Location Code "{location}" does not exist. Please select a valid location.', 'error')
            return render_template('modules/equipment/add.html', statuses=Equipment.STATUSES, locations=locations)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO equipment (tag_number, description, manufacturer, model_number,
                                       serial_number, location, installation_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tag_number, description, manufacturer or None, model_number or None,
                  serial_number or None, location or None, installation_date or None, status))
            conn.commit()
            conn.close()
            flash(f'Equipment "{description}" created successfully.', 'success')
            return redirect(url_for('equipment.master_data'))
        except Exception as e:
            flash(f'Error creating equipment: {str(e)}', 'error')
            return render_template('modules/equipment/add.html', statuses=Equipment.STATUSES, locations=locations)

    return render_template('modules/equipment/add.html', statuses=Equipment.STATUSES, locations=locations)


@equipment_bp.route('/master-data/view/<int:equip_id>')
@login_required
def view_detail(equip_id):
    """View a single equipment's details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment WHERE id = ?', (equip_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Equipment not found.', 'error')
        return redirect(url_for('equipment.equipment_list'))

    equip = Equipment.from_row(row)
    return render_template('modules/equipment/view_detail.html', equipment=equip)


@equipment_bp.route('/master-data/change')
@login_required
def change_select():
    """Select equipment to change"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment ORDER BY tag_number')
    rows = cursor.fetchall()
    conn.close()

    equipment = [Equipment.from_row(row) for row in rows]
    return render_template('modules/equipment/change_select.html', equipment=equipment)


@equipment_bp.route('/master-data/change/<int:equip_id>', methods=['GET', 'POST'])
@login_required
def change(equip_id):
    """Change/edit equipment"""
    locations = get_active_locations()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment WHERE id = ?', (equip_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Equipment not found.', 'error')
        return redirect(url_for('equipment.change_select'))

    equip = Equipment.from_row(row)

    if request.method == 'POST':
        tag_number = request.form.get('tag_number', '').strip()
        description = request.form.get('description', '').strip()
        manufacturer = request.form.get('manufacturer', '').strip()
        model_number = request.form.get('model_number', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        location = request.form.get('location', '').strip()
        installation_date = request.form.get('installation_date', '').strip()
        status = request.form.get('status', 'Active').strip()

        # Validation
        if not tag_number:
            flash('Tag Number is required.', 'error')
            conn.close()
            return render_template('modules/equipment/change.html', equipment=equip, statuses=Equipment.STATUSES, locations=locations)
        if not description:
            flash('Description is required.', 'error')
            conn.close()
            return render_template('modules/equipment/change.html', equipment=equip, statuses=Equipment.STATUSES, locations=locations)
        if location and not validate_location_code(location):
            flash(f'Location Code "{location}" does not exist. Please select a valid location.', 'error')
            conn.close()
            return render_template('modules/equipment/change.html', equipment=equip, statuses=Equipment.STATUSES, locations=locations)

        try:
            cursor.execute('''
                UPDATE equipment
                SET tag_number = ?, description = ?, manufacturer = ?, model_number = ?,
                    serial_number = ?, location = ?, installation_date = ?, status = ?
                WHERE id = ?
            ''', (tag_number, description, manufacturer or None, model_number or None,
                  serial_number or None, location or None, installation_date or None, status, equip_id))
            conn.commit()
            conn.close()
            flash(f'Equipment "{description}" updated successfully.', 'success')
            return redirect(url_for('equipment.master_data'))
        except Exception as e:
            conn.close()
            flash(f'Error updating equipment: {str(e)}', 'error')
            return render_template('modules/equipment/change.html', equipment=equip, statuses=Equipment.STATUSES, locations=locations)

    conn.close()
    return render_template('modules/equipment/change.html', equipment=equip, statuses=Equipment.STATUSES, locations=locations)
