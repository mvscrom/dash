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

def find_closest_pump_state(target_timestamp, reportes_data):
    """
    Encuentra el estado de las bombas más cercano al timestamp dado.
    Busca hacia atrás en el tiempo para encontrar el último estado conocido.
    """
    if not reportes_data:
        return None
    
    # Ordenar reportes por fecha (más reciente primero)
    sorted_reportes = sorted(reportes_data, key=lambda x: x['fecha'], reverse=True)
    
    # Buscar el reporte más reciente que sea anterior o igual al timestamp objetivo
    for report in sorted_reportes:
        if report['fecha'] <= target_timestamp:
            return report
    
    # Si no encontramos ninguno anterior, devolver el más antiguo
    return sorted_reportes[-1] if sorted_reportes else None


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
            
            # Conversión a string robusta
            bomba1_status = 'Encendida' if bombas.get('i1') and int(bombas.get('i1')) == 1 else 'Apagada'
            bomba2_status = 'Encendida' if bombas.get('i2') and int(bombas.get('i2')) == 1 else 'Apagada'

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

        # 2. Obtener datos de reportes (Bombas) con rango ampliado para asegurar cobertura
        # Ampliamos el rango hacia atrás para encontrar el último estado conocido
        extended_start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d') - datetime.timedelta(days=7)
        extended_start_date_str = extended_start_date.strftime('%Y-%m-%d')
        
        reportes_query = """
        SELECT
            fecha,
            i1,
            i2
        FROM reportes
        WHERE grd_id = %s AND fecha BETWEEN %s AND %s
        ORDER BY fecha ASC;
        """
        cursor.execute(reportes_query, (grd_id, extended_start_date_str, end_date_time))
        reportes_data = cursor.fetchall()
        
        # Debug: Mostrar información sobre los datos obtenidos
        print(f"DEBUG: GRD {grd_id} - Registros historial: {len(historial_data)}, Registros reportes: {len(reportes_data)}")
        if reportes_data:
            print(f"DEBUG: Primer reporte: {reportes_data[0]}")
            print(f"DEBUG: Último reporte: {reportes_data[-1]}")
        if historial_data:
            print(f"DEBUG: Primer historial: {historial_data[0]['timestamp']}")
            print(f"DEBUG: Último historial: {historial_data[-1]['timestamp']}")

        # 3. Combinar los datos: Usar la nueva función auxiliar para encontrar estados de bomba
        combined_data = []
        
        for h_row in historial_data:
            h_timestamp = h_row['timestamp']
            
            # Encontrar el estado de bomba más cercano
            closest_report = find_closest_pump_state(h_timestamp, reportes_data)
            
            nivel_convertido = convert_raw_to_level(grd_id, h_row['nivel_agua_raw'])
            presion_convertida = convert_raw_to_pressure(grd_id, h_row['presion_raw'])
            
            # Determinar el estado de las bombas
            if closest_report:
                # Conversión robusta: manejar diferentes tipos de datos (int, str, None)
                try:
                    i1_val = closest_report.get('i1')
                    i2_val = closest_report.get('i2')
                    
                    bomba1_status = 'Encendida' if i1_val is not None and int(i1_val) == 1 else 'Apagada'
                    bomba2_status = 'Encendida' if i2_val is not None and int(i2_val) == 1 else 'Apagada'
                    
                    # Debug para el primer registro
                    if len(combined_data) == 0:
                        print(f"DEBUG: Primer registro - i1: {i1_val}, i2: {i2_val}, Bomba1: {bomba1_status}, Bomba2: {bomba2_status}")
                        
                except (ValueError, TypeError) as e:
                    print(f"ERROR convirtiendo valores de bomba: {e}")
                    bomba1_status = 'Error'
                    bomba2_status = 'Error'
            else:
                bomba1_status = 'Sin Datos'
                bomba2_status = 'Sin Datos'
                if len(combined_data) == 0:  # Solo mostrar para el primer registro
                    print(f"ADVERTENCIA: No se encontró reporte de bombas para GRD {grd_id} en timestamp {h_timestamp}")

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