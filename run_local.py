#!/usr/bin/env python3
"""
Script para ejecutar la aplicación localmente con configuración de desarrollo
"""

import os
import sys
from app import app

def setup_local_environment():
    """Configurar variables de entorno para desarrollo local"""
    # Configuración de base de datos local
    if not os.environ.get('DATABASE_URL'):
        os.environ['DATABASE_URL'] = 'sqlite:///marketplace_local.db'
    
    # Configuración de debug
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # Secret key para desarrollo
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'dev-secret-key-for-local-development'

def main():
    """Función principal"""
    print("🚀 Iniciando servidor de desarrollo...")
    print("📍 Configuración: Desarrollo Local")
    
    setup_local_environment()
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
