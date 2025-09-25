#!/usr/bin/env python3

import mysql.connector
import datetime

# Configuración de la base de datos
DB_CONFIG = {
    'user': 'exemys_user',
    'password': 'exemys-2025',
    'host': '127.0.0.1',
    'database': 'pozo_datos'
}

def get_db_connection():
    """Establece y retorna una conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("INFO: ¡Conexión a la base de datos exitosa!")
        return conn
    except mysql.connector.Error as err:
        print(f"ERROR: No se pudo conectar a la base de datos: {err}")
        return None

def analyze_data():
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor(dictionary=True)

    try:
        print("\n=== ANÁLISIS DE DATOS ===")

        # 1. Ver últimos registros de historial para GRD 720 y 787
        print("\n1. ÚLTIMOS REGISTROS DE HISTORIAL:")
        historial_query = """
        SELECT grd_id, timestamp, direccion, valor
        FROM historial
        WHERE grd_id IN (720, 787)
        ORDER BY grd_id, timestamp DESC
        LIMIT 10;
        """
        cursor.execute(historial_query)
        historial_data = cursor.fetchall()
        for row in historial_data:
            print(f"GRD {row['grd_id']}: {row['timestamp']} - Dir: {row['direccion']} - Valor: {row['valor']}")

        # 2. Ver últimos registros de reportes para GRD 720 y 787
        print("\n2. ÚLTIMOS REGISTROS DE REPORTES:")
        reportes_query = """
        SELECT grd_id, fecha, i1, i2
        FROM reportes
        WHERE grd_id IN (720, 787)
        ORDER BY grd_id, fecha DESC
        LIMIT 10;
        """
        cursor.execute(reportes_query)
        reportes_data = cursor.fetchall()
        for row in reportes_data:
            print(f"GRD {row['grd_id']}: {row['fecha']} - I1: {row['i1']} - I2: {row['i2']}")

        # 3. Ver datos de la consulta actual (como en /api/grd_data)
        print("\n3. DATOS ACTUALES (como en /api/grd_data):")
        current_query = """
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
        WHERE t1.grd_id IN (720, 787)
        GROUP BY t1.grd_id, t1.timestamp;
        """
        cursor.execute(current_query)
        current_data = cursor.fetchall()

        reportes_current_query = """
        SELECT
            t1.grd_id,
            t1.i1,
            t1.i2
        FROM reportes AS t1
        INNER JOIN (
            SELECT grd_id, MAX(fecha) AS max_fecha
            FROM reportes
            GROUP BY grd_id
        ) AS t2 ON t1.grd_id = t2.grd_id AND t1.fecha = t2.max_fecha
        WHERE t1.grd_id IN (720, 787);
        """
        cursor.execute(reportes_current_query)
        reportes_current_data = cursor.fetchall()

        bombas_por_grd_id = {row['grd_id']: row for row in reportes_current_data}

        for row in current_data:
            grd_id = row['grd_id']
            bombas = bombas_por_grd_id.get(grd_id, {'i1': None, 'i2': None})

            bomba1_status = 'Encendida' if bombas.get('i1') and int(bombas.get('i1')) == 1 else 'Apagada'
            bomba2_status = 'Encendida' if bombas.get('i2') and int(bombas.get('i2')) == 1 else 'Apagada'

            print(f"GRD {grd_id}: Nivel: {row['nivel_agua_raw']}, Presión: {row['presion_raw']}, Bomba1: {bomba1_status}, Bomba2: {bomba2_status}")

        # 4. Verificar sincronización de fechas
        print("\n4. VERIFICACIÓN DE SINCRONIZACIÓN DE FECHAS:")
        sync_check_query = """
        SELECT h.grd_id, h.timestamp, r.fecha, r.i1, r.i2
        FROM historial h
        LEFT JOIN reportes r ON h.grd_id = r.grd_id
        WHERE h.grd_id IN (720, 787)
        ORDER BY h.grd_id, h.timestamp DESC
        LIMIT 20;
        """
        cursor.execute(sync_check_query)
        sync_data = cursor.fetchall()
        for row in sync_data:
            print(f"GRD {row['grd_id']}: Historial: {row['timestamp']}, Reportes: {row['fecha']}, I1: {row['i1']}, I2: {row['i2']}")

    except mysql.connector.Error as err:
        print(f"Error en la consulta: {err}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_data()