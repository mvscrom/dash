from flask import Flask, render_template, jsonify, request
import mysql.connector
import datetime

app = Flask(__name__)

# Configuración de la base de datos
DB_CONFIG = {
    'user': 'exemys_user',
    'password': 'exemys-2025',
    'host': '127.0.0.1',
    'database': 'pozo_datos'
}

# --- Constantes para la conversión y alarmas ---
RAW_MIN_NIVEL = 400
RAW_MAX_NIVEL = 2000
PRESSURE_SENSOR_MAX_BAR = 6.0

# Umbrales de alarma (valores RAW)
ALERT_TANQUE_LG = 1090
FULL_TANQUE_LG = 1120
ALERT_PLANTA_LG = 1255
FULL_PLANTA_LG = 1315

# Alturas máximas reales en metros, específicas por GRD (para el cálculo de porcentaje)
ALTURAS_MAXIMAS_MTS = {
    720: 4.51,  # Valor para el Tanque LG (100% a 4.51 mts)
    787: 3.60   # Valor para la Planta LG (100% a 3.60 mts)
}

# El manual confirma que una entrada de 0-10V tiene un valor RAW de 0-1000
RAW_MAX_PRESION_10V = 1000
# ---------------------------------------------

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("INFO: ¡Conexión a la base de datos exitosa!") # Mensaje de depuración
        return conn
    except mysql.connector.Error as err:
        print(f"ERROR: No se pudo conectar a la base de datos: {err}")
        return None

def convert_raw_to_level(grd_id, raw_value):
    """Convierte el valor RAW a nivel en metros, porcentaje y evalúa alarmas."""
    if raw_value is None or raw_value < RAW_MIN_NIVEL:
        return {'metros': 0, 'porcentaje': 0, 'estado': 'Sin Datos', 'alerta_visual': 'normal'}
    
    # Define la altura máxima del sensor en metros para cada GRD
    if grd_id == 787:
        sensor_range_m = 6.0
    else: # GRD 720
        sensor_range_m = 10.0

    raw_range = RAW_MAX_NIVEL - RAW_MIN_NIVEL
    nivel_m = ((raw_value - RAW_MIN_NIVEL) / raw_range) * sensor_range_m
    
    # El porcentaje se calcula sobre la altura máxima de la cisterna que me indicaste
    altura_maxima = ALTURAS_MAXIMAS_MTS.get(grd_id, 5.0)
    porcentaje = (nivel_m / altura_maxima) * 100
    
    estado_alarma = 'Normal'
    alerta_visual = 'normal'
    
    # Evaluar las alarmas basadas en los valores RAW que me pasaste
    if grd_id == 720: # Tanque LG
        if raw_value >= FULL_TANQUE_LG:
            estado_alarma = 'Lleno'
            alerta_visual = 'lleno'
        elif raw_value >= ALERT_TANQUE_LG:
            estado_alarma = 'Alerta'
            alerta_visual = 'alerta'
    elif grd_id == 787: # Planta LG
        if raw_value >= FULL_PLANTA_LG:
            estado_alarma = 'Lleno'
            alerta_visual = 'lleno'
        elif raw_value >= ALERT_PLANTA_LG:
            estado_alarma = 'Alerta'
            alerta_visual = 'alerta'
            
    return {
        'metros': round(nivel_m, 2),
        'porcentaje': round(porcentaje, 2),
        'estado': estado_alarma,
        'alerta_visual': alerta_visual
    }

def convert_raw_to_pressure(grd_id, raw_value):
    """Convierte el valor RAW de presión a bares, usando la lógica específica para cada GRD."""
    if raw_value is None:
        return 0

    # GRD 787 usa la lógica de 0-10V, 0-1000 RAW (Confirmado por el usuario con el valor del mapa)
    if grd_id == 787:
        # **Aseguramos la lógica correcta (0-1000 RAW) que coincide con el mapa**
        presion_bar = (raw_value / RAW_MAX_PRESION_10V) * PRESSURE_SENSOR_MAX_BAR
    else:
        # Otros GRD asumen 4-20mA con rango RAW de 2000
        presion_bar = (raw_value / 2000.0) * PRESSURE_SENSOR_MAX_BAR

    return round(presion_bar, 2)

def detect_bomba_changes(data):
    """Detecta cambios en el estado de las bombas y crea eventos EOS."""
    if not data:
        return data

    events = []
    previous_states = {'bomba1': None, 'bomba2': None}

    for i, row in enumerate(data):
        current_states = {
            'bomba1': 'Encendida' if row['estado_bomba_1'] == 'Encendida' else 'Apagada',
            'bomba2': 'Encendida' if row['estado_bomba_2'] == 'Encendida' else 'Apagada'
        }

        # Crear eventos para cambios de estado
        if previous_states['bomba1'] is not None and current_states['bomba1'] != previous_states['bomba1']:
            events.append({
                'timestamp': row['timestamp'],
                'bomba': 'bomba1',
                'estado_anterior': previous_states['bomba1'],
                'estado_nuevo': current_states['bomba1'],
                'tipo': 'cambio_estado'
            })

        if previous_states['bomba2'] is not None and current_states['bomba2'] != previous_states['bomba2']:
            events.append({
                'timestamp': row['timestamp'],
                'bomba': 'bomba2',
                'estado_anterior': previous_states['bomba2'],
                'estado_nuevo': current_states['bomba2'],
                'tipo': 'cambio_estado'
            })

        # Agregar el estado actual al registro
        row['eventos'] = [e for e in events if e['timestamp'] == row['timestamp']]
        previous_states = current_states.copy()

    return data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/grd_data')
def get_grd_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)
    
    historial_query = """
    SELECT
        t1.grd_id,
        t1.timestamp,
        MAX(CASE WHEN t1.direccion = 2 THEN t1.valor END) AS nivel_agua_raw,
        MAX(CASE WHEN t1.direccion = 1 THEN t1.valor END) AS presion_raw
    FROM historial AS t1
    INNER JOIN (
        SELECT grd_id, MAX(timestamp) AS max_timestamp
        FROM historial
        GROUP BY grd_id
    ) AS t2 ON t1.grd_id = t2.grd_id AND t1.timestamp = t2.max_timestamp
    GROUP BY t1.grd_id, t1.timestamp;
    """
    
    reportes_query = """
    SELECT
        t1.grd_id,
        t1.i1,
        t1.i2
    FROM reportes AS t1
    INNER JOIN (
        SELECT grd_id, MAX(fecha) AS max_fecha
        FROM reportes
        GROUP BY grd_id
    ) AS t2 ON t1.grd_id = t2.grd_id AND t1.fecha = t2.max_fecha;
    """
    
    try:
        cursor.execute(historial_query)
        historial_data = cursor.fetchall()

        cursor.execute(reportes_query)
        reportes_data = cursor.fetchall()

        # Crear una consulta mejorada que combine los datos actuales
        current_combined_query = """
        SELECT
            h.grd_id,
            h.timestamp,
            h.nivel_agua_raw,
            h.presion_raw,
            r.i1,
            r.i2
        FROM (
            SELECT
                grd_id,
                timestamp,
                MAX(CASE WHEN direccion = 2 THEN valor END) AS nivel_agua_raw,
                MAX(CASE WHEN direccion = 1 THEN valor END) AS presion_raw
            FROM historial
            GROUP BY grd_id, timestamp
        ) h
        LEFT JOIN reportes r ON h.timestamp >= r.fecha
            AND h.timestamp < DATE_ADD(r.fecha, INTERVAL 1 DAY)
            AND r.grd_id = h.grd_id
        INNER JOIN (
            SELECT grd_id, MAX(fecha) AS max_fecha
            FROM reportes
            GROUP BY grd_id
        ) r_max ON r.grd_id = r_max.grd_id AND r.fecha = r_max.max_fecha
        ORDER BY h.grd_id, h.timestamp DESC;
        """

        cursor.execute(current_combined_query)
        combined_data = cursor.fetchall()

        formatted_data = []
        for row in combined_data:
            grd_id = row['grd_id']
            nivel_convertido = convert_raw_to_level(grd_id, row['nivel_agua_raw'])
            presion_convertida = convert_raw_to_pressure(grd_id, row['presion_raw'])

            # Conversión robusta para estados de bombas
            bomba1_status = 'Encendida' if row['i1'] and int(row['i1']) == 1 else 'Apagada'
            bomba2_status = 'Encendida' if row['i2'] and int(row['i2']) == 1 else 'Apagada'

            formatted_data.append({
                'grd_id': grd_id,
                'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else None,
                'nivel_agua': nivel_convertido,
                'presion': presion_convertida,
                'estado_bomba_1': bomba1_status,
                'estado_bomba_2': bomba2_status
            })

        return jsonify(formatted_data)
        
    except mysql.connector.Error as err:
        print(f"Error en la consulta SQL: {err}")
        return jsonify({"error": "Error interno del servidor al procesar la solicitud"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/historial')
def historial():
    return render_template('historial.html')

@app.route('/api/historial')
def get_historial_data():
    grd_id = int(request.args.get('grd_id')) # Aseguramos que sea entero
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not grd_id or not start_date or not end_date:
        return jsonify({"error": "Faltan parámetros de búsqueda (grd_id, start_date, end_date)."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)

    try:
        end_date_time = end_date + " 23:59:59"

        # Consulta mejorada que combina historial y reportes usando LEFT JOIN
        # Esto asegura que tengamos todos los timestamps de historial y el estado de bombas más reciente
        combined_query = """
        SELECT
            h.timestamp,
            h.nivel_agua_raw,
            h.presion_raw,
            COALESCE(r.i1, r_prev.i1) as i1,
            COALESCE(r.i2, r_prev.i2) as i2
        FROM (
            SELECT
                timestamp,
                MAX(CASE WHEN direccion = 2 THEN valor END) AS nivel_agua_raw,
                MAX(CASE WHEN direccion = 1 THEN valor END) AS presion_raw
            FROM historial
            WHERE grd_id = %s AND timestamp BETWEEN %s AND %s
            GROUP BY timestamp
        ) h
        LEFT JOIN reportes r ON h.timestamp >= r.fecha
            AND h.timestamp < DATE_ADD(r.fecha, INTERVAL 1 DAY)
            AND r.grd_id = %s
        LEFT JOIN (
            SELECT grd_id, fecha,
                   i1, i2,
                   ROW_NUMBER() OVER (PARTITION BY grd_id ORDER BY fecha DESC) as rn
            FROM reportes
            WHERE grd_id = %s AND fecha <= %s
        ) r_prev ON r_prev.grd_id = %s AND r_prev.rn = 1
        WHERE h.timestamp BETWEEN %s AND %s
        ORDER BY h.timestamp ASC;
        """

        try:
            cursor.execute(combined_query, (grd_id, start_date, end_date_time, grd_id, grd_id, end_date_time, grd_id, start_date, end_date_time))
            data = cursor.fetchall()
        except mysql.connector.Error as sql_err:
            print(f"Error con consulta compleja, usando fallback: {sql_err}")
            # Fallback a consulta más simple pero menos precisa
            fallback_query = """
            SELECT
                h.timestamp,
                MAX(CASE WHEN h.direccion = 2 THEN h.valor END) AS nivel_agua_raw,
                MAX(CASE WHEN h.direccion = 1 THEN h.valor END) AS presion_raw,
                r.i1,
                r.i2
            FROM historial h
            LEFT JOIN reportes r ON h.grd_id = r.grd_id
                AND h.timestamp >= r.fecha
                AND h.timestamp < DATE_ADD(r.fecha, INTERVAL 1 DAY)
            WHERE h.grd_id = %s AND h.timestamp BETWEEN %s AND %s
            GROUP BY h.timestamp, r.i1, r.i2
            ORDER BY h.timestamp ASC;
            """
            cursor.execute(fallback_query, (grd_id, start_date, end_date_time))
            data = cursor.fetchall()

        if not data:
            return jsonify([])

        # Procesar los datos y convertirlos al formato esperado
        combined_data = []
        previous_bombas = {'i1': None, 'i2': None}

        for row in data:
            # Usar el estado de bomba de este registro si existe, sino usar el anterior
            current_bombas = {
                'i1': row['i1'] if row['i1'] is not None else previous_bombas['i1'],
                'i2': row['i2'] if row['i2'] is not None else previous_bombas['i2']
            }

            # Actualizar el estado anterior si tenemos datos nuevos
            if row['i1'] is not None:
                previous_bombas['i1'] = row['i1']
            if row['i2'] is not None:
                previous_bombas['i2'] = row['i2']

            nivel_convertido = convert_raw_to_level(grd_id, row['nivel_agua_raw'])
            presion_convertida = convert_raw_to_pressure(grd_id, row['presion_raw'])

            # Conversión robusta para estados de bombas
            bomba1_status = 'Encendida' if current_bombas.get('i1') and int(current_bombas.get('i1')) == 1 else 'Apagada'
            bomba2_status = 'Encendida' if current_bombas.get('i2') and int(current_bombas.get('i2')) == 1 else 'Apagada'

            combined_data.append({
                'grd_id': grd_id,
                'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'nivel_agua': nivel_convertido,
                'presion': presion_convertida,
                'estado_bomba_1': bomba1_status,
                'estado_bomba_2': bomba2_status
            })

        # Aplicar detección de cambios EOS
        combined_data = detect_bomba_changes(combined_data)

        return jsonify(combined_data)

    except mysql.connector.Error as err:
        print(f"Error en la consulta SQL del historial: {err}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/tank/<int:grd_id>')
def tank_detail(grd_id):
    return render_template('tank.html')

if __name__ == '__main__':
    app.run(debug=True)