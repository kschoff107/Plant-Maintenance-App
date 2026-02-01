from database.init_db import get_connection

# Sample spare parts data for plant maintenance
spare_parts = [
    # Bearings
    ("Ball Bearing 6205", "SKF 6205-2RS Deep Groove Ball Bearing", "Warehouse A", "A-01-01"),
    ("Ball Bearing 6206", "SKF 6206-2RS Deep Groove Ball Bearing", "Warehouse A", "A-01-02"),
    ("Ball Bearing 6207", "SKF 6207-2RS Deep Groove Ball Bearing", "Warehouse A", "A-01-03"),
    ("Roller Bearing 22210", "FAG 22210E1 Spherical Roller Bearing", "Warehouse A", "A-01-04"),
    ("Thrust Bearing 51105", "NSK 51105 Thrust Ball Bearing", "Warehouse A", "A-01-05"),

    # Belts
    ("V-Belt A68", "Gates A68 Classic V-Belt", "Warehouse A", "A-02-01"),
    ("V-Belt B75", "Gates B75 Classic V-Belt", "Warehouse A", "A-02-02"),
    ("Timing Belt HTD 5M", "Continental HTD 5M-450 Timing Belt", "Warehouse A", "A-02-03"),
    ("Serpentine Belt K060923", "Dayco K060923 Serpentine Belt", "Warehouse A", "A-02-04"),
    ("Flat Belt 3 Ply", "Habasit 3-Ply Flat Conveyor Belt 6in", "Warehouse A", "A-02-05"),

    # Filters
    ("Oil Filter LF3000", "Fleetguard LF3000 Oil Filter", "Warehouse B", "B-01-01"),
    ("Air Filter AF25550", "Fleetguard AF25550 Air Filter", "Warehouse B", "B-01-02"),
    ("Hydraulic Filter HF6177", "Fleetguard HF6177 Hydraulic Filter", "Warehouse B", "B-01-03"),
    ("Fuel Filter FF5052", "Fleetguard FF5052 Fuel Filter", "Warehouse B", "B-01-04"),
    ("Coolant Filter WF2076", "Fleetguard WF2076 Coolant Filter", "Warehouse B", "B-01-05"),

    # Seals and Gaskets
    ("O-Ring Kit Metric", "Parker Metric O-Ring Kit 382pc", "Warehouse B", "B-02-01"),
    ("Shaft Seal 35x52x7", "SKF 35x52x7 HMS5 RG Shaft Seal", "Warehouse B", "B-02-02"),
    ("Gasket Set Pump", "Grundfos Pump Gasket Set CR Series", "Warehouse B", "B-02-03"),
    ("Mechanical Seal 25mm", "John Crane Type 21 Mechanical Seal 25mm", "Warehouse B", "B-02-04"),
    ("Flange Gasket 4in", "Garlock 3000 4in 150# Flange Gasket", "Warehouse B", "B-02-05"),

    # Motors and Drives
    ("Motor 5HP 3Phase", "Baldor EM3615T 5HP 3-Phase Motor", "Warehouse C", "C-01-01"),
    ("Motor 10HP 3Phase", "Baldor EM3774T 10HP 3-Phase Motor", "Warehouse C", "C-01-02"),
    ("Motor 2HP Single Phase", "Leeson 110087 2HP Single Phase Motor", "Warehouse C", "C-01-03"),
    ("VFD 10HP", "ABB ACS310-03U-25A4-4 10HP VFD", "Warehouse C", "C-01-04"),
    ("Soft Starter 25HP", "Siemens 3RW3026 Soft Starter 25HP", "Warehouse C", "C-01-05"),

    # Pumps and Parts
    ("Centrifugal Pump Impeller", "Goulds 3196 Impeller 6in", "Warehouse C", "C-02-01"),
    ("Pump Coupling Insert", "Lovejoy L-150 Coupling Insert", "Warehouse C", "C-02-02"),
    ("Diaphragm Pump Kit", "Wilden 04-9805-20 Diaphragm Kit", "Warehouse C", "C-02-03"),
    ("Pump Wear Ring", "Goulds 3196 Wear Ring Set", "Warehouse C", "C-02-04"),
    ("Submersible Pump 2HP", "Grundfos SE1.50.65.30 Submersible Pump", "Warehouse C", "C-02-05"),

    # Valves
    ("Ball Valve 2in SS", "Swagelok SS-63TS12 2in Ball Valve", "Warehouse D", "D-01-01"),
    ("Gate Valve 4in", "Powell 1503 4in 150# Gate Valve", "Warehouse D", "D-01-02"),
    ("Check Valve 3in", "Crane 37 3in 150# Check Valve", "Warehouse D", "D-01-03"),
    ("Globe Valve 2in", "Crane 1 2in 300# Globe Valve", "Warehouse D", "D-01-04"),
    ("Butterfly Valve 6in", "Keystone AR2 6in Butterfly Valve", "Warehouse D", "D-01-05"),
    ("Solenoid Valve 1/2in", "ASCO 8210G094 1/2in Solenoid Valve", "Warehouse D", "D-01-06"),
    ("Relief Valve 1in", "Kunkle 6010HGM01 1in Relief Valve", "Warehouse D", "D-01-07"),
    ("Control Valve 3in", "Fisher ED 3in Control Valve", "Warehouse D", "D-01-08"),

    # Electrical Components
    ("Contactor 40A", "Eaton XTCE040D00A 40A Contactor", "Warehouse E", "E-01-01"),
    ("Overload Relay 25-32A", "Eaton XTOB032CC1 Overload Relay", "Warehouse E", "E-01-02"),
    ("Circuit Breaker 30A", "Square D QO330 3-Pole 30A Breaker", "Warehouse E", "E-01-03"),
    ("Fuse 30A Class RK5", "Bussmann FRS-R-30 30A Fuse", "Warehouse E", "E-01-04"),
    ("Terminal Block 10AWG", "Phoenix Contact UK 6 N Terminal Block", "Warehouse E", "E-01-05"),
    ("Push Button Green", "Allen-Bradley 800T-A1A Push Button", "Warehouse E", "E-01-06"),
    ("Pilot Light Red", "Allen-Bradley 800T-P16R Pilot Light", "Warehouse E", "E-01-07"),
    ("Selector Switch 3-Pos", "Allen-Bradley 800T-H33A Selector Switch", "Warehouse E", "E-01-08"),
    ("E-Stop Button", "Allen-Bradley 800T-FX6D4 E-Stop", "Warehouse E", "E-01-09"),
    ("Power Supply 24VDC", "Phoenix Contact QUINT-PS/1AC/24DC/10", "Warehouse E", "E-01-10"),

    # Sensors and Instrumentation
    ("Proximity Sensor 10mm", "Turck BI10-M30-AP6X Proximity Sensor", "Warehouse E", "E-02-01"),
    ("Photoelectric Sensor", "Banner QS18VP6LP Photoelectric", "Warehouse E", "E-02-02"),
    ("Pressure Transmitter", "Rosemount 3051TG Pressure Transmitter", "Warehouse E", "E-02-03"),
    ("Temperature Transmitter", "Rosemount 644 Temperature Transmitter", "Warehouse E", "E-02-04"),
    ("Level Switch Float", "Gems LS-700 Float Level Switch", "Warehouse E", "E-02-05"),
    ("Flow Meter 2in Mag", "Endress+Hauser Promag 10L 2in", "Warehouse E", "E-02-06"),
    ("Thermocouple Type K", "Omega KQSS-14G-12 Type K Thermocouple", "Warehouse E", "E-02-07"),
    ("RTD Sensor PT100", "Omega PR-13-2-100-1/4-6-E RTD", "Warehouse E", "E-02-08"),

    # Pneumatic Components
    ("Air Cylinder 2in Bore", "SMC NCGBA20-0400 Air Cylinder", "Warehouse F", "F-01-01"),
    ("Air Regulator 1/2in", "SMC AR40-N04-Z Air Regulator", "Warehouse F", "F-01-02"),
    ("Air Filter 1/2in", "SMC AF40-N04-Z Air Filter", "Warehouse F", "F-01-03"),
    ("Solenoid Valve 5/2", "SMC SY5120-5LZ-01 5/2 Solenoid Valve", "Warehouse F", "F-01-04"),
    ("Quick Connect 1/4in", "SMC KQ2H06-02AS Quick Connect", "Warehouse F", "F-01-05"),
    ("Air Hose 3/8in x 50ft", "Goodyear 3/8in x 50ft Air Hose", "Warehouse F", "F-01-06"),
    ("Muffler 1/4in", "SMC AN200-02 Muffler", "Warehouse F", "F-01-07"),

    # Hydraulic Components
    ("Hydraulic Hose 1/2in", "Parker 421-8 1/2in Hydraulic Hose 10ft", "Warehouse F", "F-02-01"),
    ("Hydraulic Fitting 1/2in", "Parker 10143-8-8 Hydraulic Fitting", "Warehouse F", "F-02-02"),
    ("Hydraulic Pump Gear", "Prince SP20A27A9H2-R Gear Pump", "Warehouse F", "F-02-03"),
    ("Hydraulic Cylinder 4in", "Parker 2H Series 4in Bore Cylinder", "Warehouse F", "F-02-04"),
    ("Directional Valve 4/3", "Parker D1VW020BNKW Directional Valve", "Warehouse F", "F-02-05"),

    # Fasteners
    ("Hex Bolt 1/2-13 x 2in", "Grade 8 Hex Bolt 1/2-13 x 2in Zinc", "Warehouse G", "G-01-01"),
    ("Hex Nut 1/2-13", "Grade 8 Hex Nut 1/2-13 Zinc", "Warehouse G", "G-01-02"),
    ("Flat Washer 1/2in", "SAE Flat Washer 1/2in Zinc", "Warehouse G", "G-01-03"),
    ("Lock Washer 1/2in", "Split Lock Washer 1/2in Zinc", "Warehouse G", "G-01-04"),
    ("Socket Head Cap Screw", "SHCS 3/8-16 x 1in Alloy", "Warehouse G", "G-01-05"),
    ("Set Screw 1/4-20 x 3/8", "Cup Point Set Screw 1/4-20 x 3/8", "Warehouse G", "G-01-06"),
    ("Anchor Bolt 5/8 x 6in", "Hilti KB-TZ 5/8 x 6in Anchor", "Warehouse G", "G-01-07"),
    ("U-Bolt 2in Pipe", "U-Bolt for 2in Pipe Zinc", "Warehouse G", "G-01-08"),

    # Lubrication
    ("Grease Cartridge EP2", "Mobil Mobilux EP 2 Grease 14oz", "Warehouse G", "G-02-01"),
    ("Motor Oil 10W-40", "Mobil 1 10W-40 Motor Oil 1qt", "Warehouse G", "G-02-02"),
    ("Hydraulic Oil AW46", "Mobil DTE 25 Hydraulic Oil 5gal", "Warehouse G", "G-02-03"),
    ("Gear Oil 90W", "Mobil SHC 630 Gear Oil 1gal", "Warehouse G", "G-02-04"),
    ("Penetrating Oil", "Kroil Penetrating Oil 13oz", "Warehouse G", "G-02-05"),
    ("Chain Lubricant", "CRC Food Grade Chain Lube 12oz", "Warehouse G", "G-02-06"),

    # Safety Equipment
    ("Safety Glasses Clear", "3M SecureFit 400 Clear Safety Glasses", "Warehouse H", "H-01-01"),
    ("Hearing Protection", "3M Peltor X4A Earmuffs", "Warehouse H", "H-01-02"),
    ("Nitrile Gloves Large", "Ansell HyFlex 11-801 Gloves Large", "Warehouse H", "H-01-03"),
    ("Hard Hat White", "MSA V-Gard White Hard Hat", "Warehouse H", "H-01-04"),
    ("Face Shield", "Honeywell Uvex Bionic Face Shield", "Warehouse H", "H-01-05"),

    # Miscellaneous
    ("Cable Tie 8in Black", "Panduit PLT2S-M0 Cable Tie 8in", "Warehouse H", "H-02-01"),
    ("Electrical Tape Black", "3M Super 33+ Electrical Tape", "Warehouse H", "H-02-02"),
    ("Teflon Tape 1/2in", "Oatey 1/2in PTFE Tape", "Warehouse H", "H-02-03"),
    ("Pipe Thread Sealant", "Loctite 565 PST Pipe Sealant", "Warehouse H", "H-02-04"),
    ("Silicone Sealant", "Permatex Ultra Grey RTV Silicone", "Warehouse H", "H-02-05"),
    ("Coupling Spider", "Lovejoy L-100 Spider NBR", "Warehouse A", "A-03-01"),
    ("Sprocket 40B18", "Martin 40B18 Sprocket", "Warehouse A", "A-03-02"),
    ("Roller Chain 40 10ft", "Tsubaki RS40 Roller Chain 10ft", "Warehouse A", "A-03-03"),
    ("Sheave 2-Groove 6in", "Browning 2TB60 V-Belt Sheave", "Warehouse A", "A-03-04"),
    ("Bushing Taper Lock", "Browning Q1 1-1/8 Taper Lock Bushing", "Warehouse A", "A-03-05"),
]

if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()

    # Insert all spare parts
    cursor.executemany('''
        INSERT INTO spare_parts (description, vendor_description, storage_location, storage_bin)
        VALUES (?, ?, ?, ?)
    ''', spare_parts)

    conn.commit()
    print(f"Successfully inserted {len(spare_parts)} spare parts!")

    # Verify count
    cursor.execute('SELECT COUNT(*) FROM spare_parts')
    count = cursor.fetchone()[0]
    print(f"Total spare parts in database: {count}")

    conn.close()
