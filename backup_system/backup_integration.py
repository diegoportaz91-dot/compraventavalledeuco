#!/usr/bin/env python3
"""
Integración del Sistema de Backup con la Aplicación Principal
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este módulo integra el sistema de backup con la aplicación Flask principal
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

class BackupIntegration:
    def __init__(self, app=None):
        """Inicializa la integración de backup"""
        self.app = app
        self.project_path = Path(__file__).parent.absolute()
        self.backup_enabled = True
        self.last_auto_backup = None
        self.auto_backup_interval = 6  # horas
        self.is_heroku = 'DYNO' in os.environ
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa la integración con la aplicación Flask"""
        self.app = app
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        # Verificar sistema al inicializar
        self.verify_backup_system()
        
        # Agregar rutas de backup a la aplicación
        self.register_backup_routes()
        
        # Iniciar monitoreo en segundo plano
        if self.backup_enabled:
            self.start_background_monitoring()
            # Ejecutar verificación inicial
            self.check_auto_backup()
    
    def on_app_start(self):
        """Se ejecuta al iniciar la aplicación"""
        logging.info("Sistema de backup integrado - Aplicación iniciada")
        
        # Verificar estado del sistema de backup
        self.verify_backup_system()
        
        # Ejecutar backup automático si es necesario
        self.check_auto_backup()
    
    def on_request_end(self, exception):
        """Se ejecuta al final de cada request"""
        # Verificar si necesita backup automático cada cierto tiempo
        if self.should_run_auto_backup():
            threading.Thread(target=self.run_auto_backup, daemon=True).start()
    
    def verify_backup_system(self):
        """Verifica que el sistema de backup esté funcionando"""
        try:
            backup_script = self.project_path / 'backup_system' / 'backup_system.py'
            if not backup_script.exists():
                # Intentar ruta alternativa
                backup_script = Path(__file__).parent / 'backup_system.py'
                if not backup_script.exists():
                    logging.warning("Sistema de backup no encontrado")
                    self.backup_enabled = False
                    return False
            
            # Verificar que las tareas programadas estén activas
            result = subprocess.run([
                sys.executable, str(self.project_path / 'backup_system' / 'backup_scheduler.py'), 'list'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logging.warning("Tareas de backup no están configuradas correctamente")
            
            logging.info("Sistema de backup verificado correctamente")
            return True
            
        except Exception as e:
            logging.error(f"Error verificando sistema de backup: {e}")
            self.backup_enabled = False
            return False
    
    def should_run_auto_backup(self):
        """Determina si debe ejecutar un backup automático"""
        if not self.backup_enabled:
            return False
        
        if self.last_auto_backup is None:
            return True
        
        time_since_backup = datetime.now() - self.last_auto_backup
        return time_since_backup.total_seconds() > (self.auto_backup_interval * 3600)
    
    def check_auto_backup(self):
        """Verifica si necesita ejecutar backup automático al iniciar"""
        if self.should_run_auto_backup():
            threading.Thread(target=self.run_auto_backup, daemon=True).start()
    
    def run_auto_backup(self):
        """Ejecuta backup automático en segundo plano"""
        try:
            logging.info("Ejecutando backup automático integrado")
            
            # En Heroku usar adaptador especial
            if self.is_heroku:
                from .heroku_backup_adapter import create_heroku_backup
                result_data = create_heroku_backup()
                
                if result_data['success']:
                    logging.info(f"Backup automático Heroku completado: {result_data['message']}")
                    self.last_auto_backup = datetime.now()
                else:
                    logging.warning(f"Backup automático Heroku con errores: {result_data['error']}")
                    self.last_auto_backup = datetime.now()
                return
            
            # Usar backup incremental para ser más rápido (solo local)
            result = subprocess.run([
                sys.executable, 
                str(Path(__file__).parent / 'incremental_backup.py'), 
                'backup'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logging.info("Backup automático completado exitosamente")
                self.last_auto_backup = datetime.now()
            else:
                logging.warning(f"Backup automático completado con advertencias: {result.stderr}")
                self.last_auto_backup = datetime.now()
                
        except subprocess.TimeoutExpired:
            logging.error("Backup automático excedió tiempo límite")
        except Exception as e:
            logging.error(f"Error en backup automático: {e}")
    
    def run_manual_backup(self):
        """Ejecuta backup manual desde la aplicación"""
        try:
            result = subprocess.run([
                sys.executable,
                str(Path(__file__).parent / 'backup_system.py'),
                'backup', 'manual'
            ], capture_output=True, text=True, timeout=300)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def get_backup_status(self):
        """Obtiene el estado actual del sistema de backup"""
        try:
            # En Heroku usar adaptador especial
            if self.is_heroku:
                from .heroku_backup_adapter import HerokuBackupAdapter
                adapter = HerokuBackupAdapter()
                heroku_status = adapter.get_backup_status()
                
                # Convertir a formato esperado
                status = 'healthy' if heroku_status['s3_configured'] else 'warning'
                if heroku_status['backup_count'] == 0:
                    status = 'no_backups'
                
                return {
                    'status': status,
                    'last_backup': heroku_status['last_backup'],
                    'backup_count': heroku_status['backup_count'],
                    'system_enabled': self.backup_enabled,
                    'platform': 'heroku',
                    's3_configured': heroku_status['s3_configured']
                }
            
            # Verificar último backup (solo local)
            backup_dirs = ['backups/daily', 'backups/weekly', 'backups/monthly', 'backups']
            latest_backup = None
            backup_count = 0
            
            for backup_dir in backup_dirs:
                backup_path = self.project_path / backup_dir
                if backup_path.exists():
                    for backup_file in backup_path.glob('*.zip'):
                        backup_count += 1
                        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        if latest_backup is None or file_time > latest_backup:
                            latest_backup = file_time
            
            # Calcular estado
            if latest_backup:
                hours_since = (datetime.now() - latest_backup).total_seconds() / 3600
                if hours_since < 26:
                    status = 'healthy'
                elif hours_since < 48:
                    status = 'warning'
                else:
                    status = 'critical'
            else:
                status = 'no_backups'
            
            return {
                'status': status,
                'last_backup': latest_backup,
                'backup_count': backup_count,
                'system_enabled': self.backup_enabled
            }
            
        except Exception as e:
            logging.error(f"Error obteniendo estado de backup: {e}")
            return {
                'status': 'error',
                'last_backup': None,
                'backup_count': 0,
                'system_enabled': False
            }
    
    def register_backup_routes(self):
        """Registra rutas de backup en la aplicación Flask"""
        
        @self.app.route('/admin/backup/status')
        def backup_status():
            """Endpoint para obtener estado del backup"""
            from flask import jsonify
            status = self.get_backup_status()
            return jsonify(status)
        
        @self.app.route('/admin/backup/run', methods=['POST'])
        def run_backup():
            """Endpoint para ejecutar backup manual"""
            from flask import jsonify, request
            
            # Verificar que sea admin (puedes agregar tu lógica de autenticación aquí)
            backup_type = request.json.get('type', 'manual') if request.is_json else 'manual'
            
            if backup_type == 'incremental':
                result = subprocess.run([
                    sys.executable,
                    str(Path(__file__).parent / 'incremental_backup.py'),
                    'backup'
                ], capture_output=True, text=True, timeout=300)
            else:
                result = self.run_manual_backup()
            
            return jsonify({
                'success': result.get('success', result.returncode == 0),
                'message': 'Backup ejecutado correctamente' if result.get('success', result.returncode == 0) else 'Error en backup',
                'output': result.get('output', result.stdout if hasattr(result, 'stdout') else ''),
                'error': result.get('error', result.stderr if hasattr(result, 'stderr') else None)
            })
        
        @self.app.route('/admin/backup/interface')
        def backup_interface():
            """Redirige a la interfaz web de backup"""
            from flask import redirect
            return redirect('http://localhost:5001')
    
    def start_background_monitoring(self):
        """Inicia monitoreo en segundo plano"""
        def monitor_loop():
            while True:
                try:
                    time.sleep(3600)  # Verificar cada hora
                    if self.should_run_auto_backup():
                        self.run_auto_backup()
                except Exception as e:
                    logging.error(f"Error en monitoreo de backup: {e}")
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info("Monitoreo de backup iniciado en segundo plano")
    
    def add_backup_context(self):
        """Agrega contexto de backup a las plantillas"""
        @self.app.context_processor
        def inject_backup_status():
            if self.backup_enabled:
                status = self.get_backup_status()
                return {
                    'backup_status': status['status'],
                    'backup_enabled': True,
                    'last_backup': status['last_backup']
                }
            return {
                'backup_enabled': False
            }

# Función de conveniencia para integrar fácilmente
def init_backup_system(app):
    """Inicializa el sistema de backup con una aplicación Flask"""
    backup_integration = BackupIntegration(app)
    backup_integration.add_backup_context()
    return backup_integration

# Middleware para aplicaciones existentes
class BackupMiddleware:
    def __init__(self, app):
        self.app = app
        self.backup_integration = BackupIntegration()
        
    def __call__(self, environ, start_response):
        # Ejecutar verificaciones antes de cada request
        if self.backup_integration.backup_enabled:
            if self.backup_integration.should_run_auto_backup():
                threading.Thread(
                    target=self.backup_integration.run_auto_backup, 
                    daemon=True
                ).start()
        
        return self.app(environ, start_response)

# Decorador para funciones que modifican datos críticos
def backup_on_change(func):
    """Decorador que ejecuta backup después de operaciones críticas"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Ejecutar backup incremental en segundo plano después de cambios importantes
        try:
            threading.Thread(
                target=lambda: subprocess.run([
                    sys.executable,
                    str(Path(__file__).parent / 'incremental_backup.py'),
                    'backup'
                ], capture_output=True, timeout=300),
                daemon=True
            ).start()
        except Exception as e:
            logging.warning(f"No se pudo ejecutar backup automático: {e}")
        
        return result
    return wrapper
