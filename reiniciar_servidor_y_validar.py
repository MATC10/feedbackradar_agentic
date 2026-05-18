"""
Script para reiniciar el servidor FastAPI y ejecutar validación E2E.

IMPORTANTE: Este script debe ejecutarse DESPUÉS de haber detenido manualmente
el servidor FastAPI actual (CTRL+C en su terminal).
"""
import subprocess
import time
import sys
import requests
from pathlib import Path

def print_separator(title=""):
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)

def check_server_running():
    """Verifica si el servidor FastAPI está corriendo"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    print_separator("REINICIO Y VALIDACIÓN DE FASTAPI")
    
    # Verificar si el servidor ya está corriendo
    print("\n1. Verificando si el servidor FastAPI está corriendo...")
    if check_server_running():
        print("   ⚠️  El servidor FastAPI YA ESTÁ CORRIENDO")
        print("   ⚠️  Debes detenerlo manualmente (CTRL+C) antes de ejecutar este script")
        print("\n   Opciones:")
        print("   a) Detén el servidor actual y ejecuta este script de nuevo")
        print("   b) O simplemente ejecuta: python validacion_backend_e2e.py")
        sys.exit(1)
    else:
        print("   ✅ No hay servidor corriendo. Procediendo...")
    
    # Arrancar servidor en background
    print("\n2. Arrancando servidor FastAPI...")
    print("   Comando: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("\n   NOTA: Los logs del servidor aparecerán a continuación.")
    print("   IMPORTANTE: Busca la sección '🔧 CONFIGURACIÓN LLM' en los logs.")
    print_separator()
    
    try:
        # Arrancar servidor
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Esperar y mostrar logs hasta que el servidor esté listo
        print("\n📝 LOGS DE STARTUP:")
        print("-" * 80)
        
        startup_complete = False
        llm_config_found = False
        logs_captured = []
        
        for line in process.stdout:
            print(line, end='')
            logs_captured.append(line)
            
            # Detectar configuración LLM
            if "🔧 CONFIGURACIÓN LLM:" in line or "CHAT_LLM_PROVIDER:" in line or "Cliente LLM creado:" in line:
                llm_config_found = True
            
            # Detectar que el servidor está listo
            if "Application startup complete" in line or "Uvicorn running" in line:
                startup_complete = True
                break
        
        if not startup_complete:
            print("\n❌ El servidor no completó el startup correctamente")
            process.terminate()
            sys.exit(1)
        
        print("-" * 80)
        print("\n✅ Servidor iniciado correctamente")
        
        # Verificar que encontramos la configuración LLM
        if llm_config_found:
            print("✅ Configuración LLM detectada en los logs")
        else:
            print("⚠️  No se detectó la sección de configuración LLM en los logs")
        
        # Esperar un poco más para asegurar que el servidor está completamente listo
        print("\n3. Esperando 3 segundos para que el servidor esté completamente listo...")
        time.sleep(3)
        
        # Verificar que el servidor responde
        print("\n4. Verificando que el servidor responde...")
        if check_server_running():
            print("   ✅ Servidor respondiendo correctamente")
        else:
            print("   ❌ El servidor no responde")
            process.terminate()
            sys.exit(1)
        
        # Ejecutar validación E2E
        print_separator("EJECUTANDO VALIDACIÓN E2E")
        print("\n5. Ejecutando validación E2E...")
        print("   Comando: python validacion_backend_e2e.py")
        print("\n")
        
        validation_process = subprocess.run(
            [sys.executable, "validacion_backend_e2e.py"],
            capture_output=False
        )
        
        print_separator("FINALIZACIÓN")
        
        # Detener servidor
        print("\n6. Deteniendo servidor FastAPI...")
        process.terminate()
        process.wait(timeout=5)
        print("   ✅ Servidor detenido")
        
        # Resumen
        print("\n" + "=" * 80)
        print("  RESUMEN")
        print("=" * 80)
        print("\n✅ Proceso completado")
        print("\nRevisa los resultados de la validación E2E arriba.")
        print("\nSi necesitas arrancar el servidor manualmente:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        if 'process' in locals():
            process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()