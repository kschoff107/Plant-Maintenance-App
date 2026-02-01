class PurchaseOrder:
    STATUSES = ['Open', 'Sent', 'Partially Received', 'Received', 'Cancelled']

    def __init__(self, id=None, po_number=None, vendor_id=None, order_date=None,
                 expected_delivery_date=None, status=None, total_amount=None,
                 notes=None, created_by=None, created_at=None,
                 vendor_name=None, created_by_name=None):
        self.id = id
        self.po_number = po_number
        self.vendor_id = vendor_id
        self.order_date = order_date
        self.expected_delivery_date = expected_delivery_date
        self.status = status or 'Open'
        self.total_amount = total_amount or 0
        self.notes = notes
        self.created_by = created_by
        self.created_at = created_at
        # Joined fields
        self.vendor_name = vendor_name
        self.created_by_name = created_by_name

    @staticmethod
    def from_row(row):
        """Create a PurchaseOrder object from a database row"""
        if row is None:
            return None
        keys = row.keys()
        return PurchaseOrder(
            id=row['id'],
            po_number=row['po_number'],
            vendor_id=row['vendor_id'],
            order_date=row['order_date'] if 'order_date' in keys else None,
            expected_delivery_date=row['expected_delivery_date'] if 'expected_delivery_date' in keys else None,
            status=row['status'] if 'status' in keys else 'Open',
            total_amount=row['total_amount'] if 'total_amount' in keys else 0,
            notes=row['notes'] if 'notes' in keys else None,
            created_by=row['created_by'] if 'created_by' in keys else None,
            created_at=row['created_at'] if 'created_at' in keys else None,
            vendor_name=row['vendor_name'] if 'vendor_name' in keys else None,
            created_by_name=row['created_by_name'] if 'created_by_name' in keys else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'po_number': self.po_number,
            'vendor_id': self.vendor_id,
            'order_date': self.order_date,
            'expected_delivery_date': self.expected_delivery_date,
            'status': self.status,
            'total_amount': self.total_amount,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'vendor_name': self.vendor_name,
            'created_by_name': self.created_by_name
        }

    def is_open(self):
        """Check if PO can be edited"""
        return self.status == 'Open'

    def is_receivable(self):
        """Check if PO can receive goods"""
        return self.status in ['Sent', 'Partially Received']
