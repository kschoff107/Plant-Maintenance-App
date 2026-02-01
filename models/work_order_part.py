class WorkOrderPart:
    TRANSACTION_TYPES = ['issue', 'return']

    def __init__(self, id=None, work_order_id=None, spare_part_id=None, quantity=None,
                 transaction_type=None, transacted_by=None, transacted_at=None, notes=None):
        self.id = id
        self.work_order_id = work_order_id
        self.spare_part_id = spare_part_id
        self.quantity = quantity
        self.transaction_type = transaction_type
        self.transacted_by = transacted_by
        self.transacted_at = transacted_at
        self.notes = notes

    @staticmethod
    def from_row(row):
        """Create a WorkOrderPart object from a database row"""
        if row is None:
            return None
        return WorkOrderPart(
            id=row['id'],
            work_order_id=row['work_order_id'],
            spare_part_id=row['spare_part_id'],
            quantity=row['quantity'],
            transaction_type=row['transaction_type'],
            transacted_by=row['transacted_by'] if 'transacted_by' in row.keys() else None,
            transacted_at=row['transacted_at'] if 'transacted_at' in row.keys() else None,
            notes=row['notes'] if 'notes' in row.keys() else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'work_order_id': self.work_order_id,
            'spare_part_id': self.spare_part_id,
            'quantity': self.quantity,
            'transaction_type': self.transaction_type,
            'transacted_by': self.transacted_by,
            'transacted_at': self.transacted_at,
            'notes': self.notes
        }
