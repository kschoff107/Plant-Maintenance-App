class Equipment:
    STATUSES = ['Active', 'Inactive', 'Under Repair', 'Decommissioned']

    def __init__(self, id=None, tag_number=None, description=None, manufacturer=None,
                 model_number=None, serial_number=None, location=None,
                 installation_date=None, status=None, created_at=None):
        self.id = id
        self.tag_number = tag_number
        self.description = description
        self.manufacturer = manufacturer
        self.model_number = model_number
        self.serial_number = serial_number
        self.location = location
        self.installation_date = installation_date
        self.status = status or 'Active'
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create an Equipment object from a database row"""
        if row is None:
            return None
        return Equipment(
            id=row['id'],
            tag_number=row['tag_number'],
            description=row['description'],
            manufacturer=row['manufacturer'] if 'manufacturer' in row.keys() else None,
            model_number=row['model_number'] if 'model_number' in row.keys() else None,
            serial_number=row['serial_number'] if 'serial_number' in row.keys() else None,
            location=row['location'] if 'location' in row.keys() else None,
            installation_date=row['installation_date'] if 'installation_date' in row.keys() else None,
            status=row['status'] if 'status' in row.keys() else 'Active',
            created_at=row['created_at']
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'tag_number': self.tag_number,
            'description': self.description,
            'manufacturer': self.manufacturer,
            'model_number': self.model_number,
            'serial_number': self.serial_number,
            'location': self.location,
            'installation_date': self.installation_date,
            'status': self.status,
            'created_at': self.created_at
        }
