from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from database.init_db import get_connection
from models.location import Location

location_bp = Blueprint('location', __name__, url_prefix='/location')


@location_bp.route('/')
@login_required
def index():
    """Main location page with module options"""
    return render_template('modules/location/index.html')


@location_bp.route('/list')
@login_required
def location_list():
    """Location List - overview of all locations"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations ORDER BY location_code')
    rows = cursor.fetchall()
    conn.close()

    locations = [Location.from_row(row) for row in rows]
    return render_template('modules/location/location_list.html', locations=locations)


@location_bp.route('/master-data')
@login_required
def master_data():
    """Master Data menu with Add, Change options"""
    return render_template('modules/location/master_data.html')


@location_bp.route('/master-data/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new location"""
    if request.method == 'POST':
        location_code = request.form.get('location_code', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        location_type = request.form.get('location_type', 'Area').strip()
        status = request.form.get('status', 'Active').strip()

        # Validation
        if not location_code:
            flash('Location Code is required.', 'error')
            return render_template('modules/location/add.html',
                                   types=Location.TYPES, statuses=Location.STATUSES)
        if not name:
            flash('Name is required.', 'error')
            return render_template('modules/location/add.html',
                                   types=Location.TYPES, statuses=Location.STATUSES)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO locations (location_code, name, description, location_type, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (location_code, name, description or None, location_type, status))
            conn.commit()
            conn.close()
            flash(f'Location "{name}" created successfully.', 'success')
            return redirect(url_for('location.master_data'))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                flash('Location Code already exists. Please use a unique code.', 'error')
            else:
                flash(f'Error creating location: {str(e)}', 'error')
            return render_template('modules/location/add.html',
                                   types=Location.TYPES, statuses=Location.STATUSES)

    return render_template('modules/location/add.html',
                           types=Location.TYPES, statuses=Location.STATUSES)


@location_bp.route('/master-data/view/<int:loc_id>')
@login_required
def view_detail(loc_id):
    """View a single location's details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations WHERE id = ?', (loc_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Location not found.', 'error')
        return redirect(url_for('location.location_list'))

    loc = Location.from_row(row)
    return render_template('modules/location/view_detail.html', location=loc)


@location_bp.route('/master-data/change')
@login_required
def change_select():
    """Select location to change"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations ORDER BY location_code')
    rows = cursor.fetchall()
    conn.close()

    locations = [Location.from_row(row) for row in rows]
    return render_template('modules/location/change_select.html', locations=locations)


@location_bp.route('/master-data/change/<int:loc_id>', methods=['GET', 'POST'])
@login_required
def change(loc_id):
    """Change/edit location"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM locations WHERE id = ?', (loc_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Location not found.', 'error')
        return redirect(url_for('location.change_select'))

    loc = Location.from_row(row)

    if request.method == 'POST':
        location_code = request.form.get('location_code', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        location_type = request.form.get('location_type', 'Area').strip()
        status = request.form.get('status', 'Active').strip()

        # Validation
        if not location_code:
            flash('Location Code is required.', 'error')
            conn.close()
            return render_template('modules/location/change.html', location=loc,
                                   types=Location.TYPES, statuses=Location.STATUSES)
        if not name:
            flash('Name is required.', 'error')
            conn.close()
            return render_template('modules/location/change.html', location=loc,
                                   types=Location.TYPES, statuses=Location.STATUSES)

        try:
            cursor.execute('''
                UPDATE locations
                SET location_code = ?, name = ?, description = ?, location_type = ?, status = ?
                WHERE id = ?
            ''', (location_code, name, description or None, location_type, status, loc_id))
            conn.commit()
            conn.close()
            flash(f'Location "{name}" updated successfully.', 'success')
            return redirect(url_for('location.master_data'))
        except Exception as e:
            conn.close()
            if 'UNIQUE constraint failed' in str(e):
                flash('Location Code already exists. Please use a unique code.', 'error')
            else:
                flash(f'Error updating location: {str(e)}', 'error')
            return render_template('modules/location/change.html', location=loc,
                                   types=Location.TYPES, statuses=Location.STATUSES)

    conn.close()
    return render_template('modules/location/change.html', location=loc,
                           types=Location.TYPES, statuses=Location.STATUSES)
