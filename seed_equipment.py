from database.init_db import get_connection

equipment_data = [
    # Pumps
    ('PMP-001', 'Cooling Water Pump 1', 'Grundfos', 'CR 15-3', 'SN-GF-2019-001', 'Utility Building - Room 101', '2019-03-15', 'Active'),
    ('PMP-002', 'Cooling Water Pump 2', 'Grundfos', 'CR 15-3', 'SN-GF-2019-002', 'Utility Building - Room 101', '2019-03-15', 'Active'),
    ('PMP-003', 'Feed Water Pump', 'Goulds', '3196 MTX', 'SN-GL-2018-055', 'Boiler House', '2018-06-20', 'Active'),
    ('PMP-004', 'Sump Pump A', 'Flygt', 'NP 3127', 'SN-FG-2020-012', 'Basement Level 1', '2020-01-10', 'Active'),
    ('PMP-005', 'Sump Pump B', 'Flygt', 'NP 3127', 'SN-FG-2020-013', 'Basement Level 2', '2020-01-10', 'Under Repair'),

    # Motors
    ('MTR-001', 'Conveyor Drive Motor 1', 'Baldor', 'EM3774T', 'SN-BD-2017-101', 'Production Hall A', '2017-08-05', 'Active'),
    ('MTR-002', 'Conveyor Drive Motor 2', 'Baldor', 'EM3774T', 'SN-BD-2017-102', 'Production Hall A', '2017-08-05', 'Active'),
    ('MTR-003', 'Mixer Motor', 'WEG', 'W22 15HP', 'SN-WG-2021-033', 'Mixing Room', '2021-04-12', 'Active'),
    ('MTR-004', 'Exhaust Fan Motor', 'ABB', 'M3BP 160', 'SN-AB-2016-089', 'Roof Level', '2016-11-30', 'Inactive'),
    ('MTR-005', 'Compressor Motor', 'Siemens', '1LE1', 'SN-SM-2019-077', 'Compressor Room', '2019-09-25', 'Active'),

    # Compressors
    ('CMP-001', 'Air Compressor 1', 'Atlas Copco', 'GA 37', 'SN-AC-2018-001', 'Compressor Room', '2018-02-14', 'Active'),
    ('CMP-002', 'Air Compressor 2', 'Ingersoll Rand', 'R55i', 'SN-IR-2020-045', 'Compressor Room', '2020-07-22', 'Active'),
    ('CMP-003', 'Refrigeration Compressor', 'Bitzer', '4FES-5Y', 'SN-BZ-2019-018', 'Cold Storage', '2019-05-08', 'Active'),

    # Conveyors
    ('CNV-001', 'Main Production Conveyor', 'Dorner', '3200 Series', 'SN-DN-2017-201', 'Production Hall A', '2017-03-20', 'Active'),
    ('CNV-002', 'Packaging Line Conveyor', 'Hytrol', 'ProSort 400', 'SN-HT-2018-156', 'Packaging Area', '2018-10-05', 'Active'),
    ('CNV-003', 'Incline Conveyor', 'FlexLink', 'X85', 'SN-FL-2021-088', 'Warehouse Entry', '2021-01-15', 'Active'),
    ('CNV-004', 'Scrap Conveyor', 'Mayfran', 'ChipVeyor', 'SN-MF-2015-044', 'Machine Shop', '2015-06-30', 'Decommissioned'),

    # HVAC
    ('AHU-001', 'Air Handling Unit 1', 'Trane', 'M Series', 'SN-TR-2019-301', 'Mechanical Room 1', '2019-11-12', 'Active'),
    ('AHU-002', 'Air Handling Unit 2', 'Carrier', '39M', 'SN-CR-2019-302', 'Mechanical Room 2', '2019-11-12', 'Active'),
    ('CHR-001', 'Chiller Unit', 'York', 'YLAA', 'SN-YK-2018-501', 'Roof Level', '2018-04-25', 'Active'),

    # Electrical
    ('TRF-001', 'Main Transformer', 'ABB', 'Distribution', 'SN-AB-2010-001', 'Substation', '2010-01-20', 'Active'),
    ('MCC-001', 'Motor Control Center 1', 'Eaton', 'Freedom 2100', 'SN-ET-2017-601', 'Electrical Room A', '2017-05-15', 'Active'),
    ('MCC-002', 'Motor Control Center 2', 'Allen-Bradley', 'Centerline 2100', 'SN-AB-2017-602', 'Electrical Room B', '2017-05-15', 'Active'),
    ('UPS-001', 'UPS System', 'APC', 'Symmetra PX', 'SN-AP-2020-701', 'Server Room', '2020-03-10', 'Active'),
    ('GEN-001', 'Backup Generator', 'Caterpillar', 'C15', 'SN-CT-2018-801', 'Generator Building', '2018-08-30', 'Active'),

    # Tanks
    ('TNK-001', 'Raw Water Tank', 'Highland Tank', 'Horizontal', 'SN-HT-2012-101', 'Tank Farm', '2012-05-20', 'Active'),
    ('TNK-002', 'Chemical Storage Tank A', 'Poly Processing', 'XLPE', 'SN-PP-2019-102', 'Chemical Storage', '2019-02-28', 'Active'),
    ('TNK-003', 'Chemical Storage Tank B', 'Poly Processing', 'XLPE', 'SN-PP-2019-103', 'Chemical Storage', '2019-02-28', 'Active'),
    ('TNK-004', 'Fuel Tank', 'Highland Tank', 'UL-142', 'SN-HT-2018-104', 'Generator Building', '2018-08-30', 'Active'),

    # Miscellaneous
    ('CRN-001', 'Overhead Crane 5-Ton', 'Konecranes', 'CXT', 'SN-KC-2016-901', 'Machine Shop', '2016-09-15', 'Active'),
    ('FLT-001', 'Dust Collector', 'Donaldson', 'Torit DFO', 'SN-DD-2018-951', 'Woodworking Area', '2018-12-01', 'Active'),
    ('MXR-001', 'Industrial Mixer', 'Chemineer', 'HT', 'SN-CH-2020-961', 'Mixing Room', '2020-06-18', 'Active'),
    ('WLD-001', 'Welding Station 1', 'Lincoln', 'Power Wave', 'SN-LN-2019-971', 'Fabrication Shop', '2019-07-22', 'Active'),
    ('WLD-002', 'Welding Station 2', 'Miller', 'Dynasty 400', 'SN-ML-2019-972', 'Fabrication Shop', '2019-07-22', 'Under Repair'),
    ('CNC-001', 'CNC Lathe', 'Haas', 'ST-30', 'SN-HS-2021-981', 'Machine Shop', '2021-02-10', 'Active'),
    ('CNC-002', 'CNC Mill', 'Haas', 'VF-4', 'SN-HS-2021-982', 'Machine Shop', '2021-02-10', 'Active'),
    ('PRS-001', 'Hydraulic Press', 'Dake', '75H', 'SN-DK-2014-991', 'Fabrication Shop', '2014-04-05', 'Active'),
    ('SAW-001', 'Band Saw', 'DoAll', 'C-916A', 'SN-DA-2017-995', 'Machine Shop', '2017-10-20', 'Active'),
    ('DRL-001', 'Drill Press', 'Clausing', '2286', 'SN-CL-2015-998', 'Machine Shop', '2015-08-12', 'Inactive'),
]

if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany('''
        INSERT INTO equipment (tag_number, description, manufacturer, model_number,
                              serial_number, location, installation_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', equipment_data)

    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM equipment')
    count = cursor.fetchone()[0]
    print(f'Added {len(equipment_data)} equipment items. Total in database: {count}')

    # Count by status
    cursor.execute('SELECT status, COUNT(*) FROM equipment GROUP BY status')
    for row in cursor.fetchall():
        print(f'  - {row[0]}: {row[1]}')

    conn.close()
