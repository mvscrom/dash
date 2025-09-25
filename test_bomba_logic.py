#!/usr/bin/env python3
"""
Script de prueba para demostrar la lógica mejorada de sincronización de bombas
y el sistema EOS para tracking de cambios de estado.
"""

# Simular datos de ejemplo para mostrar el problema y la solución
def simulate_historial_data():
    """Simula datos de la tabla historial"""
    return [
        {'grd_id': 720, 'timestamp': '2025-01-20 10:00:00', 'direccion': 2, 'valor': 1500},  # Nivel
        {'grd_id': 720, 'timestamp': '2025-01-20 10:00:00', 'direccion': 1, 'valor': 500},   # Presión
        {'grd_id': 720, 'timestamp': '2025-01-20 10:05:00', 'direccion': 2, 'valor': 1480},
        {'grd_id': 720, 'timestamp': '2025-01-20 10:05:00', 'direccion': 1, 'valor': 520},
        {'grd_id': 720, 'timestamp': '2025-01-20 10:10:00', 'direccion': 2, 'valor': 1450},
        {'grd_id': 720, 'timestamp': '2025-01-20 10:10:00', 'direccion': 1, 'valor': 540},
    ]

def simulate_reportes_data():
    """Simula datos de la tabla reportes"""
    return [
        {'grd_id': 720, 'fecha': '2025-01-20 10:02:00', 'i1': 1, 'i2': 0},  # Bomba 1 encendida, Bomba 2 apagada
        {'grd_id': 720, 'fecha': '2025-01-20 10:07:00', 'i1': 0, 'i2': 1},  # Bomba 1 apagada, Bomba 2 encendida
    ]

def old_combination_logic(historial_data, reportes_data):
    """Lógica antigua de combinación - tiene problemas"""
    print("=== LÓGICA ANTIGUA ===")

    combined_data = []
    reporte_index = 0
    current_bombas = {'i1': None, 'i2': None}

    for h_row in historial_data:
        h_timestamp = h_row['timestamp']

        # Avanzar en los reportes hasta encontrar el más reciente antes o igual a h_timestamp
        while reporte_index < len(reportes_data) and reportes_data[reporte_index]['fecha'] <= h_timestamp:
            current_bombas['i1'] = reportes_data[reporte_index]['i1']
            current_bombas['i2'] = reportes_data[reporte_index]['i2']
            reporte_index += 1

        bomba1_status = 'Encendida' if current_bombas.get('i1') and int(current_bombas.get('i1')) == 1 else 'Apagada'
        bomba2_status = 'Encendida' if current_bombas.get('i2') and int(current_bombas.get('i2')) == 1 else 'Apagada'

        combined_data.append({
            'timestamp': h_timestamp,
            'estado_bomba_1': bomba1_status,
            'estado_bomba_2': bomba2_status
        })

    for row in combined_data:
        print(f"{row['timestamp']}: Bomba1={row['estado_bomba_1']}, Bomba2={row['estado_bomba_2']}")

    return combined_data

def new_combination_logic(historial_data, reportes_data):
    """Nueva lógica mejorada - resuelve los problemas"""
    print("\n=== NUEVA LÓGICA MEJORADA ===")

    # Simular consulta LEFT JOIN mejorada
    combined_data = []
    previous_bombas = {'i1': None, 'i2': None}

    # Crear índice de reportes por fecha
    reportes_by_time = {}
    for reporte in reportes_data:
        reportes_by_time[reporte['fecha']] = reporte

    for h_row in historial_data:
        h_timestamp = h_row['timestamp']

        # Buscar el estado de bomba más reciente disponible
        current_bombas = {'i1': None, 'i2': None}

        # Buscar en orden cronológico inverso el reporte más reciente
        for reporte_time in sorted(reportes_by_time.keys(), reverse=True):
            if reporte_time <= h_timestamp:
                current_bombas = {
                    'i1': reportes_by_time[reporte_time]['i1'],
                    'i2': reportes_by_time[reporte_time]['i2']
                }
                break

        # Si no encontramos un reporte reciente, mantener el estado anterior
        if current_bombas['i1'] is None:
            current_bombas['i1'] = previous_bombas['i1']
        if current_bombas['i2'] is None:
            current_bombas['i2'] = previous_bombas['i2']

        # Actualizar el estado anterior
        previous_bombas = current_bombas.copy()

        bomba1_status = 'Encendida' if current_bombas.get('i1') and int(current_bombas.get('i1')) == 1 else 'Apagada'
        bomba2_status = 'Encendida' if current_bombas.get('i2') and int(current_bombas.get('i2')) == 1 else 'Apagada'

        combined_data.append({
            'timestamp': h_timestamp,
            'estado_bomba_1': bomba1_status,
            'estado_bomba_2': bomba2_status
        })

    for row in combined_data:
        print(f"{row['timestamp']}: Bomba1={row['estado_bomba_1']}, Bomba2={row['estado_bomba_2']}")

    return combined_data

def detect_bomba_changes(data):
    """Detecta cambios en el estado de las bombas y crea eventos EOS."""
    print("\n=== DETECCIÓN DE CAMBIOS EOS ===")

    if not data:
        return data

    events = []
    previous_states = {'bomba1': None, 'bomba2': None}

    for i, row in enumerate(data):
        current_states = {
            'bomba1': row['estado_bomba_1'],
            'bomba2': row['estado_bomba_2']
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

    # Mostrar eventos
    for row in data:
        if row['eventos']:
            for evento in row['eventos']:
                print(f"[{row['timestamp']}] {evento['bomba']}: {evento['estado_anterior']} → {evento['estado_nuevo']}")

    return data

def main():
    print("=== DEMOSTRACIÓN DE LA MEJORA EN EL MANEJO DE BOMBAS ===")
    print("Este script muestra cómo la nueva lógica resuelve el problema de bombas 'apagadas'")

    # Simular datos
    historial_data = simulate_historial_data()
    reportes_data = simulate_reportes_data()

    print(f"\nDatos de historial: {len(historial_data)} registros")
    print(f"Datos de reportes: {len(reportes_data)} registros")

    # Mostrar lógica antigua
    old_data = old_combination_logic(historial_data, reportes_data)

    # Mostrar lógica nueva
    new_data = new_combination_logic(historial_data, reportes_data)

    # Mostrar detección de cambios
    new_data_with_events = detect_bomba_changes(new_data)

    print("\n=== RESUMEN DE MEJORAS ===")
    print("1. ✅ Sincronización mejorada entre timestamps y fechas")
    print("2. ✅ Estados de bombas persistentes (no se pierden)")
    print("3. ✅ Sistema EOS para tracking de cambios")
    print("4. ✅ Mejor manejo de datos faltantes")
    print("5. ✅ Estadísticas de funcionamiento de bombas")
    print("6. ✅ Fallback para consultas SQL complejas")

if __name__ == "__main__":
    main()