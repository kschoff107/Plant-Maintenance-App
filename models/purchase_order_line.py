class PurchaseOrderLine:
    ORDERING_UNITS = ['EA', 'BOX', 'CASE', 'PACK', 'SET', 'PAIR', 'ROLL', 'GAL', 'LB', 'KG']

    def __init__(self, id=None, purchase_order_id=None, spare_part_id=None,
                 quantity=None, ordering_unit=None, unit_price=None, line_total=None,
                 spare_part_number=None, spare_part_description=None, vendor_description=None):
        self.id = id
        self.purchase_order_id = purchase_order_id
        self.spare_part_id = spare_part_id
        self.quantity = quantity or 0
        self.ordering_unit = ordering_unit or 'EA'
        self.unit_price = unit_price or 0
        self.line_total = line_total or (self.quantity * self.unit_price)
        # Joined fields from spare_parts table
        self.spare_part_number = spare_part_number
        self.spare_part_description = spare_part_description
        self.vendor_description = vendor_description

    @staticmethod
    def from_row(row):
        """Create a PurchaseOrderLine object from a database row"""
        if row is None:
            return None
        keys = row.keys()
        return PurchaseOrderLine(
            id=row['id'],
            purchase_order_id=row['purchase_order_id'],
            spare_part_id=row['spare_part_id'],
            quantity=row['quantity'] if 'quantity' in keys else 0,
            ordering_unit=row['ordering_unit'] if 'ordering_unit' in keys else 'EA',
            unit_price=row['unit_price'] if 'unit_price' in keys else 0,
            line_total=row['line_total'] if 'line_total' in keys else 0,
            spare_part_number=row['spare_part_number'] if 'spare_part_number' in keys else None,
            spare_part_description=row['spare_part_description'] if 'spare_part_description' in keys else None,
            vendor_description=row['vendor_description'] if 'vendor_description' in keys else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'spare_part_id': self.spare_part_id,
            'quantity': self.quantity,
            'ordering_unit': self.ordering_unit,
            'unit_price': self.unit_price,
            'line_total': self.line_total,
            'spare_part_number': self.spare_part_number,
            'spare_part_description': self.spare_part_description,
            'vendor_description': self.vendor_description
        }

    def calculate_total(self):
        """Calculate line total"""
        self.line_total = self.quantity * self.unit_price
        return self.line_total
