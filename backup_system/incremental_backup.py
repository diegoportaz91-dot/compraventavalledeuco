#!/usr/bin/env python3
"""
Sistema de Backup Incremental para Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script implementa backups incrementales para optimizar espacio y tiempo
"""

import os
import sys
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import zipfile

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('incremental_backup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class IncrementalBackupManager:
    def __init__(self, config_file='incremental_backup_config.json'):
        """Inicializa el gestor de backup incremental"""
        self.config_file = config_file
        self.load_config()
        self.state_file = 'backup_state.json'
        self.load_state()
        
    def load_config(self):
        """Carga la configuración del backup incremental"""
        default_config = {
            "project_path": os.path.dirname(os.path.abspath(__file__)),
            "backup_base_dir": "backups/incremental",
            "database_file": "vehicle_marketplace.db",
            "uploads_dir": "static/uploads",
            "config_files": [
                "app.py", "models.py", "routes.py", 
                "requirements.txt", "pyproject.toml", "config_local.py"
            ],
            "full_backup_interval_days": 7,
            "compression_level": 6,
            "max_incremental_chain": 10
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Error cargando configuración incremental: {e}")
        
        self.config = default_config
        self.save_config()
        
        # Crear directorio de backups incrementales
        Path(self.config['backup_base_dir']).mkdir(parents=True, exist_ok=True)
    
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración incremental: {e}")
    
    def load_state(self):
        """Carga el estado del último backup"""
        default_state = {
            "last_full_backup": None,
            "last_incremental_backup": None,
            "file_hashes": {},
            "incremental_count": 0,
            "backup_chain": []
        }
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
                    # Asegurar que todos los campos existen
                    for key, value in default_state.items():
                        if key not in self.state:
                            self.state[key] = value
            except Exception as e:
                logging.warning(f"Error cargando estado: {e}")
                self.state = default_state
        else:
            self.state = default_state
    
    def save_state(self):
        """Guarda el estado actual"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando estado: {e}")
    
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
    
    def get_database_changes(self):
        """Detecta cambios en la base de datos usando WAL"""
        db_path = Path(self.config['project_path']) / self.config['database_file']
        
        if not db_path.exists():
            return None
        
        try:
            # Verificar si hay cambios comparando timestamp y tamaño
            current_stat = db_path.stat()
            current_hash = self.calculate_file_hash(db_path)
            
            db_key = str(db_path)
            last_hash = self.state['file_hashes'].get(db_key)
            
            if current_hash != last_hash:
                return {
                    'path': db_path,
                    'hash': current_hash,
                    'size': current_stat.st_size,
                    'modified': current_stat.st_mtime,
                    'changed': True
                }
            
            return {
                'path': db_path,
                'hash': current_hash,
                'changed': False
            }
            
        except Exception as e:
            logging.error(f"Error verificando cambios en base de datos: {e}")
            return None
    
    def scan_file_changes(self):
        """Escanea cambios en archivos desde el último backup"""
        changed_files = []
        new_files = []
        deleted_files = []
        
        # Archivos a verificar
        files_to_check = []
        
        # Agregar archivos de configuración
        project_path = Path(self.config['project_path'])
        for config_file in self.config['config_files']:
            file_path = project_path / config_file
            if file_path.exists():
                files_to_check.append(file_path)
        
        # Agregar archivos de uploads
        uploads_path = project_path / self.config['uploads_dir']
        if uploads_path.exists():
            for file_path in uploads_path.rglob('*'):
                if file_path.is_file():
                    files_to_check.append(file_path)
        
        # Verificar cambios
        current_hashes = {}
        
        for file_path in files_to_check:
            try:
                current_hash = self.calculate_file_hash(file_path)
                if current_hash is None:
                    continue
                
                file_key = str(file_path.relative_to(project_path))
                current_hashes[file_key] = current_hash
                
                last_hash = self.state['file_hashes'].get(file_key)
                
                if last_hash is None:
                    # Archivo nuevo
                    new_files.append({
                        'path': file_path,
                        'relative_path': file_key,
                        'hash': current_hash,
                        'size': file_path.stat().st_size
                    })
                elif last_hash != current_hash:
                    # Archivo modificado
                    changed_files.append({
                        'path': file_path,
                        'relative_path': file_key,
                        'hash': current_hash,
                        'size': file_path.stat().st_size,
                        'old_hash': last_hash
                    })
                
            except Exception as e:
                logging.warning(f"Error procesando archivo {file_path}: {e}")
        
        # Detectar archivos eliminados
        for file_key in self.state['file_hashes']:
            if file_key not in current_hashes:
                deleted_files.append({
                    'relative_path': file_key,
                    'old_hash': self.state['file_hashes'][file_key]
                })
        
        return {
            'changed': changed_files,
            'new': new_files,
            'deleted': deleted_files,
            'current_hashes': current_hashes
        }
    
    def needs_full_backup(self):
        """Determina si se necesita un backup completo"""
        if self.state['last_full_backup'] is None:
            return True
        
        # Verificar intervalo de tiempo
        last_full = datetime.fromisoformat(self.state['last_full_backup'])
        days_since_full = (datetime.now() - last_full).days
        
        if days_since_full >= self.config['full_backup_interval_days']:
            return True
        
        # Verificar cadena de incrementales
        if self.state['incremental_count'] >= self.config['max_incremental_chain']:
            return True
        
        return False
    
    def create_full_backup(self):
        """Crea un backup completo"""
        timestamp = datetime.now()
        backup_name = f"full_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        backup_path = Path(self.config['backup_base_dir']) / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Creando backup completo: {backup_name}")
        
        try:
            # Backup de base de datos
            db_changes = self.get_database_changes()
            if db_changes and db_changes['path'].exists():
                db_backup_path = backup_path / "database"
                db_backup_path.mkdir(exist_ok=True)
                
                backup_db_file = db_backup_path / f"database_{timestamp.strftime('%Y%m%d_%H%M%S')}.db"
                
                # Usar SQLite backup API
                source_conn = sqlite3.connect(str(db_changes['path']))
                backup_conn = sqlite3.connect(str(backup_db_file))
                source_conn.backup(backup_conn)
                backup_conn.close()
                source_conn.close()
                
                logging.info(f"Base de datos respaldada: {backup_db_file}")
            
            # Backup de archivos
            file_changes = self.scan_file_changes()
            files_backup_path = backup_path / "files"
            files_backup_path.mkdir(exist_ok=True)
            
            all_files = file_changes['changed'] + file_changes['new']
            
            for file_info in all_files:
                source_file = file_info['path']
                relative_path = file_info['relative_path']
                dest_file = files_backup_path / relative_path
                
                # Crear directorio padre si no existe
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copiar archivo
                shutil.copy2(source_file, dest_file)
            
            # Crear manifiesto del backup completo
            manifest = {
                'type': 'full',
                'timestamp': timestamp.isoformat(),
                'files_count': len(all_files),
                'database_included': db_changes is not None and db_changes['path'].exists(),
                'file_hashes': file_changes['current_hashes'].copy()
            }
            
            # Incluir hash de base de datos si existe
            if db_changes and db_changes['changed']:
                manifest['file_hashes']['database'] = db_changes['hash']
            
            manifest_file = backup_path / "manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Comprimir backup
            archive_path = Path(self.config['backup_base_dir']) / f"{backup_name}.zip"
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=self.config['compression_level']) as zipf:
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_path)
                        zipf.write(file_path, arcname)
            
            # Limpiar carpeta temporal
            shutil.rmtree(backup_path)
            
            # Actualizar estado
            self.state['last_full_backup'] = timestamp.isoformat()
            self.state['file_hashes'] = file_changes['current_hashes'].copy()
            if db_changes and db_changes['changed']:
                self.state['file_hashes']['database'] = db_changes['hash']
            self.state['incremental_count'] = 0
            self.state['backup_chain'] = [str(archive_path)]
            self.save_state()
            
            logging.info(f"Backup completo creado: {archive_path}")
            return {
                'success': True,
                'backup_file': str(archive_path),
                'files_count': len(all_files),
                'size': archive_path.stat().st_size
            }
            
        except Exception as e:
            logging.error(f"Error creando backup completo: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_incremental_backup(self):
        """Crea un backup incremental"""
        timestamp = datetime.now()
        backup_name = f"incremental_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        backup_path = Path(self.config['backup_base_dir']) / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Creando backup incremental: {backup_name}")
        
        try:
            # Verificar cambios
            file_changes = self.scan_file_changes()
            db_changes = self.get_database_changes()
            
            total_changes = len(file_changes['changed']) + len(file_changes['new']) + len(file_changes['deleted'])
            db_changed = db_changes and db_changes.get('changed', False)
            
            if total_changes == 0 and not db_changed:
                logging.info("No hay cambios para backup incremental")
                shutil.rmtree(backup_path)
                return {
                    'success': True,
                    'no_changes': True,
                    'message': 'No hay cambios desde el último backup'
                }
            
            # Backup de base de datos si cambió
            if db_changed:
                db_backup_path = backup_path / "database"
                db_backup_path.mkdir(exist_ok=True)
                
                backup_db_file = db_backup_path / f"database_{timestamp.strftime('%Y%m%d_%H%M%S')}.db"
                
                source_conn = sqlite3.connect(str(db_changes['path']))
                backup_conn = sqlite3.connect(str(backup_db_file))
                source_conn.backup(backup_conn)
                backup_conn.close()
                source_conn.close()
                
                logging.info(f"Base de datos incremental respaldada: {backup_db_file}")
            
            # Backup de archivos cambiados y nuevos
            files_backup_path = backup_path / "files"
            files_backup_path.mkdir(exist_ok=True)
            
            changed_and_new = file_changes['changed'] + file_changes['new']
            
            for file_info in changed_and_new:
                source_file = file_info['path']
                relative_path = file_info['relative_path']
                dest_file = files_backup_path / relative_path
                
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest_file)
            
            # Crear manifiesto del backup incremental
            manifest = {
                'type': 'incremental',
                'timestamp': timestamp.isoformat(),
                'base_backup': self.state['backup_chain'][-1] if self.state['backup_chain'] else None,
                'files_changed': len(file_changes['changed']),
                'files_new': len(file_changes['new']),
                'files_deleted': len(file_changes['deleted']),
                'database_changed': db_changed,
                'changed_files': [f['relative_path'] for f in file_changes['changed']],
                'new_files': [f['relative_path'] for f in file_changes['new']],
                'deleted_files': [f['relative_path'] for f in file_changes['deleted']],
                'file_hashes': {}
            }
            
            # Agregar hashes de archivos cambiados
            for file_info in changed_and_new:
                manifest['file_hashes'][file_info['relative_path']] = file_info['hash']
            
            if db_changed:
                manifest['file_hashes']['database'] = db_changes['hash']
            
            manifest_file = backup_path / "manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Comprimir backup
            archive_path = Path(self.config['backup_base_dir']) / f"{backup_name}.zip"
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED,
                               compresslevel=self.config['compression_level']) as zipf:
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_path)
                        zipf.write(file_path, arcname)
            
            # Limpiar carpeta temporal
            shutil.rmtree(backup_path)
            
            # Actualizar estado
            self.state['last_incremental_backup'] = timestamp.isoformat()
            
            # Actualizar hashes de archivos
            for file_info in changed_and_new:
                self.state['file_hashes'][file_info['relative_path']] = file_info['hash']
            
            # Eliminar archivos borrados del estado
            for file_info in file_changes['deleted']:
                if file_info['relative_path'] in self.state['file_hashes']:
                    del self.state['file_hashes'][file_info['relative_path']]
            
            if db_changed:
                self.state['file_hashes']['database'] = db_changes['hash']
            
            self.state['incremental_count'] += 1
            self.state['backup_chain'].append(str(archive_path))
            self.save_state()
            
            logging.info(f"Backup incremental creado: {archive_path}")
            return {
                'success': True,
                'backup_file': str(archive_path),
                'files_changed': len(file_changes['changed']),
                'files_new': len(file_changes['new']),
                'files_deleted': len(file_changes['deleted']),
                'database_changed': db_changed,
                'size': archive_path.stat().st_size
            }
            
        except Exception as e:
            logging.error(f"Error creando backup incremental: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def perform_backup(self):
        """Ejecuta backup (completo o incremental según sea necesario)"""
        if self.needs_full_backup():
            logging.info("Ejecutando backup completo")
            return self.create_full_backup()
        else:
            logging.info("Ejecutando backup incremental")
            return self.create_incremental_backup()
    
    def list_backup_chain(self):
        """Lista la cadena de backups actual"""
        if not self.state['backup_chain']:
            print("No hay cadena de backups")
            return
        
        print("\nCadena de backups actual:")
        print("-" * 50)
        
        for i, backup_file in enumerate(self.state['backup_chain']):
            backup_path = Path(backup_file)
            if backup_path.exists():
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                backup_type = "Completo" if i == 0 else "Incremental"
                print(f"{i+1}. {backup_type}: {backup_path.name} ({size_mb:.1f} MB)")
            else:
                print(f"{i+1}. ❌ Archivo no encontrado: {backup_path.name}")
        
        print(f"\nTotal de backups en cadena: {len(self.state['backup_chain'])}")
        print(f"Último backup completo: {self.state['last_full_backup']}")
        print(f"Último backup incremental: {self.state['last_incremental_backup']}")

def main():
    """Función principal"""
    manager = IncrementalBackupManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'backup':
            result = manager.perform_backup()
            if result['success']:
                if result.get('no_changes'):
                    print(f"OK {result['message']}")
                else:
                    print(f"OK Backup creado: {result['backup_file']}")
                    print(f"   Tamaño: {result['size'] / (1024*1024):.1f} MB")
            else:
                print(f"ERROR: {result['error']}")
        
        elif command == 'full':
            result = manager.create_full_backup()
            if result['success']:
                print(f"OK Backup completo creado: {result['backup_file']}")
                print(f"   Archivos: {result['files_count']}")
                print(f"   Tamaño: {result['size'] / (1024*1024):.1f} MB")
            else:
                print(f"ERROR: {result['error']}")
        
        elif command == 'incremental':
            result = manager.create_incremental_backup()
            if result['success']:
                if result.get('no_changes'):
                    print(f"OK {result['message']}")
                else:
                    print(f"OK Backup incremental creado: {result['backup_file']}")
                    print(f"   Archivos cambiados: {result['files_changed']}")
                    print(f"   Archivos nuevos: {result['files_new']}")
                    print(f"   Archivos eliminados: {result['files_deleted']}")
                    print(f"   Base de datos cambiada: {'Sí' if result['database_changed'] else 'No'}")
                    print(f"   Tamaño: {result['size'] / (1024*1024):.1f} MB")
            else:
                print(f"ERROR: {result['error']}")
        
        elif command == 'list':
            manager.list_backup_chain()
        
        elif command == 'status':
            print(f"Último backup completo: {manager.state['last_full_backup']}")
            print(f"Último backup incremental: {manager.state['last_incremental_backup']}")
            print(f"Backups incrementales en cadena: {manager.state['incremental_count']}")
            print(f"¿Necesita backup completo?: {'Sí' if manager.needs_full_backup() else 'No'}")
        
        else:
            print("Comandos disponibles:")
            print("  backup      - Backup automático (completo o incremental)")
            print("  full        - Forzar backup completo")
            print("  incremental - Forzar backup incremental")
            print("  list        - Listar cadena de backups")
            print("  status      - Ver estado del sistema")
    
    else:
        print("Sistema de Backup Incremental")
        print("Uso: python incremental_backup.py <comando>")
        print("\nComandos:")
        print("  backup      - Ejecutar backup inteligente")
        print("  full        - Backup completo")
        print("  incremental - Backup incremental")
        print("  list        - Ver backups")
        print("  status      - Ver estado")

if __name__ == "__main__":
    main()
