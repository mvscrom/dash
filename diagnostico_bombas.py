#!/usr/bin/env python3
"""
Script de diagnóstico para el problema de las bombas en el historial
Analiza las tablas de la base de datos para identificar por qué las bombas
aparecen apagadas en el historial cuando deberían estar encendidas.
"""

import mysql.connector
from datetime import datetime, timedelta
import sys

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
        print("✅ Conexión a la base de datos exitosa!")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error de conexión: {err}")
        return None

def diagnosticar_estructura_tablas():
    """Diagnostica la estructura de las tablas."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO DE ESTRUCTURA DE TABLAS")
    print("="*60)
    
    # Mostrar tablas disponibles
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    print(f"\n📋 Tablas encontradas: {len(tables)}")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Analizar cada tabla
    for table in tables:
        table_name = table[0]
        print(f"\n🔍 ANALIZANDO TABLA: {table_name}")
        print("-" * 40)
        
        # Estructura
        cursor.execute(f"DESCRIBE {table_name};")
        columns = cursor.fetchall()
        print("📊 Estructura:")
        for col in columns:
            print(f"   {col[0]} - {col[1]} - {col[2]} - {col[3]}")
        
        # Conteo de registros
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"📈 Total registros: {count}")
        
        if count > 0:
            # Fechas mínima y máxima
            try:
                cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name};")
                min_max = cursor.fetchone()
                if min_max[0] and min_max[1]:
                    print(f"📅 Rango de fechas: {min_max[0]} a {min_max[1]}")
            except:
                try:
                    cursor.execute(f"SELECT MIN(fecha), MAX(fecha) FROM {table_name};")
                    min_max = cursor.fetchone()
                    if min_max[0] and min_max[1]:
                        print(f"📅 Rango de fechas: {min_max[0]} a {min_max[1]}")
                except:
                    print("📅 No se pudo obtener rango de fechas")
            
            # Muestra de datos
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT 3;")
            samples = cursor.fetchall()
            print("🔬 Últimos 3 registros:")
            for i, sample in enumerate(samples, 1):
                print(f"   {i}: {sample}")
    
    cursor.close()
    conn.close()

def diagnosticar_problema_bombas():
    """Diagnostica específicamente el problema de las bombas."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor(dictionary=True)
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO DEL PROBLEMA DE BOMBAS")
    print("="*60)
    
    # Verificar datos recientes de historial
    print("\n🔍 DATOS RECIENTES DE HISTORIAL:")
    historial_query = """
    SELECT 
        grd_id,
        timestamp,
        direccion,
        valor,
        COUNT(*) as registros
    FROM historial 
    WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    GROUP BY grd_id, timestamp, direccion
    ORDER BY timestamp DESC
    LIMIT 10;
    """
    
    try:
        cursor.execute(historial_query)
        historial_data = cursor.fetchall()
        
        if historial_data:
            print("📊 Últimos registros de historial (última hora):")
            for row in historial_data:
                dir_name = "Presión" if row['direccion'] == 1 else "Nivel" if row['direccion'] == 2 else f"Dir {row['direccion']}"
                print(f"   GRD {row['grd_id']} - {row['timestamp']} - {dir_name}: {row['valor']}")
        else:
            print("⚠️  No hay datos de historial en la última hora")
    except Exception as e:
        print(f"❌ Error en consulta de historial: {e}")
    
    # Verificar datos recientes de reportes
    print("\n🔍 DATOS RECIENTES DE REPORTES:")
    reportes_query = """
    SELECT 
        grd_id,
        fecha,
        i1,
        i2,
        COUNT(*) as registros
    FROM reportes 
    WHERE fecha >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    ORDER BY fecha DESC
    LIMIT 10;
    """
    
    try:
        cursor.execute(reportes_query)
        reportes_data = cursor.fetchall()
        
        if reportes_data:
            print("📊 Últimos registros de reportes (última hora):")
            for row in reportes_data:
                bomba1 = "Encendida" if row['i1'] == 1 else "Apagada"
                bomba2 = "Encendida" if row['i2'] == 1 else "Apagada"
                print(f"   GRD {row['grd_id']} - {row['fecha']} - Bomba1: {bomba1}, Bomba2: {bomba2}")
        else:
            print("⚠️  No hay datos de reportes en la última hora")
    except Exception as e:
        print(f"❌ Error en consulta de reportes: {e}")
    
    # Comparar sincronización temporal
    print("\n🔍 ANÁLISIS DE SINCRONIZACIÓN:")
    
    # Para GRD 720
    print("\n📋 GRD 720 (Tanque LG):")
    sync_query_720 = """
    SELECT 
        h.timestamp as historial_time,
        MAX(CASE WHEN h.direccion = 2 THEN h.valor END) as nivel,
        r.fecha as reporte_time,
        r.i1 as bomba1,
        r.i2 as bomba2,
        TIMESTAMPDIFF(SECOND, r.fecha, h.timestamp) as diff_seconds
    FROM historial h
    LEFT JOIN reportes r ON r.grd_id = h.grd_id 
        AND r.fecha <= h.timestamp
        AND r.fecha >= DATE_SUB(h.timestamp, INTERVAL 5 MINUTE)
    WHERE h.grd_id = 720 
        AND h.timestamp >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        AND h.direccion = 2
    GROUP BY h.timestamp
    ORDER BY h.timestamp DESC
    LIMIT 5;
    """
    
    try:
        cursor.execute(sync_query_720)
        sync_data_720 = cursor.fetchall()
        
        if sync_data_720:
            for row in sync_data_720:
                bomba1 = "Encendida" if row['bomba1'] == 1 else "Apagada" if row['bomba1'] is not None else "Sin datos"
                bomba2 = "Encendida" if row['bomba2'] == 1 else "Apagada" if row['bomba2'] is not None else "Sin datos"
                diff = f"{row['diff_seconds']}s" if row['diff_seconds'] else "N/A"
                print(f"   {row['historial_time']} - Nivel: {row['nivel']} - Bomba1: {bomba1}, Bomba2: {bomba2} (diff: {diff})")
        else:
            print("   ⚠️  No hay datos de sincronización para GRD 720")
    except Exception as e:
        print(f"   ❌ Error en análisis de GRD 720: {e}")
    
    # Para GRD 787
    print("\n📋 GRD 787 (Planta LG):")
    sync_query_787 = """
    SELECT 
        h.timestamp as historial_time,
        MAX(CASE WHEN h.direccion = 2 THEN h.valor END) as nivel,
        r.fecha as reporte_time,
        r.i1 as bomba1,
        r.i2 as bomba2,
        TIMESTAMPDIFF(SECOND, r.fecha, h.timestamp) as diff_seconds
    FROM historial h
    LEFT JOIN reportes r ON r.grd_id = h.grd_id 
        AND r.fecha <= h.timestamp
        AND r.fecha >= DATE_SUB(h.timestamp, INTERVAL 5 MINUTE)
    WHERE h.grd_id = 787 
        AND h.timestamp >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        AND h.direccion = 2
    GROUP BY h.timestamp
    ORDER BY h.timestamp DESC
    LIMIT 5;
    """
    
    try:
        cursor.execute(sync_query_787)
        sync_data_787 = cursor.fetchall()
        
        if sync_data_787:
            for row in sync_data_787:
                bomba1 = "Encendida" if row['bomba1'] == 1 else "Apagada" if row['bomba1'] is not None else "Sin datos"
                bomba2 = "Encendida" if row['bomba2'] == 1 else "Apagada" if row['bomba2'] is not None else "Sin datos"
                diff = f"{row['diff_seconds']}s" if row['diff_seconds'] else "N/A"
                print(f"   {row['historial_time']} - Nivel: {row['nivel']} - Bomba1: {bomba1}, Bomba2: {bomba2} (diff: {diff})")
        else:
            print("   ⚠️  No hay datos de sincronización para GRD 787")
    except Exception as e:
        print(f"   ❌ Error en análisis de GRD 787: {e}")
    
    cursor.close()
    conn.close()

def main():
    """Función principal del diagnóstico."""
    print("🔧 DIAGNÓSTICO DEL SISTEMA DE BOMBAS")
    print("=" * 60)
    print("Este script analiza por qué las bombas aparecen apagadas en el historial")
    print("cuando deberían estar encendidas según los datos en vivo.")
    print()
    
    # Paso 1: Estructura de tablas
    diagnosticar_estructura_tablas()
    
    # Paso 2: Problema específico de bombas
    diagnosticar_problema_bombas()
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO COMPLETADO")
    print("="*60)
    print("\n💡 PRÓXIMOS PASOS:")
    print("1. Revisa los resultados del diagnóstico")
    print("2. Identifica si hay falta de datos en la tabla 'reportes'")
    print("3. Verifica la sincronización temporal entre 'historial' y 'reportes'")
    print("4. Considera implementar una solución de sincronización mejorada")

if __name__ == "__main__":
    main()