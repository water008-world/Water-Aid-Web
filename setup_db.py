import sqlite3
import os

def setup_database():
    try:
        print("Connecting to `water_aid.db` (SQLite)...")
        conn = sqlite3.connect("water_aid.db")
        cursor = conn.cursor()
        
        print("Creating `devices` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                accountNo TEXT,
                owner TEXT,
                location TEXT,
                prevDate TEXT DEFAULT '-',
                prevReading REAL DEFAULT 0.0,
                currentReading REAL DEFAULT 0.0,
                currentDate TEXT DEFAULT '-',
                consumption REAL DEFAULT 0.0,
                status TEXT DEFAULT 'offline',
                phone TEXT DEFAULT '',
                diu TEXT DEFAULT 'ALL DIU',
                meterNo TEXT DEFAULT '',
                meterBrand TEXT DEFAULT 'BAYLAN',
                meterDiameter TEXT DEFAULT '1.5 mm',
                houseType TEXT DEFAULT 'Building',
                consumerType TEXT DEFAULT 'None',
                waterPrice TEXT DEFAULT '8.00',
                installDate TEXT DEFAULT 'N/A',
                amrDate TEXT DEFAULT 'N/A',
                flagged INTEGER DEFAULT 0,
                usage_val REAL DEFAULT 0.0,
                flow REAL DEFAULT 0.0
            )
        """)
        
        print("Creating `telemetry` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                battery INTEGER,
                network_signal INTEGER,
                water_rate REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
        """)

        print("Creating `admins` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check if devices are empty to seed
        cursor.execute("SELECT COUNT(*) FROM devices")
        if cursor.fetchone()[0] == 0:
            print("Seeding initial data into devices table...")
            seed_data = [
                ("2000120320260001", "19485038", "Shekh Shihab Ahamed", "HEAD QUATER,, CHAIRMAN BARI,BANANI,DHAKA.,", "2026-03-31 23:59:42", 29969.20, 30009.00, "2026-04-02 23:59:44", 39.80, "online", "01914725546", "ALL DIU", "18095012", "BAYLAN"),
                ("2000120320260002", "20485930", "Md Akbor Uddin", "PLOT-7-9, HOTEL SONARGAON RD,, KAWRANBAZAR, TEJGAON, DHAKA.,", "-", 0.00, 0.00, "-", 0.00, "offline", "", "ALL DIU", "", "BAYLAN"),
                ("2000120320260003", "39485721", "Saydullah Al Alamin", "18/1, TEJGAON I/A., DHAKA-1215,", "2026-03-31 23:59:44", 586519.36, 609275.45, "2026-04-07 23:24:11", 22756.09, "online", "", "ALL DIU", "", "BAYLAN"),
                ("2000120320260004", "49385729", "Rashed Kayser", "HOUSE-149, WEST ARJATPARA,, MOHAKHALI, DHAKA.,", "2026-03-31 23:58:56", 40303.00, 40397.00, "2026-04-06 16:00:42", 94.00, "online", "", "ALL DIU", "", "BAYLAN"),
                ("2000120320260005", "58394021", "Md Borhan Patowari", "SHANTA HOLDINGS LIMITED ,, PLOT NO.-190, TEJGAON INDUSTRIAL AREA, DHAKA", "2026-03-03 06:08:54", 31095.95, 31174.44, "2026-04-07 23:17:36", 78.49, "online", "", "ALL DIU", "", "BAYLAN")
            ]
            
            insert_query = """
            INSERT INTO devices (id, accountNo, owner, location, prevDate, prevReading, currentReading, currentDate, consumption, status, phone, diu, meterNo, meterBrand) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.executemany(insert_query, seed_data)
            conn.commit()
            print("Seeded data successfully.")
            
        else:
            print("Devices table already seeded.")

        # Seed master admin if not exists
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            print("Seeding master admin...")
            cursor.execute("""
                INSERT INTO admins (username, password, role) 
                VALUES ('admin', '1061', 'master')
            """)
            conn.commit()
            print("Master admin seeded successfully.")
        else:
            print("Admin table already configured.")

        print("Database setup complete! You can now run api.py")
        
    except sqlite3.Error as e:
        print(f"Error configuring SQLite: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_database()
