#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_openai_endpoint.py

Script para validar la conexión con el endpoint OpenAI-compatible.
NO ejecuta validación E2E completa, solo prueba la conectividad básica.
"""

import asyncio
import logging
from app.core.config import settings
from app.llm import OpenAIChatClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_simple_text_generation():
    """Prueba generación de texto simple."""
    print("\n" + "="*80)
    print("TEST 1: Generación de texto simple")
    print("="*80)
    
    try:
        client = OpenAIChatClient()
        
        prompt = "Di 'Hola, mundo!' en una sola línea."
        
        print(f"\n📝 Prompt: {prompt}")
        print("\n⏳ Enviando request...")
        
        response = await client.generate_text(prompt)
        
        print(f"\n✅ Respuesta recibida ({len(response)} caracteres):")
        print(f"📄 {response}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error("Error en test de texto simple", exc_info=True)
        return False


async def test_json_generation():
    """Prueba generación de JSON estructurado."""
    print("\n" + "="*80)
    print("TEST 2: Generación de JSON estructurado")
    print("="*80)
    
    try:
        client = OpenAIChatClient()
        
        prompt = """Genera un JSON con este formato exacto:
{
  "status": "ok",
  "message": "Test exitoso"
}

Devuelve SOLO el JSON, sin texto adicional."""
        
        print(f"\n📝 Prompt: Solicitud de JSON estructurado")
        print("\n⏳ Enviando request con format='json'...")
        
        response = await client.generate_text(prompt, format="json")
        
        print(f"\n✅ Respuesta recibida ({len(response)} caracteres):")
        print(f"📄 {response}")
        
        # Intentar parsear como JSON
        import json
        try:
            parsed = json.loads(response)
            print(f"\n✅ JSON válido parseado:")
            print(f"   status: {parsed.get('status')}")
            print(f"   message: {parsed.get('message')}")
        except json.JSONDecodeError as e:
            print(f"\n⚠️ La respuesta no es JSON válido: {e}")
            print("   (El endpoint puede no soportar response_format)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error("Error en test de JSON", exc_info=True)
        return False


async def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*80)
    print("VALIDACIÓN DE ENDPOINT OPENAI-COMPATIBLE")
    print("="*80)
    
    print(f"\n📋 Configuración:")
    print(f"   Base URL: {settings.openai_base_url}")
    print(f"   Model: {settings.openai_model}")
    print(f"   API Key: {settings.openai_api_key[:8]}...{settings.openai_api_key[-4:]}")
    
    results = []
    
    # Test 1: Texto simple
    result1 = await test_simple_text_generation()
    results.append(("Generación de texto simple", result1))
    
    # Test 2: JSON estructurado
    result2 = await test_json_generation()
    results.append(("Generación de JSON estructurado", result2))
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ VALIDACIÓN EXITOSA")
        print("El endpoint OpenAI-compatible está funcionando correctamente.")
    else:
        print("⚠️ VALIDACIÓN PARCIAL")
        print("Algunos tests fallaron. Revisar configuración o endpoint.")
    print("="*80 + "\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrumpido por el usuario")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        logger.error("Error fatal en validación", exc_info=True)
        exit(1)