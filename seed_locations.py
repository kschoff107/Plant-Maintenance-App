"""Seed script to populate the database with sample locations for a manufacturing plant."""

import sqlite3
import os

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'plant_maintenance.db')

def seed_locations():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Sample locations for a manufacturing plant (hierarchical structure)
    locations = [
        # Buildings
        ('BLDG-MAIN', 'Main Production Building', 'Primary manufacturing facility housing production lines and assembly areas', 'Building', 'Active'),
        ('BLDG-WH', 'Warehouse', 'Storage and logistics facility for raw materials and finished goods', 'Building', 'Active'),
        ('BLDG-OFFICE', 'Office Building', 'Administrative offices and meeting rooms', 'Building', 'Active'),

        # Floors
        ('MAIN-F1', 'Main Building - Floor 1', 'Ground floor with primary production lines', 'Floor', 'Active'),
        ('MAIN-F2', 'Main Building - Floor 2', 'Second floor with assembly and packaging', 'Floor', 'Active'),

        # Production Areas
        ('PROD-A', 'Production Line A', 'High-volume automated production line', 'Area', 'Active'),
        ('PROD-B', 'Production Line B', 'Specialized custom manufacturing line', 'Area', 'Active'),

        # Zones
        ('WH-ZONE1', 'Warehouse - Raw Materials', 'Storage zone for incoming raw materials and components', 'Zone', 'Active'),
        ('WH-ZONE2', 'Warehouse - Finished Goods', 'Storage zone for completed products awaiting shipment', 'Zone', 'Active'),

        # Rooms
        ('MAINT-SHOP', 'Maintenance Shop', 'Equipment repair and maintenance workshop with tools and spare parts', 'Room', 'Active'),
    ]

    inserted = 0
    skipped = 0

    for loc in locations:
        try:
            cursor.execute('''
                INSERT INTO locations (location_code, name, description, location_type, status)
                VALUES (?, ?, ?, ?, ?)
            ''', loc)
            inserted += 1
            print(f'  Added: {loc[0]} - {loc[1]}')
        except sqlite3.IntegrityError:
            skipped += 1
            print(f'  Skipped (already exists): {loc[0]} - {loc[1]}')

    conn.commit()
    conn.close()

    print(f'\nLocation seeding complete!')
    print(f'  Inserted: {inserted}')
    print(f'  Skipped: {skipped}')
    print(f'  Total locations in seed data: {len(locations)}')

if __name__ == '__main__':
    print('Seeding locations for manufacturing plant...\n')
    seed_locations()
