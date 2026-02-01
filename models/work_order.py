class WorkOrder:
    PRIORITIES = ['Emergency', 'High', 'Medium', 'Low']
    STATUSES = ['Open', 'In Progress', 'On Hold', 'Completed', 'Cancelled']

    def __init__(self, id=None, work_order_number=None, title=None, description=None,
                 equipment_id=None, location_code=None, priority=None, status=None,
                 assigned_to=None, created_by=None, due_date=None, completed_at=None,
                 created_at=None):
        self.id = id
        self.work_order_number = work_order_number
        self.title = title
        self.description = description
        self.equipment_id = equipment_id
        self.location_code = location_code
        self.priority = priority or 'Medium'
        self.status = status or 'Open'
        self.assigned_to = assigned_to
        self.created_by = created_by
        self.due_date = due_date
        self.completed_at = completed_at
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        """Create a WorkOrder object from a database row"""
        if row is None:
            return None
        return WorkOrder(
            id=row['id'],
            work_order_number=row['work_order_number'],
            title=row['title'],
            description=row['description'] if 'description' in row.keys() else None,
            equipment_id=row['equipment_id'] if 'equipment_id' in row.keys() else None,
            location_code=row['location_code'] if 'location_code' in row.keys() else None,
            priority=row['priority'] if 'priority' in row.keys() else 'Medium',
            status=row['status'] if 'status' in row.keys() else 'Open',
            assigned_to=row['assigned_to'] if 'assigned_to' in row.keys() else None,
            created_by=row['created_by'] if 'created_by' in row.keys() else None,
            due_date=row['due_date'] if 'due_date' in row.keys() else None,
            completed_at=row['completed_at'] if 'completed_at' in row.keys() else None,
            created_at=row['created_at']
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'work_order_number': self.work_order_number,
            'title': self.title,
            'description': self.description,
            'equipment_id': self.equipment_id,
            'location_code': self.location_code,
            'priority': self.priority,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'created_by': self.created_by,
            'due_date': self.due_date,
            'completed_at': self.completed_at,
            'created_at': self.created_at
        }
