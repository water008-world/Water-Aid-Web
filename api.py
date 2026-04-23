from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
# Enable CORS to allow the frontend HTML files to communicate with this local API
CORS(app)

def get_db_connection():
    # Establishes connection to SQLite (local file database)
    conn = sqlite3.connect("water_aid.db")
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------------------------------
# ENDPOINT 1: Fetch all devices for Dashboard & App
# -----------------------------------------------------
@app.route('/api/devices', methods=['GET'])
def get_devices():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Pull all static metadata of devices
        cursor.execute("SELECT * FROM devices")
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Hydrate the dynamic live data by pulling latest from telemetry log
        for d in devices:
            cursor.execute("""
                SELECT battery, network_signal, water_rate, timestamp 
                FROM telemetry WHERE device_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (d['id'],))
            telemetry = cursor.fetchone()
            if telemetry:
                d['battery'] = telemetry['battery']
                d['network_signal'] = telemetry['network_signal']
                d['water_rate'] = telemetry['water_rate']
                d['flow'] = telemetry['water_rate']  # Maps to the live flow UI visually
                
        return jsonify(devices), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# -----------------------------------------------------
# ENDPOINT 2: Manage Devices (Update / Add user entries)
# -----------------------------------------------------
@app.route('/api/devices', methods=['POST'])
def add_device():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SQLite UPSERT - Creates a new device or updates it if it exists.
        query = """
            INSERT INTO devices (id, accountNo, owner, phone, location, status, diu, meterNo, meterBrand, meterDiameter, houseType, consumerType, waterPrice, installDate, amrDate, flow, usage_val, flagged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
            accountNo=excluded.accountNo, owner=excluded.owner, phone=excluded.phone, location=excluded.location, 
            status=excluded.status, diu=excluded.diu, meterNo=excluded.meterNo, meterBrand=excluded.meterBrand, 
            meterDiameter=excluded.meterDiameter, houseType=excluded.houseType, consumerType=excluded.consumerType, 
            waterPrice=excluded.waterPrice, flagged=excluded.flagged
        """
        vals = (
            data.get('id'), data.get('accountNo',''), data.get('owner',''), data.get('phone',''), data.get('location',''),
            data.get('status','offline'), data.get('diu',''), data.get('meterNo',''), data.get('meterBrand',''),
            data.get('meterDiameter',''), data.get('houseType',''), data.get('consumerType',''), data.get('waterPrice','8.00'),
            data.get('installDate',''), data.get('amrDate',''), data.get('flow',0.0), data.get('usage',0.0), data.get('flagged', False)
        )
        
        cursor.execute(query, vals)
        conn.commit()
        return jsonify({"message": "Device added or updated successfully in SQLite", "id": data.get('id')}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# -----------------------------------------------------
# ENDPOINT 3: Toggle Device Flag (Manage Page)
# -----------------------------------------------------
@app.route('/api/devices/flag/<device_id>', methods=['POST'])
def toggle_flag(device_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE devices SET flagged = NOT flagged WHERE id = ?", (device_id,))
        conn.commit()
        return jsonify({"message": f"Successfully toggled flag for {device_id}"})
    except Exception as e:
         return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# -----------------------------------------------------
# ENDPOINT 4: Hardware Webhook! (Receives raw ESP/MQTT strings)
# -----------------------------------------------------
@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    # The ESP board sends payload: <device_id>,<battery>,<network_sig>,<water_rate>
    try:
        if request.is_json:
            data = request.json
            device_id = data.get('id')
            battery = data.get('battery')
            network = data.get('network')
            waterrate = data.get('waterrate')
        else:
            raw_data = request.data.decode('utf-8').strip()
            parts = raw_data.split(',')
            
            if len(parts) == 4:
                device_id = parts[0]
                battery = int(parts[1])
                network = int(parts[2])
                waterrate = float(parts[3])
            else:
                return jsonify({"error": "Invalid format. Required plain text: id,battery,network,waterrate"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Update the parent device to show it is Online and record latest flow.
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE devices 
            SET flow = ?, currentDate = ?, status = 'online' 
            WHERE id = ?
        """, (waterrate, current_time, device_id))
        
        # 2. Insert the raw event log into the Telemetry storage.
        cursor.execute("""
            INSERT INTO telemetry (device_id, battery, network_signal, water_rate)
            VALUES (?, ?, ?, ?)
        """, (device_id, battery, network, waterrate))
        
        conn.commit()
        return jsonify({"message": "Telemetry received and routed securely to database."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# -----------------------------------------------------
# ENDPOINT 5: Login Auth
# -----------------------------------------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM admins WHERE username=? AND password=?", (username, password))
        admin = cursor.fetchone()
        if admin:
            return jsonify({"success": True, "admin": dict(admin)}), 200
        else:
            return jsonify({"success": False, "message": "Invalid password or username."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# -----------------------------------------------------
# ENDPOINT 6: Fetch Admins & Create Admins
# -----------------------------------------------------
@app.route('/api/admins', methods=['GET', 'POST'])
def manage_admins():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            cursor.execute("SELECT id, username, role, created_at FROM admins")
            admins = [dict(row) for row in cursor.fetchall()]
            return jsonify(admins), 200
            
        if request.method == 'POST':
            data = request.json
            admin_user = data.get('username')
            admin_pass = data.get('password')
            admin_role = data.get('role', 'admin') # Default to standard 'admin'
            
            # Limit check
            cursor.execute("SELECT id FROM admins WHERE username=?", (admin_user,))
            if cursor.fetchone():
                return jsonify({"error": "Admin username already exists!"}), 400
                
            cursor.execute("INSERT INTO admins (username, password, role) VALUES (?, ?, ?)", (admin_user, admin_pass, admin_role))
            conn.commit()
            return jsonify({"message": "New admin assigned successfully"}), 201
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    print("WARNING: Make sure you have run `python setup_db.py` first to generate the tables!")
    # Runs the API locally on port 5000, viewable by your front-end scripts automatically via CORS.
    app.run(host='0.0.0.0', port=5000, debug=True)
