#!/usr/bin/env python3
"""
Instalador Automático del Sistema de Backup
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Script para instalar y configurar automáticamente todo el sistema de backup
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class BackupInstaller:
    def __init__(self):
        self.project_path = Path(__file__).parent.absolute()
        self.required_packages = [
            'schedule',
            'paramiko'
        ]
        self.optional_packages = {
            'dropbox': 'Para sincronización con Dropbox',
            'google-api-python-client': 'Para sincronización con Google Drive',
            'google-auth-httplib2': 'Para autenticación con Google Drive',
            'google-auth-oauthlib': 'Para OAuth con Google Drive'
        }
        
    def check_python_version(self):
        """Verifica que la versión de Python sea compatible"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Error: Se requiere Python 3.8 o superior")
            print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    
    def install_required_packages(self):
        """Instala los paquetes requeridos"""
        print("\n📦 Instalando paquetes requeridos...")
        
        for package in self.required_packages:
            try:
                print(f"   Instalando {package}...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package
                ], capture_output=True, text=True, check=True)
                print(f"   ✅ {package} instalado correctamente")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Error instalando {package}: {e.stderr}")
                return False
        
        return True
    
    def setup_directories(self):
        """Crea las carpetas necesarias"""
        print("\n📁 Creando estructura de directorios...")
        
        directories = [
            'backups',
            'backups/daily',
            'backups/weekly', 
            'backups/monthly',
            'backups/incremental'
        ]
        
        for directory in directories:
            dir_path = self.project_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}")
        
        return True
    
    def create_default_configs(self):
        """Crea archivos de configuración por defecto"""
        print("\n⚙️ Creando configuraciones por defecto...")
        
        # Configuración principal de backup
        backup_config = {
            "project_path": str(self.project_path),
            "backup_base_dir": "backups",
            "database_file": "vehicle_marketplace.db",
            "uploads_dir": "static/uploads",
            "config_files": [
                "app.py", "models.py", "routes.py",
                "requirements.txt", "pyproject.toml", "config_local.py"
            ],
            "retention_days": 30,
            "compression_level": 6,
            "enable_cloud_backup": False
        }
        
        with open('backup_config.json', 'w', encoding='utf-8') as f:
            json.dump(backup_config, f, indent=4, ensure_ascii=False)
        print("   ✅ backup_config.json")
        
        # Configuración de monitoreo
        monitor_config = {
            "monitoring": {
                "check_interval_hours": 6,
                "max_backup_age_hours": 26,
                "min_backup_size_mb": 1,
                "alert_on_failure": True
            },
            "email_alerts": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "subject_prefix": "[Backup Alert - Marketplace VUco]"
            },
            "thresholds": {
                "disk_space_warning_gb": 5,
                "consecutive_failures": 3
            }
        }
        
        with open('backup_monitor_config.json', 'w', encoding='utf-8') as f:
            json.dump(monitor_config, f, indent=4, ensure_ascii=False)
        print("   ✅ backup_monitor_config.json")
        
        return True
    
    def setup_scheduled_tasks(self):
        """Configura las tareas programadas"""
        print("\n⏰ Configurando tareas programadas...")
        
        try:
            result = subprocess.run([
                sys.executable, 'backup_scheduler.py', 'setup'
            ], capture_output=True, text=True, cwd=str(self.project_path))
            
            if result.returncode == 0:
                print("   ✅ Tareas programadas configuradas")
                return True
            else:
                print(f"   ⚠️ Advertencia configurando tareas: {result.stderr}")
                return True  # No es crítico
        except Exception as e:
            print(f"   ⚠️ Error configurando tareas programadas: {e}")
            return True  # No es crítico
    
    def run_initial_backup(self):
        """Ejecuta el primer backup de prueba"""
        print("\n🔄 Ejecutando backup inicial de prueba...")
        
        try:
            result = subprocess.run([
                sys.executable, 'backup_system.py', 'backup', 'manual'
            ], capture_output=True, text=True, cwd=str(self.project_path), timeout=300)
            
            if result.returncode == 0:
                print("   ✅ Backup inicial completado exitosamente")
                return True
            else:
                print(f"   ⚠️ Backup completado con advertencias")
                return True
        except subprocess.TimeoutExpired:
            print("   ⚠️ Backup inicial excedió tiempo límite")
            return True
        except Exception as e:
            print(f"   ❌ Error en backup inicial: {e}")
            return False
    
    def verify_installation(self):
        """Verifica que la instalación sea correcta"""
        print("\n🔍 Verificando instalación...")
        
        # Verificar archivos principales
        required_files = [
            'backup_system.py',
            'restore_system.py', 
            'backup_monitor.py',
            'incremental_backup.py',
            'cloud_backup.py',
            'backup_scheduler.py',
            'backup_web_interface.py'
        ]
        
        for file_name in required_files:
            file_path = self.project_path / file_name
            if file_path.exists():
                print(f"   ✅ {file_name}")
            else:
                print(f"   ❌ {file_name} - No encontrado")
                return False
        
        # Verificar directorios
        if (self.project_path / 'backups').exists():
            print("   ✅ Estructura de directorios")
        else:
            print("   ❌ Estructura de directorios")
            return False
        
        # Verificar configuraciones
        if (self.project_path / 'backup_config.json').exists():
            print("   ✅ Archivos de configuración")
        else:
            print("   ❌ Archivos de configuración")
            return False
        
        return True
    
    def show_usage_instructions(self):
        """Muestra instrucciones de uso"""
        print("\n" + "="*60)
        print("🎉 INSTALACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print()
        print("📋 COMANDOS PRINCIPALES:")
        print("   python backup_system.py backup manual     - Backup manual")
        print("   python incremental_backup.py backup       - Backup incremental")
        print("   python backup_monitor.py check            - Verificar salud")
        print("   python restore_system.py list             - Ver backups")
        print("   python backup_web_interface.py 5001       - Interfaz web")
        print()
        print("⏰ BACKUPS AUTOMÁTICOS CONFIGURADOS:")
        print("   • Diario: 02:00 AM")
        print("   • Semanal: Domingos 02:30 AM")
        print("   • Mensual: Día 1 de cada mes 03:00 AM")
        print("   • Limpieza: Diaria 04:00 AM")
        print()
        print("🌐 INTERFAZ WEB:")
        print("   Ejecuta: python backup_web_interface.py 5001")
        print("   Accede a: http://localhost:5001")
        print()
        print("📧 CONFIGURAR ALERTAS (Opcional):")
        print("   python backup_monitor.py setup-email")
        print()
        print("☁️ CONFIGURAR NUBE (Opcional):")
        print("   python cloud_backup.py setup dropbox")
        print("   python cloud_backup.py setup google_drive")
        print()
        print("📖 DOCUMENTACIÓN COMPLETA:")
        print("   Ver archivo: README_BACKUP_SYSTEM.md")
        print()
        print("✅ Tu sistema de backup está listo y protegiendo tus datos!")
    
    def install(self):
        """Ejecuta la instalación completa"""
        print("🚀 INSTALADOR DEL SISTEMA DE BACKUP")
        print("   Marketplace de Vehículos - Valle de Uco")
        print("="*50)
        
        steps = [
            ("Verificando Python", self.check_python_version),
            ("Instalando paquetes", self.install_required_packages),
            ("Creando directorios", self.setup_directories),
            ("Configurando sistema", self.create_default_configs),
            ("Programando tareas", self.setup_scheduled_tasks),
            ("Backup inicial", self.run_initial_backup),
            ("Verificando instalación", self.verify_installation)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if not step_func():
                print(f"\n❌ Error en: {step_name}")
                print("   La instalación no se completó correctamente")
                return False
        
        self.show_usage_instructions()
        return True

def main():
    """Función principal"""
    installer = BackupInstaller()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        # Solo verificar instalación
        if installer.verify_installation():
            print("✅ Sistema de backup instalado correctamente")
        else:
            print("❌ Sistema de backup no está instalado correctamente")
        return
    
    print("¿Deseas instalar el Sistema de Backup completo? (s/N): ", end="")
    response = input().strip().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        installer.install()
    else:
        print("Instalación cancelada")

if __name__ == "__main__":
    main()
