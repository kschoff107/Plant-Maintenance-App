from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from database.init_db import get_connection
from models.spare_part import SparePart

spare_parts_bp = Blueprint('spare_parts', __name__, url_prefix='/spare-parts')


@spare_parts_bp.route('/')
@login_required
def index():
    """Main spare parts page with module options"""
    return render_template('modules/spare_parts/index.html')


@spare_parts_bp.route('/inventory')
@login_required
def inventory():
    """Inventory Report / Spare Parts List"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts ORDER BY description')
    rows = cursor.fetchall()
    conn.close()

    spare_parts = [SparePart.from_row(row) for row in rows]
    return render_template('modules/spare_parts/inventory.html', spare_parts=spare_parts)


@spare_parts_bp.route('/master-data')
@login_required
def master_data():
    """Master Data menu with Add, Change, View options"""
    return render_template('modules/spare_parts/master_data.html')


@spare_parts_bp.route('/master-data/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new spare part"""
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        vendor_description = request.form.get('vendor_description', '').strip()
        storage_location = request.form.get('storage_location', '').strip()
        storage_bin = request.form.get('storage_bin', '').strip()
        rounding_value = request.form.get('rounding_value', '').strip()
        maximum_stock = request.form.get('maximum_stock', '').strip()

        # Convert to integers or None
        rounding_value = int(rounding_value) if rounding_value else None
        maximum_stock = int(maximum_stock) if maximum_stock else None

        # Validation
        if not description:
            flash('Description is required.', 'error')
            return render_template('modules/spare_parts/add.html')

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO spare_parts (description, vendor_description, storage_location, storage_bin, rounding_value, maximum_stock)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (description, vendor_description, storage_location, storage_bin, rounding_value, maximum_stock))
            conn.commit()
            conn.close()
            flash(f'Spare part "{description}" created successfully.', 'success')
            return redirect(url_for('spare_parts.master_data'))
        except Exception as e:
            flash(f'Error creating spare part: {str(e)}', 'error')
            return render_template('modules/spare_parts/add.html')

    return render_template('modules/spare_parts/add.html')


@spare_parts_bp.route('/master-data/view/<int:part_id>')
@login_required
def view_detail(part_id):
    """View a single spare part's details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts WHERE id = ?', (part_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Spare part not found.', 'error')
        return redirect(url_for('spare_parts.inventory'))

    spare_part = SparePart.from_row(row)
    return render_template('modules/spare_parts/view_detail.html', spare_part=spare_part)


@spare_parts_bp.route('/master-data/change')
@login_required
def change_select():
    """Select a spare part to change"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts ORDER BY description')
    rows = cursor.fetchall()
    conn.close()

    spare_parts = [SparePart.from_row(row) for row in rows]
    return render_template('modules/spare_parts/change_select.html', spare_parts=spare_parts)


@spare_parts_bp.route('/master-data/change/<int:part_id>', methods=['GET', 'POST'])
@login_required
def change(part_id):
    """Change/edit a spare part"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts WHERE id = ?', (part_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Spare part not found.', 'error')
        return redirect(url_for('spare_parts.change_select'))

    spare_part = SparePart.from_row(row)

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        vendor_description = request.form.get('vendor_description', '').strip()
        storage_location = request.form.get('storage_location', '').strip()
        storage_bin = request.form.get('storage_bin', '').strip()
        rounding_value = request.form.get('rounding_value', '').strip()
        maximum_stock = request.form.get('maximum_stock', '').strip()

        # Convert to integers or None
        rounding_value = int(rounding_value) if rounding_value else None
        maximum_stock = int(maximum_stock) if maximum_stock else None

        # Validation
        if not description:
            flash('Description is required.', 'error')
            conn.close()
            return render_template('modules/spare_parts/change.html', spare_part=spare_part)

        try:
            cursor.execute('''
                UPDATE spare_parts
                SET description = ?, vendor_description = ?, storage_location = ?, storage_bin = ?, rounding_value = ?, maximum_stock = ?
                WHERE id = ?
            ''', (description, vendor_description, storage_location, storage_bin, rounding_value, maximum_stock, part_id))
            conn.commit()
            conn.close()
            flash(f'Spare part "{description}" updated successfully.', 'success')
            return redirect(url_for('spare_parts.master_data'))
        except Exception as e:
            conn.close()
            flash(f'Error updating spare part: {str(e)}', 'error')
            return render_template('modules/spare_parts/change.html', spare_part=spare_part)

    conn.close()
    return render_template('modules/spare_parts/change.html', spare_part=spare_part)
