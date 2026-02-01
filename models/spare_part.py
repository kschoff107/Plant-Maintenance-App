class SparePart:
    def __init__(self, id=None, description=None, vendor_description=None,
                 storage_location=None, storage_bin=None, rounding_value=None,
                 maximum_stock=None, quantity_available=None, created_at=None):
        self.id = id
        self.description = description
        self.vendor_description = vendor_description
        self.storage_location = storage_location
        self.storage_bin = storage_bin
        self.rounding_value = rounding_value
        self.maximum_stock = maximum_stock
        self.quantity_available = quantity_available if quantity_available is not None else 0
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create a SparePart object from a database row"""
        if row is None:
            return None
        return SparePart(
            id=row['id'],
            description=row['description'],
            vendor_description=row['vendor_description'],
            storage_location=row['storage_location'],
            storage_bin=row['storage_bin'],
            rounding_value=row['rounding_value'] if 'rounding_value' in row.keys() else None,
            maximum_stock=row['maximum_stock'] if 'maximum_stock' in row.keys() else None,
            quantity_available=row['quantity_available'] if 'quantity_available' in row.keys() else 0,
            created_at=row['created_at']
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'description': self.description,
            'vendor_description': self.vendor_description,
            'storage_location': self.storage_location,
            'storage_bin': self.storage_bin,
            'rounding_value': self.rounding_value,
            'maximum_stock': self.maximum_stock,
            'quantity_available': self.quantity_available,
            'created_at': self.created_at
        }

    def get_stock_status(self):
        """Returns stock status: 'low', 'exceeds', or 'ok'"""
        if self.rounding_value is not None and self.quantity_available < self.rounding_value:
            return 'low'
        elif self.maximum_stock is not None and self.quantity_available > self.maximum_stock:
            return 'exceeds'
        return 'ok'
