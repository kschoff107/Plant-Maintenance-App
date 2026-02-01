class Location:
    TYPES = ['Building', 'Floor', 'Room', 'Zone', 'Area', 'Other']
    STATUSES = ['Active', 'Inactive']

    def __init__(self, id=None, location_code=None, name=None, description=None,
                 location_type=None, status=None, created_at=None):
        self.id = id
        self.location_code = location_code
        self.name = name
        self.description = description
        self.location_type = location_type or 'Area'
        self.status = status or 'Active'
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create a Location object from a database row"""
        if row is None:
            return None
        return Location(
            id=row['id'],
            location_code=row['location_code'],
            name=row['name'],
            description=row['description'] if 'description' in row.keys() else None,
            location_type=row['location_type'] if 'location_type' in row.keys() else 'Area',
            status=row['status'] if 'status' in row.keys() else 'Active',
            created_at=row['created_at']
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'location_code': self.location_code,
            'name': self.name,
            'description': self.description,
            'location_type': self.location_type,
            'status': self.status,
            'created_at': self.created_at
        }
