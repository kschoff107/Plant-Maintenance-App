from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.meter_reading import MeterReading
from models.equipment import Equipment

meter_readings_bp = Blueprint('meter_readings', __name__, url_prefix='/meter-readings')


def get_all_equipment():
    """Fetch all active equipment for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment WHERE status = 'Active' ORDER BY tag_number")
    rows = cursor.fetchall()
    conn.close()
    return [Equipment.from_row(row) for row in rows]


@meter_readings_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new meter reading"""
    equipment_list = get_all_equipment()
    preselected_equipment = request.args.get('equipment_id', '')

    if request.method == 'POST':
        equipment_id = request.form.get('equipment_id', '').strip()
        reading_value = request.form.get('reading_value', '').strip()
        reading_unit = request.form.get('reading_unit', '').strip()
        notes = request.form.get('notes', '').strip()

        # Validation
        if not equipment_id:
            flash('Equipment is required.', 'error')
            return render_template('modules/meter_readings/add.html',
                                   equipment_list=equipment_list,
                                   units=MeterReading.COMMON_UNITS,
                                   preselected_equipment=preselected_equipment)

        if not reading_value or not reading_value.isdigit():
            flash('Valid meter reading value is required.', 'error')
            return render_template('modules/meter_readings/add.html',
                                   equipment_list=equipment_list,
                                   units=MeterReading.COMMON_UNITS,
                                   preselected_equipment=preselected_equipment)

        equipment_id = int(equipment_id)
        reading_value = int(reading_value)

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Insert the reading
            cursor.execute('''
                INSERT INTO meter_readings (equipment_id, reading_value, reading_unit, recorded_by, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (equipment_id, reading_value, reading_unit or None, current_user.id, notes or None))

            # Check if any meter-based schedules are now due
            cursor.execute('''
                SELECT ms.id, ms.name, ms.next_due_meter
                FROM maintenance_schedules ms
                WHERE ms.equipment_id = ? AND ms.schedule_type = 'meter-based'
                AND ms.status = 'Active' AND ms.next_due_meter IS NOT NULL
                AND ms.next_due_meter <= ?
            ''', (equipment_id, reading_value))

            due_schedules = cursor.fetchall()

            conn.commit()
            conn.close()

            if due_schedules:
                schedule_names = ', '.join([s['name'] for s in due_schedules])
                flash(f'Meter reading recorded. Maintenance due: {schedule_names}', 'warning')
            else:
                flash('Meter reading recorded successfully.', 'success')

            # Redirect back to equipment detail if came from there
            return_to = request.form.get('return_to', '')
            if return_to:
                return redirect(return_to)

            return redirect(url_for('meter_readings.add'))

        except Exception as e:
            flash(f'Error recording meter reading: {str(e)}', 'error')

    return render_template('modules/meter_readings/add.html',
                           equipment_list=equipment_list,
                           units=MeterReading.COMMON_UNITS,
                           preselected_equipment=preselected_equipment)


@meter_readings_bp.route('/history/<int:equipment_id>')
@login_required
def history(equipment_id):
    """View meter reading history for an equipment"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get equipment info
    cursor.execute('SELECT * FROM equipment WHERE id = ?', (equipment_id,))
    equip_row = cursor.fetchone()

    if equip_row is None:
        conn.close()
        flash('Equipment not found.', 'error')
        return redirect(url_for('equipment.index'))

    equipment = Equipment.from_row(equip_row)

    # Get readings
    cursor.execute('''
        SELECT mr.*, u.username as recorded_by_name
        FROM meter_readings mr
        LEFT JOIN users u ON mr.recorded_by = u.id
        WHERE mr.equipment_id = ?
        ORDER BY mr.recorded_at DESC
    ''', (equipment_id,))
    rows = cursor.fetchall()
    conn.close()

    readings = []
    for row in rows:
        reading = MeterReading.from_row(row)
        reading.recorded_by_name = row['recorded_by_name'] if 'recorded_by_name' in row.keys() else None
        readings.append(reading)

    return render_template('modules/meter_readings/history.html',
                           equipment=equipment, readings=readings)


@meter_readings_bp.route('/api/latest/<int:equipment_id>')
@login_required
def api_latest(equipment_id):
    """API endpoint to get latest meter reading for equipment"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reading_value, reading_unit, recorded_at
        FROM meter_readings
        WHERE equipment_id = ?
        ORDER BY recorded_at DESC LIMIT 1
    ''', (equipment_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            'value': row['reading_value'],
            'unit': row['reading_unit'],
            'recorded_at': row['recorded_at']
        })
    return jsonify({'value': None, 'unit': None, 'recorded_at': None})
