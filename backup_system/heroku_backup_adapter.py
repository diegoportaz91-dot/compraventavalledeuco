#!/usr/bin/env python3
"""
Adaptador del Sistema de Backup para Heroku
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este módulo adapta el sistema de backup para funcionar en Heroku con sus limitaciones
"""

import os
import sys
import logging
import tempfile
import boto3
from pathlib import Path
from datetime import datetime
import subprocess
import zipfile
import json

class HerokuBackupAdapter:
    def __init__(self):
        """Inicializa el adaptador para Heroku"""
        self.is_heroku = 'DYNO' in os.environ
        self.temp_dir = Path(tempfile.gettempdir()) / 'backup_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # Configuración de S3 para Heroku
        self.s3_bucket = os.environ.get('S3_BACKUP_BUCKET')
        self.aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        
        if self.is_heroku and self.s3_bucket:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
        else:
            self.s3_client = None
    
    def create_heroku_backup(self):
        """Crea backup adaptado para Heroku"""
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'heroku_backup',
                'database_url': os.environ.get('DATABASE_URL', ''),
                'files': []
            }
            
            # Crear backup de base de datos usando pg_dump si es PostgreSQL
            if 'postgres' in backup_data['database_url']:
                db_backup = self.backup_postgres_database()
                if db_backup:
                    backup_data['files'].append(db_backup)
            
            # Backup de archivos críticos (solo configuración, no uploads en Heroku)
            config_backup = self.backup_config_files()
            if config_backup:
                backup_data['files'].extend(config_backup)
            
            # Crear archivo ZIP del backup
            backup_file = self.create_backup_zip(backup_data)
            
            # Subir a S3 si está configurado
            if self.s3_client and backup_file:
                s3_key = f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}_heroku_backup.zip"
                self.upload_to_s3(backup_file, s3_key)
                
                return {
                    'success': True,
                    'backup_file': s3_key,
                    'location': 'S3',
                    'size': backup_file.stat().st_size,
                    'message': 'Backup creado y subido a S3 exitosamente'
                }
            
            return {
                'success': True,
                'backup_file': str(backup_file),
                'location': 'local_temp',
                'size': backup_file.stat().st_size,
                'message': 'Backup creado localmente (temporal en Heroku)'
            }
            
        except Exception as e:
            logging.error(f"Error en backup de Heroku: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_postgres_database(self):
        """Backup de base de datos PostgreSQL usando pg_dump"""
        try:
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                return None
            
            # Heroku requiere usar pg_dump con la URL completa
            dump_file = self.temp_dir / f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # Ejecutar pg_dump
            result = subprocess.run([
                'pg_dump', 
                database_url,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '-f', str(dump_file)
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and dump_file.exists():
                return {
                    'type': 'database',
                    'file': str(dump_file),
                    'size': dump_file.stat().st_size
                }
            else:
                logging.warning(f"pg_dump falló: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Error en backup de PostgreSQL: {e}")
            return None
    
    def backup_config_files(self):
        """Backup de archivos de configuración críticos"""
        config_files = [
            'app.py',
            'models.py', 
            'routes.py',
            'requirements.txt',
            'Procfile',
            'runtime.txt'
        ]
        
        backed_files = []
        
        for file_name in config_files:
            file_path = Path(file_name)
            if file_path.exists():
                # Copiar a directorio temporal
                temp_file = self.temp_dir / file_name
                temp_file.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
                
                backed_files.append({
                    'type': 'config',
                    'file': str(temp_file),
                    'original': file_name,
                    'size': temp_file.stat().st_size
                })
        
        return backed_files
    
    def create_backup_zip(self, backup_data):
        """Crea archivo ZIP con todos los backups"""
        zip_file = self.temp_dir / f"heroku_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Agregar manifest
            manifest = {
                'created_at': backup_data['timestamp'],
                'type': backup_data['type'],
                'heroku_app': os.environ.get('HEROKU_APP_NAME', 'unknown'),
                'files': []
            }
            
            # Agregar archivos al ZIP
            for file_info in backup_data['files']:
                file_path = Path(file_info['file'])
                if file_path.exists():
                    arc_name = f"{file_info['type']}/{file_path.name}"
                    zf.write(file_path, arc_name)
                    manifest['files'].append({
                        'type': file_info['type'],
                        'name': file_path.name,
                        'size': file_info['size'],
                        'archive_path': arc_name
                    })
            
            # Agregar manifest
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))
        
        return zip_file
    
    def upload_to_s3(self, file_path, s3_key):
        """Sube archivo a S3"""
        try:
            self.s3_client.upload_file(str(file_path), self.s3_bucket, s3_key)
            logging.info(f"Backup subido a S3: s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            logging.error(f"Error subiendo a S3: {e}")
            return False
    
    def list_s3_backups(self):
        """Lista backups disponibles en S3"""
        if not self.s3_client:
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='backups/'
            )
            
            backups = []
            for obj in response.get('Contents', []):
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'name': obj['Key'].split('/')[-1]
                })
            
            return sorted(backups, key=lambda x: x['last_modified'], reverse=True)
            
        except Exception as e:
            logging.error(f"Error listando backups S3: {e}")
            return []
    
    def download_from_s3(self, s3_key, local_path):
        """Descarga backup desde S3"""
        try:
            self.s3_client.download_file(self.s3_bucket, s3_key, str(local_path))
            return True
        except Exception as e:
            logging.error(f"Error descargando desde S3: {e}")
            return False
    
    def get_backup_status(self):
        """Obtiene estado del sistema de backup en Heroku"""
        status = {
            'platform': 'heroku' if self.is_heroku else 'local',
            'database_type': 'postgresql' if 'postgres' in os.environ.get('DATABASE_URL', '') else 'sqlite',
            's3_configured': bool(self.s3_client),
            'temp_dir': str(self.temp_dir),
            'last_backup': None,
            'backup_count': 0
        }
        
        if self.s3_client:
            backups = self.list_s3_backups()
            status['backup_count'] = len(backups)
            if backups:
                status['last_backup'] = backups[0]['last_modified']
        
        return status
    
    def cleanup_temp_files(self):
        """Limpia archivos temporales"""
        try:
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            logging.info("Archivos temporales limpiados")
        except Exception as e:
            logging.error(f"Error limpiando archivos temporales: {e}")

def create_heroku_backup():
    """Función de conveniencia para crear backup en Heroku"""
    adapter = HerokuBackupAdapter()
    result = adapter.create_heroku_backup()
    adapter.cleanup_temp_files()
    return result

if __name__ == '__main__':
    # Ejecutar backup si se llama directamente
    result = create_heroku_backup()
    if result['success']:
        print(f"✅ Backup exitoso: {result['message']}")
        print(f"   Archivo: {result['backup_file']}")
        print(f"   Ubicación: {result['location']}")
        print(f"   Tamaño: {result['size'] / (1024*1024):.1f} MB")
    else:
        print(f"❌ Error en backup: {result['error']}")
        sys.exit(1)
