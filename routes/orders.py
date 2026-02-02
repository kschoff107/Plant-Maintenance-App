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
    """List all purchase orders"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT po.*, v.name as vendor_name, u.username as created_by_name
        FROM purchase_orders po
        LEFT JOIN vendors v ON po.vendor_id = v.id
        LEFT JOIN users u ON po.created_by = u.id
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
    """Edit a purchase order"""
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

    if purchase_order.status == 'Cancelled':
        conn.close()
        flash('Cancelled purchase orders cannot be edited.', 'error')
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

    if purchase_order.status == 'Cancelled':
        conn.close()
        flash('Cannot receive goods for cancelled purchase orders.', 'error')
        return redirect(url_for('orders.view_detail', po_id=po_id))

    if request.method == 'POST':
        line_id = request.form.get('line_id', type=int)
        receive_qty = request.form.get('quantity', type=int, default=0)
        final_delivery = 1 if request.form.get('final_delivery') else 0

        if not line_id or (receive_qty <= 0 and final_delivery == 0):
            flash('Please enter a valid quantity to receive or check Final Delivery.', 'error')
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

                try:
                    # Update line item quantity_received and final_delivery
                    new_received = current_received + receive_qty
                    cursor.execute('''
                        UPDATE purchase_order_lines
                        SET quantity_received = ?, final_delivery = ?
                        WHERE id = ?
                    ''', (new_received, final_delivery, line_id))

                    # Log receipt in audit table (with unit_price for MAP calculations)
                    unit_price = line_row['unit_price']
                    cursor.execute('''
                        INSERT INTO gr_receipts (purchase_order_line_id, quantity_received,
                                                 final_delivery, received_by, unit_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (line_id, receive_qty, final_delivery, current_user.id, unit_price))

                    # Update spare parts inventory with MAP calculation
                    spare_part_id = line_row['spare_part_id']
                    current_qty = line_row['quantity_available'] or 0

                    # Retrieve current MAP and inventory value
                    cursor.execute('''
                        SELECT moving_average_price, total_inventory_value
                        FROM spare_parts WHERE id = ?
                    ''', (spare_part_id,))
                    sp_cost_row = cursor.fetchone()
                    current_MAP = sp_cost_row['moving_average_price'] or 0
                    current_inv_value = sp_cost_row['total_inventory_value'] or 0

                    # Calculate new MAP
                    if current_qty == 0:
                        # Initial receipt - direct assignment
                        new_MAP = unit_price
                        new_inv_value = receive_qty * unit_price
                    else:
                        # Standard MAP calculation
                        old_inv_value = current_qty * current_MAP
                        new_receipt_value = receive_qty * unit_price
                        new_qty = current_qty + receive_qty
                        new_MAP = (old_inv_value + new_receipt_value) / new_qty
                        new_inv_value = new_qty * new_MAP

                    # Update spare parts with new values
                    new_stock = current_qty + receive_qty
                    cursor.execute('''
                        UPDATE spare_parts
                        SET quantity_available = ?,
                            moving_average_price = ?,
                            total_inventory_value = ?
                        WHERE id = ?
                    ''', (new_stock, new_MAP, new_inv_value, spare_part_id))

                    # Check if all lines are complete (fully received OR final delivery)
                    cursor.execute('''
                        SELECT COUNT(*) as total_lines,
                               SUM(CASE
                                   WHEN quantity_received >= quantity OR final_delivery = 1
                                   THEN 1 ELSE 0
                               END) as complete_lines
                        FROM purchase_order_lines
                        WHERE purchase_order_id = ?
                    ''', (po_id,))
                    result = cursor.fetchone()
                    total_lines = result['total_lines']
                    complete_lines = result['complete_lines']

                    # Update PO status
                    if complete_lines >= total_lines:
                        new_status = 'Received'
                    elif receive_qty > 0 or final_delivery == 1:
                        new_status = 'Partially Received'
                    else:
                        new_status = purchase_order.status

                    if new_status == 'Received' and purchase_order.status != 'Received':
                        # Track PO closing event
                        cursor.execute('''
                            UPDATE purchase_orders
                            SET status = ?, closed_at = CURRENT_TIMESTAMP, closed_by = ?
                            WHERE id = ?
                        ''', (new_status, current_user.id, po_id))
                    elif new_status != purchase_order.status:
                        cursor.execute('''
                            UPDATE purchase_orders SET status = ? WHERE id = ?
                        ''', (new_status, po_id))

                    conn.commit()

                    if receive_qty > 0:
                        flash(f'Received {receive_qty} unit(s). Inventory updated.', 'success')
                    if final_delivery == 1 and receive_qty == 0:
                        flash('Line marked as final delivery.', 'success')

                    if new_status == 'Received':
                        flash('All items complete. Purchase order closed.', 'info')
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


@orders_bp.route('/view/<int:po_id>/history')
@login_required
def po_history(po_id):
    """Display PO history timeline"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get PO header
    cursor.execute('''
        SELECT po.*, u.username as created_by_name
        FROM purchase_orders po
        LEFT JOIN users u ON po.created_by = u.id
        WHERE po.id = ?
    ''', (po_id,))
    po_row = cursor.fetchone()

    if not po_row:
        conn.close()
        flash('Purchase order not found.', 'error')
        return redirect(url_for('orders.open_list'))

    # Get all events and combine into timeline
    events = []

    # 1. PO Opening event
    events.append({
        'type': 'opening',
        'timestamp': po_row['created_at'],
        'user': po_row['created_by_name'],
        'data': {
            'po_number': po_row['po_number'],
            'status': 'Open'
        }
    })

    # 2. Goods Receipt events
    cursor.execute('''
        SELECT gr.*, pol.spare_part_id, pol.quantity as ordered_qty,
               sp.id as part_number, sp.description as part_description,
               u.username as received_by_name
        FROM gr_receipts gr
        JOIN purchase_order_lines pol ON gr.purchase_order_line_id = pol.id
        JOIN spare_parts sp ON pol.spare_part_id = sp.id
        LEFT JOIN users u ON gr.received_by = u.id
        WHERE pol.purchase_order_id = ?
        ORDER BY gr.received_at
    ''', (po_id,))

    for row in cursor.fetchall():
        events.append({
            'type': 'receipt',
            'timestamp': row['received_at'],
            'user': row['received_by_name'],
            'data': {
                'part_number': row['part_number'],
                'part_description': row['part_description'],
                'quantity': row['quantity_received'],
                'final_delivery': row['final_delivery'] == 1,
                'ordered_qty': row['ordered_qty']
            }
        })

    # 3. GR Reversal events
    cursor.execute('''
        SELECT grr.*, pol.spare_part_id,
               sp.id as part_number, sp.description as part_description,
               u.username as reversed_by_name
        FROM gr_reversals grr
        JOIN purchase_order_lines pol ON grr.purchase_order_line_id = pol.id
        JOIN spare_parts sp ON pol.spare_part_id = sp.id
        LEFT JOIN users u ON grr.reversed_by = u.id
        WHERE pol.purchase_order_id = ?
        ORDER BY grr.reversed_at
    ''', (po_id,))

    for row in cursor.fetchall():
        events.append({
            'type': 'reversal',
            'timestamp': row['reversed_at'],
            'user': row['reversed_by_name'],
            'data': {
                'part_number': row['part_number'],
                'part_description': row['part_description'],
                'quantity': row['quantity_reversed'],
                'reason_code': row['reason_code'],
                'reason_notes': row['reason_notes']
            }
        })

    # 4. PO Closing event
    if po_row['closed_at']:
        cursor.execute('SELECT username FROM users WHERE id = ?', (po_row['closed_by'],))
        closed_by_row = cursor.fetchone()
        events.append({
            'type': 'closing',
            'timestamp': po_row['closed_at'],
            'user': closed_by_row['username'] if closed_by_row else 'System',
            'data': {
                'status': 'Received'
            }
        })

    # Sort all events by timestamp
    events.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '')

    conn.close()
    return render_template('modules/orders/po_history.html',
                          po=po_row,
                          events=events)


@orders_bp.route('/view/<int:po_id>/reverse-receipt', methods=['POST'])
@login_required
def reverse_receipt(po_id):
    """Reverse a goods receipt for a purchase order"""
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

    if purchase_order.status == 'Cancelled':
        conn.close()
        flash('Cannot reverse receipt for cancelled purchase orders.', 'error')
        return redirect(url_for('orders.view_detail', po_id=po_id))

    line_id = request.form.get('line_id', type=int)
    reverse_qty = request.form.get('reverse_quantity', type=int, default=0)
    reason_code = request.form.get('reason_code', '').strip()
    reason_notes = request.form.get('reason_notes', '').strip()

    # Validation: Reason code required
    if not reason_code:
        conn.close()
        flash('Reason code is required for reversals.', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    # Validation: If "Other" selected, notes required
    if reason_code == 'Other' and not reason_notes:
        conn.close()
        flash('Please specify reason for "Other" selection.', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    if not line_id or reverse_qty <= 0:
        flash('Please enter a valid quantity to reverse.', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    # Get line item details
    cursor.execute('''
        SELECT pol.*, sp.quantity_available
        FROM purchase_order_lines pol
        JOIN spare_parts sp ON pol.spare_part_id = sp.id
        WHERE pol.id = ? AND pol.purchase_order_id = ?
    ''', (line_id, po_id))
    line_row = cursor.fetchone()

    if not line_row:
        conn.close()
        flash('Line item not found.', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    current_received = line_row['quantity_received'] or 0
    spare_part_id = line_row['spare_part_id']
    current_stock = line_row['quantity_available'] or 0

    # Validation: Cannot reverse more than received
    if reverse_qty > current_received:
        conn.close()
        flash(f'Cannot reverse more than received quantity ({current_received}).', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    # Validation: Cannot reverse if it would make inventory negative
    if reverse_qty > current_stock:
        conn.close()
        flash(f'Cannot reverse receipt. Insufficient inventory (current stock: {current_stock}).', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    try:
        # Update line item quantity_received
        new_received = current_received - reverse_qty
        # Reset final_delivery if no longer fully received
        new_final_delivery = 0 if new_received < line_row['quantity'] else line_row['final_delivery']

        cursor.execute('''
            UPDATE purchase_order_lines
            SET quantity_received = ?, final_delivery = ?
            WHERE id = ?
        ''', (new_received, new_final_delivery, line_id))

        # Update spare parts inventory with MAP adjustment (reduce)
        # Get unit_price from the purchase_order_line being reversed
        original_unit_price = line_row['unit_price']

        # Get current MAP and inventory value
        cursor.execute('''
            SELECT moving_average_price, total_inventory_value
            FROM spare_parts WHERE id = ?
        ''', (spare_part_id,))
        sp_cost_row = cursor.fetchone()
        current_MAP = sp_cost_row['moving_average_price'] or 0
        current_inv_value = sp_cost_row['total_inventory_value'] or 0

        # Calculate new values after reversal
        new_stock = current_stock - reverse_qty
        removed_value = reverse_qty * original_unit_price
        new_inv_value = current_inv_value - removed_value

        if new_stock == 0:
            new_MAP = 0
            new_inv_value = 0
        else:
            new_MAP = new_inv_value / new_stock if new_stock > 0 else 0

        # Update spare parts inventory with new cost data
        cursor.execute('''
            UPDATE spare_parts
            SET quantity_available = ?,
                moving_average_price = ?,
                total_inventory_value = ?
            WHERE id = ?
        ''', (new_stock, new_MAP, new_inv_value, spare_part_id))

        # Check if all lines are complete (fully received OR final delivery)
        cursor.execute('''
            SELECT COUNT(*) as total_lines,
                   SUM(CASE
                       WHEN quantity_received >= quantity OR final_delivery = 1
                       THEN 1 ELSE 0
                   END) as complete_lines
            FROM purchase_order_lines
            WHERE purchase_order_id = ?
        ''', (po_id,))
        result = cursor.fetchone()
        total_lines = result['total_lines']
        complete_lines = result['complete_lines']

        # Update PO status
        if complete_lines >= total_lines:
            new_status = 'Received'
        elif new_received >= 0:
            new_status = 'Partially Received'
        else:
            new_status = 'Sent'

        if new_status != purchase_order.status:
            cursor.execute('''
                UPDATE purchase_orders SET status = ? WHERE id = ?
            ''', (new_status, po_id))

        # Log reversal in audit table
        cursor.execute('''
            INSERT INTO gr_reversals (purchase_order_line_id, quantity_reversed,
                                      reason_code, reason_notes, reversed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (line_id, reverse_qty, reason_code, reason_notes or None, current_user.id))

        conn.commit()
        flash(f'Reversed {reverse_qty} unit(s). Inventory reduced.', 'success')

    except Exception as e:
        conn.close()
        flash(f'Error reversing goods receipt: {str(e)}', 'error')
        return redirect(url_for('orders.goods_receipt', po_id=po_id))

    conn.close()
    return redirect(url_for('orders.goods_receipt', po_id=po_id))
