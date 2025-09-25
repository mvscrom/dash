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


def is_bomba_on(value):
    """Devuelve True si el valor representa 'encendida' (1). Acepta int/str/None.

    Esta función es robusta frente a valores '0' como string, None, etc.
    """
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return False

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
        
        bombas_por_grd_id = {row['grd_id']: row for row in reportes_data}
        
        formatted_data = []
        for row in historial_data:
            grd_id = row['grd_id']
            nivel_convertido = convert_raw_to_level(grd_id, row['nivel_agua_raw'])
            presion_convertida = convert_raw_to_pressure(grd_id, row['presion_raw'])
            
        bombas = bombas_por_grd_id.get(grd_id, {'i1': None, 'i2': None})
            
            # Conversión robusta
            bomba1_status = 'Encendida' if is_bomba_on(bombas.get('i1')) else 'Apagada'
            bomba2_status = 'Encendida' if is_bomba_on(bombas.get('i2')) else 'Apagada'

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
        
        # 1. Obtener datos de historial (Nivel y Presión)
        historial_query = """
        SELECT
            h.timestamp,
            MAX(CASE WHEN h.direccion = 2 THEN h.valor END) AS nivel_agua_raw,
            MAX(CASE WHEN h.direccion = 1 THEN h.valor END) AS presion_raw
        FROM historial h
        WHERE h.grd_id = %s AND h.timestamp BETWEEN %s AND %s
        GROUP BY h.timestamp
        ORDER BY h.timestamp ASC;
        """
        cursor.execute(historial_query, (grd_id, start_date, end_date_time))
        historial_data = cursor.fetchall()
        
        if not historial_data:
            return jsonify([])

        # 2. Obtener datos de reportes (Bombas) dentro del rango
        reportes_query = """
        SELECT
            fecha,
            i1,
            i2
        FROM reportes
        WHERE grd_id = %s AND fecha BETWEEN %s AND %s
        ORDER BY fecha ASC;
        """
        cursor.execute(reportes_query, (grd_id, start_date, end_date_time))
        reportes_data = cursor.fetchall()

        # 2.b Semilla: último estado de bombas previo al primer dato de historial
        seed_query = """
        SELECT i1, i2
        FROM reportes
        WHERE grd_id = %s AND fecha < %s
        ORDER BY fecha DESC
        LIMIT 1;
        """
        first_ts = historial_data[0]['timestamp']
        cursor.execute(seed_query, (grd_id, first_ts))
        seed_row = cursor.fetchone() or {}

        # 3. Combinar los datos: Iterar sobre historial y asignar el último estado de bomba conocido (FIX para bombas)
        combined_data = []
        reporte_index = 0
        current_bombas = {
            'i1': seed_row.get('i1') if seed_row else None,
            'i2': seed_row.get('i2') if seed_row else None
        }

        for h_row in historial_data:
            h_timestamp = h_row['timestamp']
            
            # Avanzar en los reportes hasta encontrar el más reciente antes o igual a h_timestamp
            # En MySQL, la columna 'fecha' del reporte se compara con el 'timestamp' del historial
            while reporte_index < len(reportes_data) and reportes_data[reporte_index]['fecha'] <= h_timestamp:
                current_bombas['i1'] = reportes_data[reporte_index]['i1']
                current_bombas['i2'] = reportes_data[reporte_index]['i2']
                reporte_index += 1
            
            nivel_convertido = convert_raw_to_level(grd_id, h_row['nivel_agua_raw'])
            presion_convertida = convert_raw_to_pressure(grd_id, h_row['presion_raw'])
            
            # Usamos la conversión robusta para asegurar que los valores 1/0 de la BD funcionen
            bomba1_status = 'Encendida' if is_bomba_on(current_bombas.get('i1')) else 'Apagada'
            bomba2_status = 'Encendida' if is_bomba_on(current_bombas.get('i2')) else 'Apagada'

            combined_data.append({
                'grd_id': grd_id,
                'timestamp': h_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'nivel_agua': nivel_convertido,
                'presion': presion_convertida,
                'estado_bomba_1': bomba1_status,
                'estado_bomba_2': bomba2_status
            })

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