from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.init_db import get_connection
from models.vendor import Vendor
from models.purchase_order import PurchaseOrder
from models.purchase_order_line import PurchaseOrderLine
from models.spare_part import SparePart
from datetime import datetime
import json

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


def get_all_vendors():
    """Get all active vendors"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors WHERE status = 'Active' ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [Vendor.from_row(row) for row in rows]


def get_all_spare_parts():
    """Get all spare parts for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM spare_parts ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [SparePart.from_row(row) for row in rows]


def generate_po_number():
    """Generate next PO number"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT po_number FROM purchase_orders ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return 'PO-0001'
    try:
        num = int(row['po_number'].split('-')[1]) + 1
        return f'PO-{num:04d}'
    except:
        return f'PO-{datetime.now().strftime("%Y%m%d%H%M%S")}'


@orders_bp.route('/')
@login_required
def index():
    """Orders module index page"""
    return render_template('modules/orders/index.html')


@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new purchase order"""
    vendors = get_all_vendors()
    spare_parts = get_all_spare_parts()
    po_number = generate_po_number()
    today = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id', '').strip()
        order_date = request.form.get('order_date', today).strip()
        expected_delivery_date = request.form.get('expected_delivery_date', '').strip()
        notes = request.form.get('notes', '').strip()
        line_items_json = request.form.get('line_items', '[]')

        # Validation
        if not vendor_id:
            flash('Please select a vendor.', 'error')
            return render_template('modules/orders/create.html',
                                   vendors=vendors, spare_parts=spare_parts,
                                   po_number=po_number, today=today)

        try:
            line_items = json.loads(line_items_json)
        except:
            line_items = []

        if len(line_items) == 0:
            flash('Please add at least one line item.', 'error')
            return render_template('modules/orders/create.html',
                                   vendors=vendors, spare_parts=spare_parts,
                                   po_number=po_number, today=today)

        # Calculate total
        total_amount = sum(float(item.get('line_total', 0)) for item in line_items)

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Insert purchase order
            cursor.execute('''
                INSERT INTO purchase_orders (po_number, vendor_id, order_date,
                                             expected_delivery_date, status, total_amount,
                                             notes, created_by)
                VALUES (?, ?, ?, ?, 'Open', ?, ?, ?)
            ''', (po_number, vendor_id, order_date, expected_delivery_date or None,
                  total_amount, notes or None, current_user.id))

            po_id = cursor.lastrowid

            # Insert line items
            for item in line_items:
                spare_part_id = int(item.get('spare_part_id', 0))
                quantity = int(item.get('quantity', 0))
                ordering_unit = item.get('ordering_unit', 'EA')
                unit_price = float(item.get('unit_price', 0))
                line_total = float(item.get('line_total', 0))

                if spare_part_id > 0 and quantity > 0:
                    cursor.execute('''
                        INSERT INTO purchase_order_lines (purchase_order_id, spare_part_id,
                                                          quantity, ordering_unit, unit_price, line_total)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (po_id, spare_part_id, quantity, ordering_unit, unit_price, line_total))

            conn.commit()
            conn.close()

            flash(f'Purchase Order {po_number} created successfully.', 'success')
            return redirect(url_for('orders.view_detail', po_id=po_id))

        except Exception as e:
            flash(f'Error creating purchase order: {str(e)}', 'error')
            return render_template('modules/orders/create.html',
                                   vendors=vendors, spare_parts=spare_parts,
                                   po_number=po_number, today=today)

    return render_template('modules/orders/create.html',
                           vendors=vendors, spare_parts=spare_parts,
                           po_number=po_number, today=today,
                           ordering_units=PurchaseOrderLine.ORDERING_UNITS)


@orders_bp.route('/open')
@login_required
def open_list():
    """List all open purchase orders"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT po.*, v.name as vendor_name, u.username as created_by_name
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        LEFT JOIN users u ON po.created_by = u.id
        WHERE po.status NOT IN ('Received', 'Cancelled')
        ORDER BY po.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    purchase_orders = [PurchaseOrder.from_row(row) for row in rows]
    return render_template('modules/orders/open_list.html', purchase_orders=purchase_orders)


@orders_bp.route('/view/<int:po_id>')
@login_required
def view_detail(po_id):
    """View purchase order details"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get PO header
    cursor.execute('''
        SELECT po.*, v.name as vendor_name, v.vendor_id as vendor_code,
               u.username as created_by_name
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        LEFT JOIN users u ON po.created_by = u.id
        WHERE po.id = ?
    ''', (po_id,))
    po_row = cursor.fetchone()

    if po_row is None:
        conn.close()
        flash('Purchase order not found.', 'error')
        return redirect(url_for('orders.open_list'))

    purchase_order = PurchaseOrder.from_row(po_row)
    vendor_code = po_row['vendor_code']

    # Get line items
    cursor.execute('''
        SELECT pol.*, sp.id as spare_part_number, sp.description as spare_part_description,
               sp.vendor_description
        FROM purchase_order_lines pol
        LEFT JOIN spare_parts sp ON pol.spare_part_id = sp.id
        WHERE pol.purchase_order_id = ?
        ORDER BY pol.id
    ''', (po_id,))
    line_rows = cursor.fetchall()
    conn.close()

    line_items = [PurchaseOrderLine.from_row(row) for row in line_rows]

    return render_template('modules/orders/view_detail.html',
                           po=purchase_order, vendor_code=vendor_code,
                           line_items=line_items)


@orders_bp.route('/change/<int:po_id>', methods=['GET', 'POST'])
@login_required
def change(po_id):
    """Edit a purchase order (only if status is Open)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get PO header
    cursor.execute('SELECT * FROM purchase_orders WHERE id = ?', (po_id,))
    po_row = cursor.fetchone()

    if po_row is None:
        conn.close()
        flash('Purchase order not found.', 'error')
        return redirect(url_for('orders.open_list'))

    purchase_order = PurchaseOrder.from_row(po_row)

    if purchase_order.status != 'Open':
        conn.close()
        flash('Only Open purchase orders can be edited.', 'error')
        return redirect(url_for('orders.view_detail', po_id=po_id))

    vendors = get_all_vendors()
    spare_parts = get_all_spare_parts()

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id', '').strip()
        order_date = request.form.get('order_date', '').strip()
        expected_delivery_date = request.form.get('expected_delivery_date', '').strip()
        notes = request.form.get('notes', '').strip()
        line_items_json = request.form.get('line_items', '[]')

        if not vendor_id:
            flash('Please select a vendor.', 'error')
            # Get current line items for re-display
            cursor.execute('''
                SELECT pol.*, sp.id as spare_part_number, sp.description as spare_part_description,
                       sp.vendor_description
                FROM purchase_order_lines pol
                LEFT JOIN spare_parts sp ON pol.spare_part_id = sp.id
                WHERE pol.purchase_order_id = ?
            ''', (po_id,))
            line_rows = cursor.fetchall()
            conn.close()
            line_items = [PurchaseOrderLine.from_row(row) for row in line_rows]
            return render_template('modules/orders/change.html',
                                   po=purchase_order, vendors=vendors,
                                   spare_parts=spare_parts, line_items=line_items,
                                   ordering_units=PurchaseOrderLine.ORDERING_UNITS)

        try:
            line_items = json.loads(line_items_json)
        except:
            line_items = []

        if len(line_items) == 0:
            flash('Please add at least one line item.', 'error')
            cursor.execute('''
                SELECT pol.*, sp.id as spare_part_number, sp.description as spare_part_description,
                       sp.vendor_description
                FROM purchase_order_lines pol
                LEFT JOIN spare_parts sp ON pol.spare_part_id = sp.id
                WHERE pol.purchase_order_id = ?
            ''', (po_id,))
            line_rows = cursor.fetchall()
            conn.close()
            existing_lines = [PurchaseOrderLine.from_row(row) for row in line_rows]
            return render_template('modules/orders/change.html',
                                   po=purchase_order, vendors=vendors,
                                   spare_parts=spare_parts, line_items=existing_lines,
                                   ordering_units=PurchaseOrderLine.ORDERING_UNITS)

        # Calculate total
        total_amount = sum(float(item.get('line_total', 0)) for item in line_items)

        try:
            # Update purchase order header
            cursor.execute('''
                UPDATE purchase_orders
                SET vendor_id = ?, order_date = ?, expected_delivery_date = ?,
                    total_amount = ?, notes = ?
                WHERE id = ?
            ''', (vendor_id, order_date, expected_delivery_date or None,
                  total_amount, notes or None, po_id))

            # Delete existing line items
            cursor.execute('DELETE FROM purchase_order_lines WHERE purchase_order_id = ?', (po_id,))

            # Insert new line items
            for item in line_items:
                spare_part_id = int(item.get('spare_part_id', 0))
                quantity = int(item.get('quantity', 0))
                ordering_unit = item.get('ordering_unit', 'EA')
                unit_price = float(item.get('unit_price', 0))
                line_total = float(item.get('line_total', 0))

                if spare_part_id > 0 and quantity > 0:
                    cursor.execute('''
                        INSERT INTO purchase_order_lines (purchase_order_id, spare_part_id,
                                                          quantity, ordering_unit, unit_price, line_total)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (po_id, spare_part_id, quantity, ordering_unit, unit_price, line_total))

            conn.commit()
            conn.close()

            flash(f'Purchase Order {purchase_order.po_number} updated successfully.', 'success')
            return redirect(url_for('orders.view_detail', po_id=po_id))

        except Exception as e:
            conn.close()
            flash(f'Error updating purchase order: {str(e)}', 'error')
            return redirect(url_for('orders.change', po_id=po_id))

    # GET request - load existing line items
    cursor.execute('''
        SELECT pol.*, sp.id as spare_part_number, sp.description as spare_part_description,
               sp.vendor_description
        FROM purchase_order_lines pol
        LEFT JOIN spare_parts sp ON pol.spare_part_id = sp.id
        WHERE pol.purchase_order_id = ?
    ''', (po_id,))
    line_rows = cursor.fetchall()
    conn.close()

    line_items = [PurchaseOrderLine.from_row(row) for row in line_rows]

    return render_template('modules/orders/change.html',
                           po=purchase_order, vendors=vendors,
                           spare_parts=spare_parts, line_items=line_items,
                           ordering_units=PurchaseOrderLine.ORDERING_UNITS)


@orders_bp.route('/api/spare-part/<int:part_id>')
@login_required
def get_spare_part_info(part_id):
    """API endpoint to get spare part info for auto-fill"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts WHERE id = ?', (part_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': 'Part not found'}), 404

    part = SparePart.from_row(row)
    return jsonify({
        'id': part.id,
        'description': part.description,
        'vendor_description': part.vendor_description or ''
    })


@orders_bp.route('/view/<int:po_id>/receive', methods=['GET', 'POST'])
@login_required
def goods_receipt(po_id):
    """Post goods receipt for a purchase order"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get PO header
    cursor.execute('''
        SELECT po.*, v.name as vendor_name, v.vendor_id as vendor_code
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        WHERE po.id = ?
    ''', (po_id,))
    po_row = cursor.fetchone()

    if po_row is None:
        conn.close()
        flash('Purchase order not found.', 'error')
        return redirect(url_for('orders.open_list'))

    purchase_order = PurchaseOrder.from_row(po_row)

    if purchase_order.status in ['Received', 'Cancelled']:
        conn.close()
        flash('Cannot receive goods for this purchase order.', 'error')
        return redirect(url_for('orders.view_detail', po_id=po_id))

    if request.method == 'POST':
        line_id = request.form.get('line_id', type=int)
        receive_qty = request.form.get('quantity', type=int, default=0)

        if not line_id or receive_qty <= 0:
            flash('Please enter a valid quantity to receive.', 'error')
        else:
            # Get line item details
            cursor.execute('''
                SELECT pol.*, sp.quantity_available
                FROM purchase_order_lines pol
                JOIN spare_parts sp ON pol.spare_part_id = sp.id
                WHERE pol.id = ? AND pol.purchase_order_id = ?
            ''', (line_id, po_id))
            line_row = cursor.fetchone()

            if line_row:
                current_received = line_row['quantity_received'] or 0
                ordered_qty = line_row['quantity']
                remaining = ordered_qty - current_received

                if receive_qty > remaining:
                    flash(f'Cannot receive more than remaining quantity ({remaining}).', 'error')
                else:
                    try:
                        # Update line item quantity_received
                        new_received = current_received + receive_qty
                        cursor.execute('''
                            UPDATE purchase_order_lines
                            SET quantity_received = ?
                            WHERE id = ?
                        ''', (new_received, line_id))

                        # Update spare parts inventory
                        spare_part_id = line_row['spare_part_id']
                        current_stock = line_row['quantity_available'] or 0
                        new_stock = current_stock + receive_qty
                        cursor.execute('''
                            UPDATE spare_parts
                            SET quantity_available = ?
                            WHERE id = ?
                        ''', (new_stock, spare_part_id))

                        # Check if all lines are fully received
                        cursor.execute('''
                            SELECT SUM(quantity) as total_ordered,
                                   SUM(quantity_received) as total_received
                            FROM purchase_order_lines
                            WHERE purchase_order_id = ?
                        ''', (po_id,))
                        totals = cursor.fetchone()
                        total_ordered = totals['total_ordered'] or 0
                        total_received = (totals['total_received'] or 0) + receive_qty

                        # Update PO status
                        if total_received >= total_ordered:
                            new_status = 'Received'
                        elif total_received > 0:
                            new_status = 'Partially Received'
                        else:
                            new_status = purchase_order.status

                        if new_status != purchase_order.status:
                            cursor.execute('''
                                UPDATE purchase_orders SET status = ? WHERE id = ?
                            ''', (new_status, po_id))

                        conn.commit()
                        flash(f'Received {receive_qty} unit(s). Inventory updated.', 'success')

                        if new_status == 'Received':
                            flash('Purchase order fully received.', 'info')
                            conn.close()
                            return redirect(url_for('orders.view_detail', po_id=po_id))

                    except Exception as e:
                        flash(f'Error posting goods receipt: {str(e)}', 'error')
            else:
                flash('Line item not found.', 'error')

    # Get line items with remaining quantities
    cursor.execute('''
        SELECT pol.*, sp.id as spare_part_number, sp.description as spare_part_description,
               sp.vendor_description, sp.quantity_available as current_stock
        FROM purchase_order_lines pol
        LEFT JOIN spare_parts sp ON pol.spare_part_id = sp.id
        WHERE pol.purchase_order_id = ?
        ORDER BY pol.id
    ''', (po_id,))
    line_rows = cursor.fetchall()
    conn.close()

    line_items = []
    for row in line_rows:
        line = PurchaseOrderLine.from_row(row)
        line.current_stock = row['current_stock'] or 0
        line_items.append(line)

    return render_template('modules/orders/goods_receipt.html',
                           po=purchase_order, line_items=line_items)
