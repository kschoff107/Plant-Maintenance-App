from datetime import datetime, timedelta


class MaintenanceSchedule:
    SCHEDULE_TYPES = ['time-based', 'meter-based']
    FREQUENCIES = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Semi-Annual', 'Annual']
    PRIORITIES = ['Emergency', 'High', 'Medium', 'Low']
    STATUSES = ['Active', 'Inactive']

    # Frequency to days mapping
    FREQUENCY_DAYS = {
        'Daily': 1,
        'Weekly': 7,
        'Monthly': 30,
        'Quarterly': 90,
        'Semi-Annual': 182,
        'Annual': 365
    }

    def __init__(self, id=None, schedule_id=None, name=None, description=None, equipment_id=None,
                 schedule_type=None, frequency=None, meter_interval=None, meter_unit=None,
                 last_performed_date=None, last_meter_reading=None, next_due_date=None,
                 next_due_meter=None, priority=None, estimated_duration=None,
                 instructions=None, status=None, created_by=None, created_at=None):
        self.id = id
        self.schedule_id = schedule_id
        self.name = name
        self.description = description
        self.equipment_id = equipment_id
        self.schedule_type = schedule_type or 'time-based'
        self.frequency = frequency
        self.meter_interval = meter_interval
        self.meter_unit = meter_unit
        self.last_performed_date = last_performed_date
        self.last_meter_reading = last_meter_reading
        self.next_due_date = next_due_date
        self.next_due_meter = next_due_meter
        self.priority = priority or 'Medium'
        self.estimated_duration = estimated_duration
        self.instructions = instructions
        self.status = status or 'Active'
        self.created_by = created_by
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create a MaintenanceSchedule object from a database row"""
        if row is None:
            return None
        return MaintenanceSchedule(
            id=row['id'],
            schedule_id=row['schedule_id'] if 'schedule_id' in row.keys() else None,
            name=row['name'],
            description=row['description'] if 'description' in row.keys() else None,
            equipment_id=row['equipment_id'],
            schedule_type=row['schedule_type'],
            frequency=row['frequency'] if 'frequency' in row.keys() else None,
            meter_interval=row['meter_interval'] if 'meter_interval' in row.keys() else None,
            meter_unit=row['meter_unit'] if 'meter_unit' in row.keys() else None,
            last_performed_date=row['last_performed_date'] if 'last_performed_date' in row.keys() else None,
            last_meter_reading=row['last_meter_reading'] if 'last_meter_reading' in row.keys() else None,
            next_due_date=row['next_due_date'] if 'next_due_date' in row.keys() else None,
            next_due_meter=row['next_due_meter'] if 'next_due_meter' in row.keys() else None,
            priority=row['priority'] if 'priority' in row.keys() else 'Medium',
            estimated_duration=row['estimated_duration'] if 'estimated_duration' in row.keys() else None,
            instructions=row['instructions'] if 'instructions' in row.keys() else None,
            status=row['status'] if 'status' in row.keys() else 'Active',
            created_by=row['created_by'] if 'created_by' in row.keys() else None,
            created_at=row['created_at'] if 'created_at' in row.keys() else None
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'name': self.name,
            'description': self.description,
            'equipment_id': self.equipment_id,
            'schedule_type': self.schedule_type,
            'frequency': self.frequency,
            'meter_interval': self.meter_interval,
            'meter_unit': self.meter_unit,
            'last_performed_date': self.last_performed_date,
            'last_meter_reading': self.last_meter_reading,
            'next_due_date': self.next_due_date,
            'next_due_meter': self.next_due_meter,
            'priority': self.priority,
            'estimated_duration': self.estimated_duration,
            'instructions': self.instructions,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at
        }

    @staticmethod
    def calculate_next_due_date(frequency, from_date=None):
        """Calculate the next due date based on frequency"""
        if from_date is None:
            from_date = datetime.now().date()
        elif isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()

        days = MaintenanceSchedule.FREQUENCY_DAYS.get(frequency, 30)
        next_date = from_date + timedelta(days=days)
        return next_date.strftime('%Y-%m-%d')

    @staticmethod
    def calculate_next_due_meter(current_reading, interval):
        """Calculate the next due meter reading"""
        if current_reading is None or interval is None:
            return None
        return current_reading + interval

    def is_time_based(self):
        """Check if this is a time-based schedule"""
        return self.schedule_type == 'time-based'

    def is_meter_based(self):
        """Check if this is a meter-based schedule"""
        return self.schedule_type == 'meter-based'

    def is_overdue(self, current_meter_reading=None):
        """Check if this schedule is overdue"""
        if self.status != 'Active':
            return False

        if self.is_time_based() and self.next_due_date:
            today = datetime.now().date()
            due_date = datetime.strptime(self.next_due_date, '%Y-%m-%d').date()
            return today > due_date

        if self.is_meter_based() and self.next_due_meter and current_meter_reading:
            return current_meter_reading >= self.next_due_meter

        return False

    def is_due_today(self):
        """Check if this schedule is due today (time-based only)"""
        if self.status != 'Active' or not self.is_time_based() or not self.next_due_date:
            return False

        today = datetime.now().strftime('%Y-%m-%d')
        return self.next_due_date == today

    def is_due_soon(self, days=7, current_meter_reading=None):
        """Check if this schedule is due within the specified days"""
        if self.status != 'Active':
            return False

        if self.is_time_based() and self.next_due_date:
            today = datetime.now().date()
            due_date = datetime.strptime(self.next_due_date, '%Y-%m-%d').date()
            return today <= due_date <= today + timedelta(days=days)

        return False
