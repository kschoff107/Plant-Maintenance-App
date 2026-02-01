from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.vendor import Vendor
from datetime import datetime

vendors_bp = Blueprint('vendors', __name__, url_prefix='/vendors')


def generate_vendor_id():
    """Generate next vendor ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT vendor_id FROM vendors ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return 'V-0001'
    try:
        num = int(row['vendor_id'].split('-')[1]) + 1
        return f'V-{num:04d}'
    except:
        return f'V-{datetime.now().strftime("%Y%m%d%H%M%S")}'


@vendors_bp.route('/')
@login_required
def index():
    """Vendors sub-module index page"""
    return render_template('modules/vendors/index.html')


@vendors_bp.route('/list')
@login_required
def vendor_list():
    """List all vendors"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors ORDER BY name")
    rows = cursor.fetchall()
    conn.close()

    vendors = [Vendor.from_row(row) for row in rows]
    return render_template('modules/vendors/vendor_list.html', vendors=vendors)


@vendors_bp.route('/master-data')
@login_required
def master_data():
    """Vendor master data menu"""
    return render_template('modules/vendors/master_data.html')


@vendors_bp.route('/master-data/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new vendor"""
    vendor_id = generate_vendor_id()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact_name = request.form.get('contact_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'Active')

        if not name:
            flash('Vendor name is required.', 'error')
            return render_template('modules/vendors/add.html', vendor_id=vendor_id)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vendors (vendor_id, name, contact_name, email, phone, address, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (vendor_id, name, contact_name or None, email or None,
                  phone or None, address or None, status))
            conn.commit()
            conn.close()

            flash(f'Vendor {vendor_id} created successfully.', 'success')
            return redirect(url_for('vendors.master_data'))

        except Exception as e:
            flash(f'Error creating vendor: {str(e)}', 'error')
            return render_template('modules/vendors/add.html', vendor_id=vendor_id)

    return render_template('modules/vendors/add.html', vendor_id=vendor_id,
                           statuses=Vendor.STATUSES)


@vendors_bp.route('/master-data/view/<int:vendor_id>')
@login_required
def view_detail(vendor_id):
    """View vendor details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vendors WHERE id = ?', (vendor_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        flash('Vendor not found.', 'error')
        return redirect(url_for('vendors.vendor_list'))

    vendor = Vendor.from_row(row)
    return render_template('modules/vendors/view_detail.html', vendor=vendor)


@vendors_bp.route('/master-data/change')
@login_required
def change_select():
    """Select vendor to edit"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors ORDER BY name")
    rows = cursor.fetchall()
    conn.close()

    vendors = [Vendor.from_row(row) for row in rows]
    return render_template('modules/vendors/change_select.html', vendors=vendors)


@vendors_bp.route('/master-data/change/<int:vendor_id>', methods=['GET', 'POST'])
@login_required
def change(vendor_id):
    """Edit a vendor"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vendors WHERE id = ?', (vendor_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        flash('Vendor not found.', 'error')
        return redirect(url_for('vendors.change_select'))

    vendor = Vendor.from_row(row)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact_name = request.form.get('contact_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'Active')

        if not name:
            flash('Vendor name is required.', 'error')
            return render_template('modules/vendors/change.html', vendor=vendor,
                                   statuses=Vendor.STATUSES)

        try:
            cursor.execute('''
                UPDATE vendors
                SET name = ?, contact_name = ?, email = ?, phone = ?, address = ?, status = ?
                WHERE id = ?
            ''', (name, contact_name or None, email or None, phone or None,
                  address or None, status, vendor_id))
            conn.commit()
            conn.close()

            flash(f'Vendor {vendor.vendor_id} updated successfully.', 'success')
            return redirect(url_for('vendors.view_detail', vendor_id=vendor_id))

        except Exception as e:
            conn.close()
            flash(f'Error updating vendor: {str(e)}', 'error')
            return render_template('modules/vendors/change.html', vendor=vendor,
                                   statuses=Vendor.STATUSES)

    conn.close()
    return render_template('modules/vendors/change.html', vendor=vendor,
                           statuses=Vendor.STATUSES)
