#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
inspect_openai_endpoint.py

Script para inspeccionar el endpoint OpenAI-compatible y descubrir
el valor correcto del header 'provider'.
"""

import asyncio
import httpx
import json
from app.core.config import settings

# Configurar timeout
TIMEOUT = 30.0

# Endpoint base
BASE_URL = settings.openai_base_url
API_KEY = settings.openai_api_key

# Enmascarar API key para logging
MASKED_KEY = f"{API_KEY[:8]}...{API_KEY[-4:]}" if len(API_KEY) > 12 else "***"


def print_section(title):
    """Imprime una sección separadora."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_response(response, max_body=500):
    """Imprime información de una respuesta HTTP de forma segura."""
    print(f"\n📊 Status: {response.status_code}")
    print(f"📋 Headers:")
    for key, value in response.headers.items():
        # No mostrar headers de autenticación completos
        if 'auth' in key.lower() or 'token' in key.lower():
            print(f"   {key}: ***")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n📄 Body (primeros {max_body} chars):")
    try:
        # Intentar parsear como JSON
        body = response.json()
        body_str = json.dumps(body, indent=2, ensure_ascii=False)
        print(body_str[:max_body])
        if len(body_str) > max_body:
            print(f"\n   ... ({len(body_str) - max_body} caracteres más)")
    except:
        # Si no es JSON, mostrar texto
        text = response.text
        print(text[:max_body])
        if len(text) > max_body:
            print(f"\n   ... ({len(text) - max_body} caracteres más)")


async def inspect_endpoint(url, method="GET", headers=None, json_body=None):
    """Inspecciona un endpoint de forma segura."""
    print(f"\n🔍 Inspeccionando: {method} {url}")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_body)
            else:
                print(f"⚠️ Método {method} no soportado")
                return None
            
            print_response(response)
            return response
            
    except httpx.TimeoutException:
        print(f"⏱️ Timeout después de {TIMEOUT}s")
        return None
    except httpx.ConnectError as e:
        print(f"❌ Error de conexión: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def main():
    """Ejecuta la inspección completa."""
    print_section("INSPECCIÓN DE ENDPOINT OPENAI-COMPATIBLE")
    
    print(f"\n📋 Configuración:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   API Key: {MASKED_KEY}")
    print(f"   Model: {settings.openai_model}")
    
    # Headers base
    base_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # ========================================================================
    # PASO 1: Endpoints de descubrimiento
    # ========================================================================
    
    print_section("PASO 1: Endpoints de Descubrimiento")
    
    # 1.1 Root del endpoint
    await inspect_endpoint(BASE_URL, headers=base_headers)
    
    # 1.2 Root con trailing slash
    await inspect_endpoint(f"{BASE_URL}/", headers=base_headers)
    
    # 1.3 Docs
    await inspect_endpoint(f"{BASE_URL}/docs", headers=base_headers)
    
    # 1.4 OpenAPI spec
    await inspect_endpoint(f"{BASE_URL}/openapi.json", headers=base_headers)
    
    # 1.5 Models endpoint
    await inspect_endpoint(f"{BASE_URL}/models", headers=base_headers)
    
    # 1.6 V1 Models
    await inspect_endpoint(f"{BASE_URL}/v1/models", headers=base_headers)
    
    # 1.7 Host raíz (sin /aigen)
    host_root = BASE_URL.rsplit('/aigen', 1)[0] if '/aigen' in BASE_URL else BASE_URL
    if host_root != BASE_URL:
        print(f"\n🔍 Probando host raíz: {host_root}")
        await inspect_endpoint(host_root, headers=base_headers)
        await inspect_endpoint(f"{host_root}/docs", headers=base_headers)
    
    # ========================================================================
    # PASO 2: Probar comportamiento del header 'provider'
    # ========================================================================
    
    print_section("PASO 2: Comportamiento del Header 'provider'")
    
    # Endpoint de chat completions
    chat_url = f"{BASE_URL}/chat/completions"
    
    # Payload mínimo
    test_payload = {
        "model": settings.openai_model,
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # 2.1 Sin header provider (solo con origin y origin-detail actuales)
    print("\n--- Test 2.1: Sin header 'provider' ---")
    headers_no_provider = {
        **base_headers,
        "origin": settings.openai_origin,
        "origin-detail": settings.openai_origin_detail
    }
    await inspect_endpoint(chat_url, method="POST", headers=headers_no_provider, json_body=test_payload)
    
    # 2.2 Con provider="openai" (actual, sabemos que falla)
    print("\n--- Test 2.2: Con provider='openai' (actual) ---")
    headers_with_openai = {
        **headers_no_provider,
        "provider": "openai"
    }
    await inspect_endpoint(chat_url, method="POST", headers=headers_with_openai, json_body=test_payload)
    
    # 2.3 Con provider vacío
    print("\n--- Test 2.3: Con provider='' (vacío) ---")
    headers_with_empty = {
        **headers_no_provider,
        "provider": ""
    }
    await inspect_endpoint(chat_url, method="POST", headers=headers_with_empty, json_body=test_payload)
    
    # 2.4 Probar valores comunes
    print("\n--- Test 2.4: Probando valores comunes ---")
    common_providers = ["gpt-5", "azure", "custom", "anthropic", "cohere", "mistral"]
    
    for provider_value in common_providers:
        print(f"\n🧪 Probando provider='{provider_value}'")
        headers_test = {
            **headers_no_provider,
            "provider": provider_value
        }
        response = await inspect_endpoint(chat_url, method="POST", headers=headers_test, json_body=test_payload)
        
        # Si obtenemos algo diferente a 400, es prometedor
        if response and response.status_code != 400:
            print(f"\n✨ ¡POSIBLE VALOR VÁLIDO! provider='{provider_value}' → Status {response.status_code}")
            if response.status_code == 200:
                print(f"✅ ¡ÉXITO! provider='{provider_value}' funciona correctamente")
                return provider_value
    
    # ========================================================================
    # PASO 3: Resumen
    # ========================================================================
    
    print_section("RESUMEN DE INSPECCIÓN")
    print("\n❌ No se pudo descubrir automáticamente el valor de 'provider'")
    print("\n📝 Información recopilada:")
    print("   - El endpoint requiere un header 'provider'")
    print("   - El valor 'openai' no es válido")
    print("   - No se encontró documentación expuesta en /docs o /openapi.json")
    print("   - Los valores comunes probados no funcionaron")
    
    print("\n📋 Dato exacto requerido:")
    print("   El proveedor del servicio debe proporcionar:")
    print("   → El valor válido del header 'provider' para este endpoint")
    print(f"   → Endpoint: {BASE_URL}")
    
    return None


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print(f"\n\n✅ PROVIDER DESCUBIERTO: {result}")
            print(f"\nActualizar .env con:")
            print(f"OPENAI_PROVIDER={result}")
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Inspección interrumpida por el usuario")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        exit(1)