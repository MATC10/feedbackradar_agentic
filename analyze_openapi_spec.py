#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analyze_openapi_spec.py

Analiza el OpenAPI spec para encontrar información sobre el header 'provider'.
"""

import asyncio
import httpx
import json
from app.core.config import settings

async def main():
    """Analiza el OpenAPI spec."""
    print("="*80)
    print("ANÁLISIS DEL OPENAPI SPEC")
    print("="*80)
    
    openapi_url = f"{settings.openai_base_url}/openapi.json"
    
    print(f"\n📥 Descargando: {openapi_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(openapi_url)
            
            if response.status_code != 200:
                print(f"❌ Error: Status {response.status_code}")
                return
            
            spec = response.json()
            print(f"✅ OpenAPI spec descargado: {len(json.dumps(spec))} caracteres")
            
            # Buscar información sobre el endpoint chat/completions
            print("\n" + "="*80)
            print("INFORMACIÓN DEL ENDPOINT /chat/completions")
            print("="*80)
            
            paths = spec.get("paths", {})
            chat_endpoint = None
            
            # Buscar el endpoint de chat completions
            for path, methods in paths.items():
                if "chat" in path.lower() and "completion" in path.lower():
                    print(f"\n📍 Encontrado: {path}")
                    chat_endpoint = methods
                    break
            
            if not chat_endpoint:
                print("\n⚠️ No se encontró endpoint de chat/completions")
                return
            
            # Analizar el método POST
            post_spec = chat_endpoint.get("post", {})
            
            if not post_spec:
                print("\n⚠️ No se encontró método POST")
                return
            
            print(f"\n📋 Descripción: {post_spec.get('summary', 'N/A')}")
            print(f"📋 Operation ID: {post_spec.get('operationId', 'N/A')}")
            
            # Analizar parámetros
            parameters = post_spec.get("parameters", [])
            
            print(f"\n📋 Parámetros ({len(parameters)}):")
            
            provider_param = None
            for param in parameters:
                param_name = param.get("name", "")
                param_in = param.get("in", "")
                param_required = param.get("required", False)
                param_schema = param.get("schema", {})
                param_desc = param.get("description", "")
                
                print(f"\n   • {param_name} ({param_in})")
                print(f"     Required: {param_required}")
                print(f"     Schema: {param_schema}")
                if param_desc:
                    print(f"     Description: {param_desc}")
                
                if param_name.lower() == "provider":
                    provider_param = param
            
            # Analizar el parámetro provider específicamente
            if provider_param:
                print("\n" + "="*80)
                print("🎯 PARÁMETRO 'provider' ENCONTRADO")
                print("="*80)
                
                print(f"\n{json.dumps(provider_param, indent=2, ensure_ascii=False)}")
                
                # Buscar enum o valores permitidos
                schema = provider_param.get("schema", {})
                
                if "enum" in schema:
                    print(f"\n✨ VALORES PERMITIDOS ENCONTRADOS:")
                    for value in schema["enum"]:
                        print(f"   → {value}")
                    
                    return schema["enum"]
                
                elif "anyOf" in schema or "oneOf" in schema:
                    options = schema.get("anyOf", schema.get("oneOf", []))
                    print(f"\n✨ OPCIONES ENCONTRADAS:")
                    for opt in options:
                        if "enum" in opt:
                            for value in opt["enum"]:
                                print(f"   → {value}")
                
                elif "$ref" in schema:
                    ref = schema["$ref"]
                    print(f"\n🔗 Referencia encontrada: {ref}")
                    
                    # Buscar la definición
                    ref_path = ref.split("/")
                    components = spec.get("components", {})
                    schemas = components.get("schemas", {})
                    
                    ref_name = ref_path[-1] if ref_path else None
                    if ref_name and ref_name in schemas:
                        ref_schema = schemas[ref_name]
                        print(f"\n📋 Definición de {ref_name}:")
                        print(json.dumps(ref_schema, indent=2, ensure_ascii=False)[:1000])
                        
                        if "enum" in ref_schema:
                            print(f"\n✨ VALORES PERMITIDOS EN REFERENCIA:")
                            for value in ref_schema["enum"]:
                                print(f"   → {value}")
                            return ref_schema["enum"]
            
            else:
                print("\n⚠️ No se encontró el parámetro 'provider' en la especificación")
                print("\nBuscando en schemas de componentes...")
                
                # Buscar en components/schemas
                components = spec.get("components", {})
                schemas = components.get("schemas", {})
                
                for schema_name, schema_def in schemas.items():
                    if "provider" in schema_name.lower():
                        print(f"\n📋 Schema relacionado encontrado: {schema_name}")
                        print(json.dumps(schema_def, indent=2, ensure_ascii=False)[:500])
                        
                        if "enum" in schema_def:
                            print(f"\n✨ VALORES PERMITIDOS:")
                            for value in schema_def["enum"]:
                                print(f"   → {value}")
                            return schema_def["enum"]
            
            print("\n❌ No se pudieron extraer los valores permitidos del OpenAPI spec")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print(f"\n\n✅ VALORES VÁLIDOS DE PROVIDER:")
        for value in result:
            print(f"   • {value}")
        print(f"\nPrueba con uno de estos valores en .env:")
        print(f"OPENAI_PROVIDER={result[0]}")