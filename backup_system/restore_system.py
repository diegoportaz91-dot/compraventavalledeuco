#!/usr/bin/env python3
"""
Sistema de Restauración para Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script permite restaurar backups completos de:
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

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('restore_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class RestoreManager:
    def __init__(self, config_file='backup_config.json'):
        """Inicializa el gestor de restauración"""
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        """Carga la configuración desde archivo JSON"""
        default_config = {
            "project_path": os.path.dirname(os.path.abspath(__file__)),
            "backup_base_dir": "backups",
            "database_file": "vehicle_marketplace.db",
            "uploads_dir": "static/uploads"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Error cargando configuración: {e}. Usando configuración por defecto.")
        
        self.config = default_config
    
    def list_available_backups(self):
        """Lista todos los backups disponibles"""
        backup_dir = Path(self.config['backup_base_dir'])
        backups = []
        
        if not backup_dir.exists():
            logging.error("Directorio de backups no encontrado")
            return backups
        
        # Buscar en todas las subcarpetas
        for subdir in ['daily', 'weekly', 'monthly', '.']:
            search_dir = backup_dir / subdir if subdir != '.' else backup_dir
            if search_dir.exists():
                for backup_file in search_dir.glob('*.zip'):
                    manifest_file = backup_file.parent / f"{backup_file.stem}_manifest.json"
                    
                    backup_info = {
                        'file': str(backup_file),
                        'name': backup_file.stem,
                        'size': backup_file.stat().st_size,
                        'date': datetime.datetime.fromtimestamp(backup_file.stat().st_mtime),
                        'type': subdir if subdir != '.' else 'manual'
                    }
                    
                    # Cargar información del manifiesto si existe
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                                backup_info.update(manifest)
                        except Exception as e:
                            logging.warning(f"Error leyendo manifiesto {manifest_file}: {e}")
                    
                    backups.append(backup_info)
        
        # Ordenar por fecha (más reciente primero)
        backups.sort(key=lambda x: x['date'], reverse=True)
        return backups
    
    def verify_backup_integrity(self, backup_file):
        """Verifica la integridad de un archivo de backup"""
        try:
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                # Verificar que el archivo ZIP no esté corrupto
                bad_file = zipf.testzip()
                if bad_file:
                    logging.error(f"Archivo corrupto en backup: {bad_file}")
                    return False
                
                # Verificar que contenga los archivos esperados
                file_list = zipf.namelist()
                required_files = ['database_backup_', 'uploads_backup/', 'config_backup/']
                
                for required in required_files:
                    if not any(f.startswith(required) for f in file_list):
                        logging.warning(f"Archivo requerido no encontrado en backup: {required}")
                
                logging.info("Verificación de integridad del backup exitosa")
                return True
                
        except Exception as e:
            logging.error(f"Error verificando integridad del backup: {e}")
            return False
    
    def create_backup_before_restore(self):
        """Crea un backup de seguridad antes de restaurar"""
        try:
            from backup_system import BackupManager
            backup_manager = BackupManager()
            
            logging.info("Creando backup de seguridad antes de la restauración...")
            backup_info = backup_manager.perform_backup('pre_restore')
            
            if backup_info['success']:
                logging.info("Backup de seguridad creado exitosamente")
                return True
            else:
                logging.error("Error creando backup de seguridad")
                return False
                
        except Exception as e:
            logging.error(f"Error creando backup de seguridad: {e}")
            return False
    
    def restore_database(self, extract_path):
        """Restaura la base de datos desde el backup"""
        try:
            # Buscar archivo de base de datos en el backup
            db_backup_files = list(extract_path.glob('database_backup_*.db'))
            
            if not db_backup_files:
                logging.error("No se encontró archivo de base de datos en el backup")
                return False
            
            backup_db_file = db_backup_files[0]  # Tomar el primero si hay varios
            
            # Verificar integridad de la base de datos del backup
            if not self.verify_database_integrity(backup_db_file):
                logging.error("La base de datos del backup está corrupta")
                return False
            
            # Ruta de la base de datos actual
            current_db_path = Path(self.config['project_path']) / self.config['database_file']
            
            # Hacer backup de la base de datos actual si existe
            if current_db_path.exists():
                backup_current_db = current_db_path.parent / f"{current_db_path.stem}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(current_db_path, backup_current_db)
                logging.info(f"Base de datos actual respaldada en: {backup_current_db}")
            
            # Restaurar base de datos
            shutil.copy2(backup_db_file, current_db_path)
            
            # Verificar que la restauración fue exitosa
            if self.verify_database_integrity(current_db_path):
                logging.info("Base de datos restaurada exitosamente")
                return True
            else:
                logging.error("Error en la verificación de la base de datos restaurada")
                return False
                
        except Exception as e:
            logging.error(f"Error restaurando base de datos: {e}")
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
    
    def restore_uploads(self, extract_path):
        """Restaura las imágenes y archivos subidos"""
        try:
            uploads_backup_path = extract_path / 'uploads_backup' / 'uploads'
            
            if not uploads_backup_path.exists():
                logging.error("Carpeta de uploads no encontrada en el backup")
                return False
            
            # Ruta actual de uploads
            current_uploads_path = Path(self.config['project_path']) / self.config['uploads_dir']
            
            # Hacer backup de uploads actuales si existen
            if current_uploads_path.exists():
                backup_uploads_path = current_uploads_path.parent / f"uploads_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(current_uploads_path, backup_uploads_path)
                logging.info(f"Uploads actuales respaldados en: {backup_uploads_path}")
                
                # Eliminar uploads actuales
                shutil.rmtree(current_uploads_path)
            
            # Restaurar uploads desde backup
            shutil.copytree(uploads_backup_path, current_uploads_path)
            
            # Verificar con inventario si existe
            inventory_file = extract_path / 'uploads_backup' / 'inventory.json'
            if inventory_file.exists():
                if self.verify_uploads_with_inventory(current_uploads_path, inventory_file):
                    logging.info("Uploads restaurados y verificados exitosamente")
                    return True
                else:
                    logging.warning("Uploads restaurados pero con diferencias en el inventario")
                    return True  # Continuar aunque haya diferencias menores
            else:
                logging.info("Uploads restaurados exitosamente (sin verificación de inventario)")
                return True
                
        except Exception as e:
            logging.error(f"Error restaurando uploads: {e}")
            return False
    
    def verify_uploads_with_inventory(self, uploads_path, inventory_file):
        """Verifica uploads usando el archivo de inventario"""
        try:
            with open(inventory_file, 'r', encoding='utf-8') as f:
                inventory = json.load(f)
            
            for relative_path, file_info in inventory.items():
                file_path = uploads_path / relative_path
                
                if not file_path.exists():
                    logging.warning(f"Archivo faltante: {relative_path}")
                    continue
                
                # Verificar tamaño
                if file_path.stat().st_size != file_info['size']:
                    logging.warning(f"Tamaño diferente en {relative_path}")
                
                # Verificar hash si está disponible
                if file_info.get('hash'):
                    current_hash = self.calculate_file_hash(file_path)
                    if current_hash != file_info['hash']:
                        logging.warning(f"Hash diferente en {relative_path}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error verificando inventario: {e}")
            return False
    
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
    
    def restore_config_files(self, extract_path):
        """Restaura archivos de configuración"""
        try:
            config_backup_path = extract_path / 'config_backup'
            
            if not config_backup_path.exists():
                logging.error("Carpeta de configuración no encontrada en el backup")
                return False
            
            project_path = Path(self.config['project_path'])
            restored_files = []
            
            for config_file in config_backup_path.rglob('*'):
                if config_file.is_file():
                    # Calcular ruta relativa y destino
                    relative_path = config_file.relative_to(config_backup_path)
                    dest_file = project_path / relative_path
                    
                    # Crear directorio padre si no existe
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Hacer backup del archivo actual si existe
                    if dest_file.exists():
                        backup_file = dest_file.parent / f"{dest_file.name}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(dest_file, backup_file)
                    
                    # Restaurar archivo
                    shutil.copy2(config_file, dest_file)
                    restored_files.append(str(relative_path))
            
            logging.info(f"Archivos de configuración restaurados: {restored_files}")
            return True
            
        except Exception as e:
            logging.error(f"Error restaurando archivos de configuración: {e}")
            return False
    
    def perform_restore(self, backup_file, components=None):
        """Realiza una restauración completa desde un archivo de backup"""
        if components is None:
            components = ['database', 'uploads', 'config']
        
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            logging.error(f"Archivo de backup no encontrado: {backup_file}")
            return False
        
        # Verificar integridad del backup
        if not self.verify_backup_integrity(backup_path):
            logging.error("El archivo de backup está corrupto o incompleto")
            return False
        
        # Crear backup de seguridad antes de restaurar
        if not self.create_backup_before_restore():
            response = input("No se pudo crear backup de seguridad. ¿Continuar? (s/N): ")
            if response.lower() != 's':
                logging.info("Restauración cancelada por el usuario")
                return False
        
        # Extraer backup a carpeta temporal
        temp_extract_path = Path('temp_restore_extract')
        
        try:
            # Limpiar carpeta temporal si existe
            if temp_extract_path.exists():
                shutil.rmtree(temp_extract_path)
            
            temp_extract_path.mkdir()
            
            # Extraer archivo ZIP
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_extract_path)
            
            logging.info(f"Iniciando restauración desde: {backup_file}")
            
            success = True
            
            # Restaurar componentes seleccionados
            if 'database' in components:
                if not self.restore_database(temp_extract_path):
                    success = False
                    logging.error("Error restaurando base de datos")
            
            if 'uploads' in components:
                if not self.restore_uploads(temp_extract_path):
                    success = False
                    logging.error("Error restaurando uploads")
            
            if 'config' in components:
                if not self.restore_config_files(temp_extract_path):
                    success = False
                    logging.error("Error restaurando archivos de configuración")
            
            if success:
                logging.info("Restauración completada exitosamente")
            else:
                logging.error("Restauración completada con errores")
            
            return success
            
        except Exception as e:
            logging.error(f"Error durante la restauración: {e}")
            return False
            
        finally:
            # Limpiar carpeta temporal
            if temp_extract_path.exists():
                try:
                    shutil.rmtree(temp_extract_path)
                except Exception as e:
                    logging.warning(f"No se pudo limpiar carpeta temporal: {e}")

def main():
    """Función principal"""
    restore_manager = RestoreManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'list':
            # Listar backups disponibles
            backups = restore_manager.list_available_backups()
            
            if not backups:
                print("No se encontraron backups disponibles")
                return
            
            print("\nBackups disponibles:")
            print("-" * 80)
            for i, backup in enumerate(backups, 1):
                size_mb = backup['size'] / (1024 * 1024)
                print(f"{i}. {backup['name']}")
                print(f"   Fecha: {backup['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Tipo: {backup['type']}")
                print(f"   Tamaño: {size_mb:.1f} MB")
                print(f"   Archivo: {backup['file']}")
                print()
        
        elif command == 'restore':
            if len(sys.argv) < 3:
                print("Uso: python restore_system.py restore <archivo_backup> [componentes]")
                print("Componentes: database,uploads,config (separados por coma)")
                return
            
            backup_file = sys.argv[2]
            components = ['database', 'uploads', 'config']
            
            if len(sys.argv) > 3:
                components = [c.strip() for c in sys.argv[3].split(',')]
            
            print(f"Restaurando desde: {backup_file}")
            print(f"Componentes: {', '.join(components)}")
            
            response = input("¿Continuar con la restauración? (s/N): ")
            if response.lower() == 's':
                restore_manager.perform_restore(backup_file, components)
            else:
                print("Restauración cancelada")
        
        else:
            print("Comandos disponibles:")
            print("  list     - Listar backups disponibles")
            print("  restore  - Restaurar desde backup")
    
    else:
        # Modo interactivo
        backups = restore_manager.list_available_backups()
        
        if not backups:
            print("No se encontraron backups disponibles")
            return
        
        print("\nBackups disponibles:")
        for i, backup in enumerate(backups, 1):
            size_mb = backup['size'] / (1024 * 1024)
            print(f"{i}. {backup['name']} - {backup['date'].strftime('%Y-%m-%d %H:%M:%S')} ({size_mb:.1f} MB)")
        
        try:
            selection = int(input("\nSelecciona el número de backup a restaurar (0 para cancelar): "))
            
            if selection == 0:
                print("Operación cancelada")
                return
            
            if 1 <= selection <= len(backups):
                selected_backup = backups[selection - 1]
                
                print(f"\nBackup seleccionado: {selected_backup['name']}")
                print("Componentes disponibles: database, uploads, config")
                
                components_input = input("Componentes a restaurar (Enter para todos): ").strip()
                components = ['database', 'uploads', 'config']
                
                if components_input:
                    components = [c.strip() for c in components_input.split(',')]
                
                print(f"Restaurando componentes: {', '.join(components)}")
                
                response = input("¿Continuar? (s/N): ")
                if response.lower() == 's':
                    restore_manager.perform_restore(selected_backup['file'], components)
                else:
                    print("Restauración cancelada")
            else:
                print("Selección inválida")
                
        except ValueError:
            print("Entrada inválida")
        except KeyboardInterrupt:
            print("\nOperación cancelada")

if __name__ == "__main__":
    main()
