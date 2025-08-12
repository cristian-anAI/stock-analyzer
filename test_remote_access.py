#!/usr/bin/env python3
"""
Test Remote Access - Diagnostica el acceso remoto al dashboard
"""

import socket
import subprocess
import sys

def test_remote_access():
    print("=== DIAGNÓSTICO DE ACCESO REMOTO ===")
    
    # 1. Verificar que el servidor esté funcionando localmente
    print("\n1. Probando acceso local...")
    try:
        import requests
        response = requests.get('http://127.0.0.1:5000', timeout=5)
        print(f"   [OK] Local access: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Local access failed: {e}")
        return
    
    # 2. Obtener IP local
    print("\n2. Detectando IP local...")
    try:
        # Crear socket para detectar IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"   [INFO] IP local detectada: {local_ip}")
    except Exception as e:
        print(f"   [ERROR] No se pudo detectar IP: {e}")
        local_ip = "192.168.1.155"  # Fallback
    
    # 3. Probar acceso desde IP local
    print(f"\n3. Probando acceso desde {local_ip}:5000...")
    try:
        response = requests.get(f'http://{local_ip}:5000', timeout=10)
        print(f"   [OK] Remote access works: {response.status_code}")
        return True
    except requests.exceptions.ConnectTimeout:
        print("   [ERROR] Connection timeout - posible problema de firewall")
    except requests.exceptions.ConnectionError as e:
        print(f"   [ERROR] Connection failed: {e}")
        print("   [INFO] Esto suele ser problema de firewall de Windows")
    except Exception as e:
        print(f"   [ERROR] Unexpected error: {e}")
    
    # 4. Sugerir soluciones
    print(f"\n=== SOLUCIONES SUGERIDAS ===")
    print("1. FIREWALL DE WINDOWS:")
    print("   - Ve a: Panel de Control > Sistema y Seguridad > Firewall de Windows")
    print("   - Clic en: 'Permitir una aplicación o característica a través del Firewall'")
    print("   - Busca: Python o añade puerto 5000")
    print()
    print("2. PRUEBA MANUAL:")
    print(f"   - URL para móvil: http://{local_ip}:5000")
    print("   - Asegúrate de estar en la misma WiFi")
    print()
    print("3. DESACTIVAR FIREWALL TEMPORALMENTE:")
    print("   - Panel de Control > Firewall > Activar o desactivar Firewall")
    print("   - Desactivar solo para probar, luego reactivar")
    
    return False

def create_firewall_instructions():
    print("\n=== INSTRUCCIONES DE FIREWALL ===")
    print("Copia y pega este comando en CMD como Administrador:")
    print('netsh advfirewall firewall add rule name="Python Trading" dir=in action=allow program="C:\\Python313\\python.exe" enable=yes')
    print()
    print("O este para el puerto específico:")
    print('netsh advfirewall firewall add rule name="Trading Port 5000" dir=in action=allow protocol=TCP localport=5000')

if __name__ == "__main__":
    if test_remote_access():
        print("\n[SUCCESS] ¡Acceso remoto funcionando!")
    else:
        create_firewall_instructions()