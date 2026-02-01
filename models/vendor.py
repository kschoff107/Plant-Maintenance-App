class Vendor:
    STATUSES = ['Active', 'Inactive']

    def __init__(self, id=None, vendor_id=None, name=None, contact_name=None,
                 email=None, phone=None, address=None, status=None, created_at=None):
        self.id = id
        self.vendor_id = vendor_id
        self.name = name
        self.contact_name = contact_name
        self.email = email
        self.phone = phone
        self.address = address
        self.status = status or 'Active'
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create a Vendor object from a database row"""
        if row is None:
            return None
        return Vendor(
            id=row['id'],
            vendor_id=row['vendor_id'],
            name=row['name'],
            contact_name=row['contact_name'] if 'contact_name' in row.keys() else None,
            email=row['email'] if 'email' in row.keys() else None,
            phone=row['phone'] if 'phone' in row.keys() else None,
            address=row['address'] if 'address' in row.keys() else None,
            status=row['status'] if 'status' in row.keys() else 'Active',
            created_at=row['created_at'] if 'created_at' in row.keys() else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'name': self.name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'status': self.status,
            'created_at': self.created_at
        }
