"""
Script de diagnóstico para verificar conectividad con Ollama
"""
import asyncio
import httpx
from app.core.config import settings

async def test_ollama_direct():
    """Test directo a Ollama"""
    print("=" * 80)
    print("DIAGNÓSTICO DE OLLAMA")
    print("=" * 80)
    
    print(f"\n1. Configuración actual:")
    print(f"   OLLAMA_BASE_URL: {settings.ollama_base_url}")
    print(f"   OLLAMA_CHAT_MODEL: {settings.ollama_chat_model}")
    print(f"   CHAT_LLM_PROVIDER: {settings.chat_llm_provider}")
    
    print(f"\n2. Test de conectividad a {settings.ollama_base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test 1: /api/tags
            print(f"\n   Test 1: GET {settings.ollama_base_url}/api/tags")
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            print(f"   ✅ Status: {response.status_code}")
            data = response.json()
            print(f"   ✅ Modelos disponibles: {len(data.get('models', []))}")
            for model in data.get('models', []):
                print(f"      - {model['name']}")
            
            # Test 2: /api/generate con prompt simple
            print(f"\n   Test 2: POST {settings.ollama_base_url}/api/generate")
            payload = {
                "model": settings.ollama_chat_model,
                "prompt": "Say 'hello' in one word",
                "stream": False
            }
            print(f"   Enviando prompt simple con timeout de 30s...")
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=30.0
            )
            print(f"   ✅ Status: {response.status_code}")
            result = response.json()
            generated = result.get('response', '')
            print(f"   ✅ Respuesta generada: '{generated[:100]}'")
            
            # Test 3: Prompt más largo (similar al de los agentes)
            print(f"\n   Test 3: POST con prompt más largo (similar a agentes)")
            long_prompt = """Eres un experto analista. Analiza este feedback:
1. El pago no funciona
2. La app es lenta
3. No puedo hacer login

Devuelve ÚNICAMENTE un JSON con este formato:
{
  "themes": [
    {"name": "Tema1", "description": "Descripción"}
  ]
}"""
            payload = {
                "model": settings.ollama_chat_model,
                "prompt": long_prompt,
                "stream": False,
                "format": "json"
            }
            print(f"   Enviando prompt largo con timeout de 60s...")
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=60.0
            )
            print(f"   ✅ Status: {response.status_code}")
            result = response.json()
            generated = result.get('response', '')
            print(f"   ✅ Respuesta generada ({len(generated)} chars): '{generated[:200]}'")
            
    except httpx.TimeoutException as e:
        print(f"   ❌ TIMEOUT: {e}")
    except httpx.ConnectError as e:
        print(f"   ❌ ERROR DE CONEXIÓN: {e}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_ollama_direct())