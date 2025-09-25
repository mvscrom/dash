#!/usr/bin/env python3
"""
Script de prueba para verificar que la aplicación funciona correctamente
y que las mejoras en la sincronización de bombas están funcionando.
"""

import requests
import json
from datetime import datetime, timedelta

def test_app():
    """Prueba la aplicación Flask."""
    base_url = "http://localhost:5000"
    
    print("🧪 INICIANDO PRUEBAS DE LA APLICACIÓN")
    print("=" * 50)
    
    # Test 1: Página principal
    print("\n1️⃣ Probando página principal...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Página principal: OK")
        else:
            print(f"❌ Página principal: Error {response.status_code}")
    except Exception as e:
        print(f"❌ Página principal: {e}")
    
    # Test 2: API de datos GRD
    print("\n2️⃣ Probando API de datos GRD...")
    try:
        response = requests.get(f"{base_url}/api/grd_data")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API GRD: OK - {len(data)} dispositivos encontrados")
            for grd in data:
                print(f"   GRD {grd['grd_id']}: Bomba1={grd['estado_bomba_1']}, Bomba2={grd['estado_bomba_2']}")
        else:
            print(f"❌ API GRD: Error {response.status_code}")
    except Exception as e:
        print(f"❌ API GRD: {e}")
    
    # Test 3: Página de historial
    print("\n3️⃣ Probando página de historial...")
    try:
        response = requests.get(f"{base_url}/historial")
        if response.status_code == 200:
            print("✅ Página historial: OK")
        else:
            print(f"❌ Página historial: Error {response.status_code}")
    except Exception as e:
        print(f"❌ Página historial: {e}")
    
    # Test 4: API de historial (últimas 24 horas)
    print("\n4️⃣ Probando API de historial...")
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Probar con GRD 720
        response = requests.get(f"{base_url}/api/historial?grd_id=720&start_date={yesterday}&end_date={today}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API historial GRD 720: OK - {len(data)} registros")
            if data:
                # Mostrar algunos registros de ejemplo
                for i, record in enumerate(data[:3]):
                    print(f"   {record['timestamp']}: Bomba1={record['estado_bomba_1']}, Bomba2={record['estado_bomba_2']}")
        else:
            print(f"❌ API historial GRD 720: Error {response.status_code}")
            
        # Probar con GRD 787
        response = requests.get(f"{base_url}/api/historial?grd_id=787&start_date={yesterday}&end_date={today}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API historial GRD 787: OK - {len(data)} registros")
        else:
            print(f"❌ API historial GRD 787: Error {response.status_code}")
            
    except Exception as e:
        print(f"❌ API historial: {e}")
    
    # Test 5: Página de diagnóstico
    print("\n5️⃣ Probando página de diagnóstico...")
    try:
        response = requests.get(f"{base_url}/diagnostico")
        if response.status_code == 200:
            print("✅ Página diagnóstico: OK")
        else:
            print(f"❌ Página diagnóstico: Error {response.status_code}")
    except Exception as e:
        print(f"❌ Página diagnóstico: {e}")
    
    # Test 6: API de diagnóstico
    print("\n6️⃣ Probando API de diagnóstico...")
    try:
        response = requests.get(f"{base_url}/api/diagnostico_bombas?grd_id=720")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API diagnóstico GRD 720: OK - {len(data['datos'])} registros analizados")
            
            # Analizar los datos
            historial_count = len([d for d in data['datos'] if d['tabla'] == 'historial'])
            reportes_count = len([d for d in data['datos'] if d['tabla'] == 'reportes'])
            print(f"   Historial: {historial_count} registros")
            print(f"   Reportes: {reportes_count} registros")
            
            if reportes_count == 0:
                print("   ⚠️  PROBLEMA: No hay datos de reportes (bombas)")
            elif historial_count > reportes_count * 3:
                print("   ⚠️  PROBLEMA: Muchos más datos de historial que de reportes")
            else:
                print("   ✅ Sincronización parece estar bien")
                
        else:
            print(f"❌ API diagnóstico GRD 720: Error {response.status_code}")
    except Exception as e:
        print(f"❌ API diagnóstico: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 PRUEBAS COMPLETADAS")
    print("=" * 50)
    
    print("\n💡 PRÓXIMOS PASOS:")
    print("1. Si las pruebas pasaron, la aplicación está funcionando")
    print("2. Usa la página de diagnóstico para analizar problemas de sincronización")
    print("3. Revisa los datos en vivo vs historial para identificar discrepancias")
    print("4. Ajusta la configuración del middleware si es necesario")

if __name__ == "__main__":
    test_app()