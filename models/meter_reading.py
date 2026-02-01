class MeterReading:
    COMMON_UNITS = ['hours', 'miles', 'kilometers', 'cycles', 'units', 'gallons', 'liters']

    def __init__(self, id=None, equipment_id=None, reading_value=None, reading_unit=None,
                 recorded_by=None, recorded_at=None, notes=None):
        self.id = id
        self.equipment_id = equipment_id
        self.reading_value = reading_value
        self.reading_unit = reading_unit
        self.recorded_by = recorded_by
        self.recorded_at = recorded_at
        self.notes = notes

    @staticmethod
    def from_row(row):
        """Create a MeterReading object from a database row"""
        if row is None:
            return None
        return MeterReading(
            id=row['id'],
            equipment_id=row['equipment_id'],
            reading_value=row['reading_value'],
            reading_unit=row['reading_unit'] if 'reading_unit' in row.keys() else None,
            recorded_by=row['recorded_by'] if 'recorded_by' in row.keys() else None,
            recorded_at=row['recorded_at'] if 'recorded_at' in row.keys() else None,
            notes=row['notes'] if 'notes' in row.keys() else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'equipment_id': self.equipment_id,
            'reading_value': self.reading_value,
            'reading_unit': self.reading_unit,
            'recorded_by': self.recorded_by,
            'recorded_at': self.recorded_at,
            'notes': self.notes
        }
