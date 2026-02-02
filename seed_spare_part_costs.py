"""
Seed script to populate moving average prices and inventory values for spare parts.
This generates realistic test data for demonstration purposes.
"""

import sqlite3
import random
from database.init_db import get_db_path

def seed_spare_part_costs():
    """Populate MAP and inventory values for all spare parts"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all spare parts
    cursor.execute('SELECT id, description, quantity_available FROM spare_parts')
    parts = cursor.fetchall()

    if not parts:
        print('No spare parts found in database.')
        conn.close()
        return

    print(f'Found {len(parts)} spare parts. Generating cost data...\n')

    updated_count = 0
    for part in parts:
        part_id = part['id']
        description = part['description']
        qty = part['quantity_available'] or 0

        # Generate realistic MAP based on part type
        # Use description hash to make it deterministic but varied
        random.seed(hash(description) % 10000)

        # Different price ranges based on keywords in description
        desc_lower = description.lower()

        if any(word in desc_lower for word in ['bearing', 'motor', 'pump', 'valve']):
            # High-value mechanical parts: $50-$500
            map_price = round(random.uniform(50, 500), 2)
        elif any(word in desc_lower for word in ['seal', 'gasket', 'o-ring', 'washer']):
            # Low-value consumables: $2-$25
            map_price = round(random.uniform(2, 25), 2)
        elif any(word in desc_lower for word in ['filter', 'element', 'cartridge']):
            # Medium-value filters: $15-$75
            map_price = round(random.uniform(15, 75), 2)
        elif any(word in desc_lower for word in ['belt', 'hose', 'cable', 'wire']):
            # Medium-low value parts: $8-$50
            map_price = round(random.uniform(8, 50), 2)
        elif any(word in desc_lower for word in ['sensor', 'switch', 'relay']):
            # Electronics: $20-$150
            map_price = round(random.uniform(20, 150), 2)
        elif any(word in desc_lower for word in ['bolt', 'nut', 'screw', 'fastener']):
            # Very low value fasteners: $0.50-$5
            map_price = round(random.uniform(0.50, 5), 2)
        else:
            # Default range: $10-$100
            map_price = round(random.uniform(10, 100), 2)

        # Calculate total inventory value
        total_value = round(qty * map_price, 2)

        # Update the spare part
        cursor.execute('''
            UPDATE spare_parts
            SET moving_average_price = ?,
                total_inventory_value = ?
            WHERE id = ?
        ''', (map_price, total_value, part_id))

        print(f'Part #{part_id}: {description[:50]}')
        print(f'  Qty: {qty}, MAP: ${map_price:.2f}, Total Value: ${total_value:.2f}')
        updated_count += 1

    conn.commit()
    conn.close()

    print(f'\n✓ Successfully updated {updated_count} spare parts with cost data!')
    print('\nYou can now view the inventory report to see the moving average prices.')

if __name__ == '__main__':
    print('='*70)
    print('SPARE PARTS COST DATA SEEDING')
    print('='*70)
    print('\nThis script will populate moving average prices for all spare parts')
    print('based on realistic price ranges for different part types.\n')

    response = input('Continue? (y/n): ')
    if response.lower() == 'y':
        seed_spare_part_costs()
    else:
        print('Operation cancelled.')
