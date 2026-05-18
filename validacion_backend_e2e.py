"""
Script de validación end-to-end del backend de FeedbackRadar Agentic.

Este script valida:
1. Servicios Docker corriendo
2. Ingesta de CSV
3. Ejecución del workflow de análisis
4. Consulta de insights y actions
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def check_health():
    """Verifica el health check de la API."""
    print_section("1. HEALTH CHECK")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data.get("status") == "healthy"

def upload_csv():
    """Sube el CSV de validación."""
    print_section("2. INGESTA DE CSV")
    csv_path = Path("data/raw/validacion_real.csv")
    
    if not csv_path.exists():
        print(f"❌ Error: No se encuentra el archivo {csv_path}")
        return None
    
    with open(csv_path, 'rb') as f:
        files = {'files': ('validacion_real.csv', f, 'text/csv')}
        response = requests.post(f"{BASE_URL}/feedback/upload", files=files)
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def run_analysis():
    """Ejecuta el análisis de feedback."""
    print_section("3. EJECUCIÓN DEL WORKFLOW DE ANÁLISIS")
    
    # Payload para el análisis
    payload = {
        "limit": 100,
        "days": None  # Analizar todo el feedback
    }
    
    print("Ejecutando análisis... (esto puede tardar un par de minutos)")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/analysis/run", json=payload)
    
    execution_time = time.time() - start_time
    print(f"\nStatus: {response.status_code}")
    print(f"Tiempo de ejecución: {execution_time:.2f}s")
    
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def get_insights():
    """Obtiene los insights generados."""
    print_section("4. CONSULTA DE INSIGHTS")
    response = requests.get(f"{BASE_URL}/analysis/insights?limit=10")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Insights encontrados: {len(data)}")
    
    for i, insight in enumerate(data, 1):
        print(f"\n--- Insight {i} ---")
        print(f"ID: {insight.get('insight_id')}")
        print(f"Título: {insight.get('title', 'N/A')}")
        print(f"Categoría: {insight.get('category', 'N/A')}")
        print(f"Severidad: {insight.get('severity', 'N/A')}")
        print(f"Descripción: {insight.get('description', 'N/A')[:100]}...")
    
    return data

def get_actions():
    """Obtiene las acciones generadas."""
    print_section("5. CONSULTA DE ACTIONS")
    response = requests.get(f"{BASE_URL}/analysis/actions?limit=10")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Acciones encontradas: {len(data)}")
    
    for i, action in enumerate(data, 1):
        print(f"\n--- Acción {i} ---")
        print(f"ID: {action.get('action_id')}")
        print(f"Título: {action.get('title')}")
        print(f"Prioridad: {action.get('priority')}")
        print(f"Estado: {action.get('status')}")
        print(f"Descripción: {action.get('description', 'N/A')[:100]}...")
    
    return data

def main():
    """Ejecuta la validación completa."""
    print_section("VALIDACIÓN END-TO-END DE FEEDBACKRADAR AGENTIC")
    print("Fecha: 2026-05-13")
    print("Objetivo: Validar el backend completo antes de la Fase 5 (Streamlit)")
    
    results = {
        "health_check": False,
        "csv_upload": False,
        "analysis_run": False,
        "insights_retrieved": False,
        "actions_retrieved": False
    }
    
    try:
        # 1. Health Check
        results["health_check"] = check_health()
        if not results["health_check"]:
            print("❌ Health check falló. Verifica que los servicios estén corriendo.")
            return
        
        # 2. Upload CSV
        upload_result = upload_csv()
        if upload_result and upload_result.get("success"):
            results["csv_upload"] = True
            print(f"\n✅ CSV ingestado correctamente:")
            print(f"   - Filas válidas: {upload_result.get('valid_rows')}")
            print(f"   - Filas insertadas: {upload_result.get('inserted_rows')}")
            print(f"   - Filas indexadas: {upload_result.get('indexed_rows')}")
        else:
            print("\n❌ Error en la ingesta del CSV")
            return
        
        # 3. Run Analysis
        analysis_result = run_analysis()
        if analysis_result and analysis_result.get("success"):
            results["analysis_run"] = True
            print(f"\n✅ Análisis ejecutado correctamente:")
            print(f"   - Feedback analizado: {analysis_result.get('feedback_analyzed')}")
            print(f"   - Temas detectados: {analysis_result.get('themes_detected')}")
            print(f"   - Evidencias recuperadas: {analysis_result.get('evidence_count')}")
            print(f"   - Recomendaciones: {analysis_result.get('recommendations_generated')}")
            print(f"   - Actions creadas: {analysis_result.get('actions_created')}")
            print(f"   - Insights creados: {analysis_result.get('insights_created')}")
        else:
            print("\n⚠️ El análisis tuvo problemas")
            if analysis_result:
                errors = analysis_result.get("errors", [])
                for error in errors:
                    print(f"   - {error}")
        
        # 4. Get Insights
        insights = get_insights()
        if insights:
            results["insights_retrieved"] = True
            print(f"\n✅ Insights recuperados: {len(insights)}")
        
        # 5. Get Actions
        actions = get_actions()
        if actions:
            results["actions_retrieved"] = True
            print(f"\n✅ Actions recuperadas: {len(actions)}")
        
        # Resumen final
        print_section("RESUMEN DE VALIDACIÓN")
        for key, value in results.items():
            status = "✅" if value else "❌"
            print(f"{status} {key.replace('_', ' ').title()}: {'PASS' if value else 'FAIL'}")
        
        all_pass = all(results.values())
        print(f"\n{'='*80}")
        if all_pass:
            print("🎉 VALIDACIÓN END-TO-END COMPLETADA EXITOSAMENTE")
            print("✅ El backend está listo para la Fase 5 (Frontend Streamlit)")
        else:
            print("⚠️ VALIDACIÓN PARCIAL")
            print("Revisar los errores antes de continuar a la Fase 5")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error durante la validación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()