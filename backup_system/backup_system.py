#!/usr/bin/env python3
"""
Sistema de Backup Automatizado para Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script realiza backups completos de:
- Base de datos SQLite
- Imágenes de vehículos y gestores
- Archivos de configuración críticos
"""

import os
import sys
import shutil
import sqlite3
import zipfile
import datetime
import logging
import json
import hashlib
from pathlib import Path
import schedule
import time

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class BackupManager:
    def __init__(self, config_file='backup_config.json'):
        """Inicializa el gestor de backups"""
        self.config_file = config_file
        self.load_config()
        self.setup_directories()
        
    def load_config(self):
        """Carga la configuración desde archivo JSON"""
        default_config = {
            "project_path": os.path.dirname(os.path.abspath(__file__)),
            "backup_base_dir": "backups",
            "database_file": "vehicle_marketplace.db",
            "uploads_dir": "static/uploads",
            "config_files": [
                "app.py",
                "models.py", 
                "routes.py",
                "requirements.txt",
                "pyproject.toml",
                "config_local.py"
            ],
            "retention_days": 30,
            "compression_level": 6,
            "enable_cloud_backup": False,
            "cloud_provider": "none",
            "backup_schedule": {
                "daily": "02:00",
                "weekly": "sunday",
                "monthly": 1
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Error cargando configuración: {e}. Usando configuración por defecto.")
        
        self.config = default_config
        self.save_config()
        
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
    
    def setup_directories(self):
        """Crea las carpetas necesarias para backups"""
        self.backup_dir = Path(self.config['backup_base_dir'])
        self.daily_dir = self.backup_dir / 'daily'
        self.weekly_dir = self.backup_dir / 'weekly'
        self.monthly_dir = self.backup_dir / 'monthly'
        
        for directory in [self.backup_dir, self.daily_dir, self.weekly_dir, self.monthly_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
    def calculate_file_hash(self, file_path):
        """Calcula el hash SHA-256 de un archivo"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logging.error(f"Error calculando hash de {file_path}: {e}")
            return None
    
    def backup_database(self, backup_path):
        """Realiza backup de la base de datos SQLite"""
        db_path = Path(self.config['project_path']) / self.config['database_file']
        
        if not db_path.exists():
            logging.warning(f"Base de datos no encontrada: {db_path}")
            return False
            
        try:
            # Crear backup usando SQLite backup API (más seguro que copiar archivo)
            backup_db_path = backup_path / f"database_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            # Conectar a la base de datos original
            source_conn = sqlite3.connect(str(db_path))
            
            # Crear conexión al archivo de backup
            backup_conn = sqlite3.connect(str(backup_db_path))
            
            # Realizar backup usando la API de SQLite
            source_conn.backup(backup_conn)
            
            # Cerrar conexiones
            backup_conn.close()
            source_conn.close()
            
            # Verificar integridad del backup
            if self.verify_database_integrity(backup_db_path):
                logging.info(f"Backup de base de datos completado: {backup_db_path}")
                return True
            else:
                logging.error("Error en la verificación de integridad del backup de base de datos")
                return False
                
        except Exception as e:
            logging.error(f"Error en backup de base de datos: {e}")
            return False
    
    def verify_database_integrity(self, db_path):
        """Verifica la integridad de la base de datos"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception as e:
            logging.error(f"Error verificando integridad de {db_path}: {e}")
            return False
    
    def backup_uploads(self, backup_path):
        """Realiza backup de las imágenes y archivos subidos"""
        uploads_path = Path(self.config['project_path']) / self.config['uploads_dir']
        
        if not uploads_path.exists():
            logging.warning(f"Carpeta de uploads no encontrada: {uploads_path}")
            return False
            
        try:
            backup_uploads_path = backup_path / "uploads_backup"
            backup_uploads_path.mkdir(exist_ok=True)
            
            # Copiar toda la carpeta de uploads
            shutil.copytree(uploads_path, backup_uploads_path / "uploads", dirs_exist_ok=True)
            
            # Crear archivo de inventario con hashes
            inventory = {}
            for file_path in uploads_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(uploads_path)
                    file_hash = self.calculate_file_hash(file_path)
                    inventory[str(relative_path)] = {
                        'size': file_path.stat().st_size,
                        'modified': file_path.stat().st_mtime,
                        'hash': file_hash
                    }
            
            # Guardar inventario
            inventory_file = backup_uploads_path / "inventory.json"
            with open(inventory_file, 'w', encoding='utf-8') as f:
                json.dump(inventory, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Backup de uploads completado: {backup_uploads_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error en backup de uploads: {e}")
            return False
    
    def backup_config_files(self, backup_path):
        """Realiza backup de archivos de configuración críticos"""
        try:
            config_backup_path = backup_path / "config_backup"
            config_backup_path.mkdir(exist_ok=True)
            
            project_path = Path(self.config['project_path'])
            
            for config_file in self.config['config_files']:
                source_file = project_path / config_file
                if source_file.exists():
                    dest_file = config_backup_path / config_file
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, dest_file)
                    logging.info(f"Archivo de configuración respaldado: {config_file}")
                else:
                    logging.warning(f"Archivo de configuración no encontrado: {config_file}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error en backup de archivos de configuración: {e}")
            return False
    
    def create_backup_archive(self, backup_path, archive_name):
        """Crea un archivo comprimido del backup"""
        try:
            archive_path = backup_path.parent / f"{archive_name}.zip"
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=self.config['compression_level']) as zipf:
                
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_path)
                        zipf.write(file_path, arcname)
            
            # Eliminar carpeta temporal después de comprimir
            shutil.rmtree(backup_path)
            
            logging.info(f"Archivo de backup creado: {archive_path}")
            return archive_path
            
        except Exception as e:
            logging.error(f"Error creando archivo de backup: {e}")
            return None
    
    def create_backup_manifest(self, backup_info):
        """Crea un manifiesto con información del backup"""
        manifest = {
            'backup_date': backup_info['timestamp'],
            'backup_type': backup_info['type'],
            'files_backed_up': backup_info.get('files_count', 0),
            'total_size': backup_info.get('total_size', 0),
            'database_hash': backup_info.get('database_hash'),
            'success': backup_info.get('success', False),
            'errors': backup_info.get('errors', [])
        }
        
        manifest_file = backup_info['backup_path'].parent / f"{backup_info['archive_name']}_manifest.json"
        
        try:
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            logging.info(f"Manifiesto creado: {manifest_file}")
        except Exception as e:
            logging.error(f"Error creando manifiesto: {e}")
    
    def perform_backup(self, backup_type='manual'):
        """Realiza un backup completo"""
        timestamp = datetime.datetime.now()
        backup_name = f"backup_{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Determinar directorio según tipo de backup
        if backup_type == 'daily':
            target_dir = self.daily_dir
        elif backup_type == 'weekly':
            target_dir = self.weekly_dir
        elif backup_type == 'monthly':
            target_dir = self.monthly_dir
        else:
            target_dir = self.backup_dir
        
        backup_path = target_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Iniciando backup {backup_type}: {backup_name}")
        
        backup_info = {
            'timestamp': timestamp.isoformat(),
            'type': backup_type,
            'backup_path': backup_path,
            'archive_name': backup_name,
            'success': True,
            'errors': []
        }
        
        try:
            # Backup de base de datos
            if not self.backup_database(backup_path):
                backup_info['errors'].append("Error en backup de base de datos")
                backup_info['success'] = False
            
            # Backup de uploads
            if not self.backup_uploads(backup_path):
                backup_info['errors'].append("Error en backup de uploads")
                backup_info['success'] = False
            
            # Backup de archivos de configuración
            if not self.backup_config_files(backup_path):
                backup_info['errors'].append("Error en backup de configuración")
                backup_info['success'] = False
            
            # Crear archivo comprimido
            archive_path = self.create_backup_archive(backup_path, backup_name)
            if archive_path:
                backup_info['total_size'] = archive_path.stat().st_size
                backup_info['archive_path'] = str(archive_path)
            else:
                backup_info['errors'].append("Error creando archivo comprimido")
                backup_info['success'] = False
            
            # Crear manifiesto
            self.create_backup_manifest(backup_info)
            
            if backup_info['success']:
                logging.info(f"Backup {backup_type} completado exitosamente: {backup_name}")
            else:
                logging.error(f"Backup {backup_type} completado con errores: {backup_info['errors']}")
            
            return backup_info
            
        except Exception as e:
            logging.error(f"Error crítico durante backup: {e}")
            backup_info['success'] = False
            backup_info['errors'].append(f"Error crítico: {str(e)}")
            return backup_info
    
    def cleanup_old_backups(self):
        """Elimina backups antiguos según la política de retención"""
        retention_days = self.config['retention_days']
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        for backup_dir in [self.daily_dir, self.weekly_dir, self.monthly_dir]:
            try:
                for item in backup_dir.iterdir():
                    if item.is_file() and item.suffix == '.zip':
                        # Extraer fecha del nombre del archivo
                        try:
                            date_str = item.stem.split('_')[-2] + '_' + item.stem.split('_')[-1]
                            file_date = datetime.datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                            
                            if file_date < cutoff_date:
                                item.unlink()
                                # Eliminar manifiesto asociado
                                manifest_file = item.parent / f"{item.stem}_manifest.json"
                                if manifest_file.exists():
                                    manifest_file.unlink()
                                logging.info(f"Backup antiguo eliminado: {item}")
                                
                        except (ValueError, IndexError):
                            logging.warning(f"No se pudo parsear fecha del archivo: {item}")
                            
            except Exception as e:
                logging.error(f"Error limpiando backups antiguos en {backup_dir}: {e}")
    
    def schedule_backups(self):
        """Programa los backups automáticos"""
        # Backup diario
        daily_time = self.config['backup_schedule']['daily']
        schedule.every().day.at(daily_time).do(self.perform_backup, 'daily')
        
        # Backup semanal
        weekly_day = self.config['backup_schedule']['weekly']
        schedule.every().week.at(daily_time).do(self.perform_backup, 'weekly')
        
        # Backup mensual (primer día del mes)
        schedule.every().month.do(self.perform_backup, 'monthly')
        
        # Limpieza de backups antiguos (diaria)
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)
        
        logging.info("Backups programados:")
        logging.info(f"- Diario: {daily_time}")
        logging.info(f"- Semanal: {weekly_day} a las {daily_time}")
        logging.info(f"- Mensual: primer día del mes")
        logging.info("- Limpieza: diaria a las 03:00")
    
    def run_scheduler(self):
        """Ejecuta el programador de backups"""
        self.schedule_backups()
        
        logging.info("Sistema de backup iniciado. Presiona Ctrl+C para detener.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
        except KeyboardInterrupt:
            logging.info("Sistema de backup detenido por el usuario.")

def main():
    """Función principal"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        backup_manager = BackupManager()
        
        if command == 'backup':
            backup_type = sys.argv[2] if len(sys.argv) > 2 else 'manual'
            backup_manager.perform_backup(backup_type)
        elif command == 'schedule':
            backup_manager.run_scheduler()
        elif command == 'cleanup':
            backup_manager.cleanup_old_backups()
        else:
            print("Uso: python backup_system.py [backup|schedule|cleanup] [tipo]")
            print("Tipos de backup: manual, daily, weekly, monthly")
    else:
        # Ejecutar backup manual por defecto
        backup_manager = BackupManager()
        backup_manager.perform_backup('manual')

if __name__ == "__main__":
    main()
