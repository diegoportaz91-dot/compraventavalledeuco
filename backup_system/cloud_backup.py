#!/usr/bin/env python3
"""
Sistema de Backup en la Nube para Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script permite sincronizar backups con servicios en la nube:
- Google Drive
- Dropbox
- OneDrive
- FTP/SFTP
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime
import ftplib
import paramiko
from typing import Optional, Dict, Any

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CloudBackupManager:
    def __init__(self, config_file='cloud_backup_config.json'):
        """Inicializa el gestor de backup en la nube"""
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Carga la configuración de servicios en la nube"""
        default_config = {
            "enabled_services": [],
            "google_drive": {
                "enabled": False,
                "credentials_file": "google_drive_credentials.json",
                "folder_id": None,
                "max_file_size_mb": 100
            },
            "dropbox": {
                "enabled": False,
                "access_token": "",
                "app_key": "",
                "app_secret": "",
                "folder_path": "/backups"
            },
            "onedrive": {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "tenant_id": "",
                "folder_path": "/backups"
            },
            "ftp": {
                "enabled": False,
                "host": "",
                "port": 21,
                "username": "",
                "password": "",
                "remote_path": "/backups",
                "use_tls": False
            },
            "sftp": {
                "enabled": False,
                "host": "",
                "port": 22,
                "username": "",
                "password": "",
                "private_key_file": "",
                "remote_path": "/backups"
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Error cargando configuración de nube: {e}")
        
        self.config = default_config
        self.save_config()
    
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración de nube: {e}")
    
    def upload_to_google_drive(self, file_path: str) -> bool:
        """Sube archivo a Google Drive"""
        if not self.config['google_drive']['enabled']:
            return False
        
        try:
            # Nota: Requiere instalación de google-api-python-client
            # pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
            
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            
            creds = None
            token_file = 'google_drive_token.json'
            
            # Cargar credenciales existentes
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            # Si no hay credenciales válidas, obtenerlas
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config['google_drive']['credentials_file'], SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Guardar credenciales para próxima ejecución
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            service = build('drive', 'v3', credentials=creds)
            
            # Preparar archivo para subir
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.config['google_drive']['folder_id']] if self.config['google_drive']['folder_id'] else []
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            # Subir archivo
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logging.info(f"Archivo subido a Google Drive: {file.get('id')}")
            return True
            
        except Exception as e:
            logging.error(f"Error subiendo a Google Drive: {e}")
            return False
    
    def upload_to_dropbox(self, file_path: str) -> bool:
        """Sube archivo a Dropbox"""
        if not self.config['dropbox']['enabled']:
            return False
        
        try:
            # Nota: Requiere instalación de dropbox
            # pip install dropbox
            
            import dropbox
            
            dbx = dropbox.Dropbox(self.config['dropbox']['access_token'])
            
            file_name = os.path.basename(file_path)
            remote_path = f"{self.config['dropbox']['folder_path']}/{file_name}"
            
            # Subir archivo
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                
                if file_size <= 150 * 1024 * 1024:  # 150MB
                    # Subida simple para archivos pequeños
                    dbx.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode.overwrite)
                else:
                    # Subida por chunks para archivos grandes
                    CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
                    
                    session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=session_start_result.session_id,
                        offset=f.tell()
                    )
                    
                    while f.tell() < file_size:
                        if (file_size - f.tell()) <= CHUNK_SIZE:
                            # Último chunk
                            commit = dropbox.files.CommitInfo(path=remote_path, mode=dropbox.files.WriteMode.overwrite)
                            dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                        else:
                            dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                            cursor.offset = f.tell()
            
            logging.info(f"Archivo subido a Dropbox: {remote_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error subiendo a Dropbox: {e}")
            return False
    
    def upload_to_ftp(self, file_path: str) -> bool:
        """Sube archivo via FTP/FTPS"""
        if not self.config['ftp']['enabled']:
            return False
        
        try:
            if self.config['ftp']['use_tls']:
                ftp = ftplib.FTP_TLS()
            else:
                ftp = ftplib.FTP()
            
            # Conectar
            ftp.connect(self.config['ftp']['host'], self.config['ftp']['port'])
            ftp.login(self.config['ftp']['username'], self.config['ftp']['password'])
            
            if self.config['ftp']['use_tls']:
                ftp.prot_p()  # Proteger transferencia de datos
            
            # Cambiar al directorio remoto
            try:
                ftp.cwd(self.config['ftp']['remote_path'])
            except ftplib.error_perm:
                # Crear directorio si no existe
                self._create_ftp_directory(ftp, self.config['ftp']['remote_path'])
                ftp.cwd(self.config['ftp']['remote_path'])
            
            # Subir archivo
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {file_name}', f)
            
            ftp.quit()
            
            logging.info(f"Archivo subido via FTP: {file_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error subiendo via FTP: {e}")
            return False
    
    def upload_to_sftp(self, file_path: str) -> bool:
        """Sube archivo via SFTP"""
        if not self.config['sftp']['enabled']:
            return False
        
        try:
            # Crear cliente SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Conectar
            if self.config['sftp']['private_key_file']:
                key = paramiko.RSAKey.from_private_key_file(self.config['sftp']['private_key_file'])
                ssh.connect(
                    self.config['sftp']['host'],
                    port=self.config['sftp']['port'],
                    username=self.config['sftp']['username'],
                    pkey=key
                )
            else:
                ssh.connect(
                    self.config['sftp']['host'],
                    port=self.config['sftp']['port'],
                    username=self.config['sftp']['username'],
                    password=self.config['sftp']['password']
                )
            
            # Crear cliente SFTP
            sftp = ssh.open_sftp()
            
            # Crear directorio remoto si no existe
            try:
                sftp.listdir(self.config['sftp']['remote_path'])
            except FileNotFoundError:
                self._create_sftp_directory(sftp, self.config['sftp']['remote_path'])
            
            # Subir archivo
            file_name = os.path.basename(file_path)
            remote_file_path = f"{self.config['sftp']['remote_path']}/{file_name}"
            
            sftp.put(file_path, remote_file_path)
            
            sftp.close()
            ssh.close()
            
            logging.info(f"Archivo subido via SFTP: {remote_file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error subiendo via SFTP: {e}")
            return False
    
    def _create_ftp_directory(self, ftp, path):
        """Crea directorio en servidor FTP recursivamente"""
        dirs = path.strip('/').split('/')
        current_path = ''
        
        for dir_name in dirs:
            current_path += f'/{dir_name}'
            try:
                ftp.mkd(current_path)
            except ftplib.error_perm:
                pass  # Directorio ya existe
    
    def _create_sftp_directory(self, sftp, path):
        """Crea directorio en servidor SFTP recursivamente"""
        dirs = path.strip('/').split('/')
        current_path = ''
        
        for dir_name in dirs:
            current_path += f'/{dir_name}'
            try:
                sftp.mkdir(current_path)
            except FileExistsError:
                pass  # Directorio ya existe
    
    def sync_backup_to_cloud(self, backup_file_path: str) -> Dict[str, bool]:
        """Sincroniza un archivo de backup con todos los servicios habilitados"""
        results = {}
        
        if not os.path.exists(backup_file_path):
            logging.error(f"Archivo de backup no encontrado: {backup_file_path}")
            return results
        
        file_size_mb = os.path.getsize(backup_file_path) / (1024 * 1024)
        logging.info(f"Sincronizando backup ({file_size_mb:.1f} MB): {backup_file_path}")
        
        # Google Drive
        if 'google_drive' in self.config['enabled_services']:
            results['google_drive'] = self.upload_to_google_drive(backup_file_path)
        
        # Dropbox
        if 'dropbox' in self.config['enabled_services']:
            results['dropbox'] = self.upload_to_dropbox(backup_file_path)
        
        # FTP
        if 'ftp' in self.config['enabled_services']:
            results['ftp'] = self.upload_to_ftp(backup_file_path)
        
        # SFTP
        if 'sftp' in self.config['enabled_services']:
            results['sftp'] = self.upload_to_sftp(backup_file_path)
        
        # Resumen de resultados
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        if successful == total and total > 0:
            logging.info(f"Backup sincronizado exitosamente con {successful}/{total} servicios")
        elif successful > 0:
            logging.warning(f"Backup sincronizado parcialmente con {successful}/{total} servicios")
        else:
            logging.error("No se pudo sincronizar el backup con ningún servicio")
        
        return results
    
    def setup_service(self, service_name: str):
        """Configuración interactiva de un servicio"""
        if service_name == 'google_drive':
            print("\n=== Configuración de Google Drive ===")
            print("1. Ve a https://console.developers.google.com/")
            print("2. Crea un proyecto o selecciona uno existente")
            print("3. Habilita la API de Google Drive")
            print("4. Crea credenciales OAuth 2.0")
            print("5. Descarga el archivo JSON de credenciales")
            
            credentials_file = input("Ruta al archivo de credenciales JSON: ").strip()
            if os.path.exists(credentials_file):
                self.config['google_drive']['credentials_file'] = credentials_file
                self.config['google_drive']['enabled'] = True
                if 'google_drive' not in self.config['enabled_services']:
                    self.config['enabled_services'].append('google_drive')
                print("Google Drive configurado exitosamente")
            else:
                print("Archivo de credenciales no encontrado")
        
        elif service_name == 'dropbox':
            print("\n=== Configuración de Dropbox ===")
            print("1. Ve a https://www.dropbox.com/developers/apps")
            print("2. Crea una nueva app")
            print("3. Genera un access token")
            
            access_token = input("Access Token de Dropbox: ").strip()
            folder_path = input("Carpeta remota (default: /backups): ").strip() or "/backups"
            
            if access_token:
                self.config['dropbox']['access_token'] = access_token
                self.config['dropbox']['folder_path'] = folder_path
                self.config['dropbox']['enabled'] = True
                if 'dropbox' not in self.config['enabled_services']:
                    self.config['enabled_services'].append('dropbox')
                print("Dropbox configurado exitosamente")
            else:
                print("Access token requerido")
        
        elif service_name == 'ftp':
            print("\n=== Configuración de FTP ===")
            host = input("Servidor FTP: ").strip()
            port = int(input("Puerto (default: 21): ").strip() or "21")
            username = input("Usuario: ").strip()
            password = input("Contraseña: ").strip()
            remote_path = input("Carpeta remota (default: /backups): ").strip() or "/backups"
            use_tls = input("¿Usar TLS? (s/N): ").strip().lower() == 's'
            
            if host and username:
                self.config['ftp'].update({
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password,
                    'remote_path': remote_path,
                    'use_tls': use_tls,
                    'enabled': True
                })
                if 'ftp' not in self.config['enabled_services']:
                    self.config['enabled_services'].append('ftp')
                print("FTP configurado exitosamente")
            else:
                print("Servidor y usuario son requeridos")
        
        elif service_name == 'sftp':
            print("\n=== Configuración de SFTP ===")
            host = input("Servidor SFTP: ").strip()
            port = int(input("Puerto (default: 22): ").strip() or "22")
            username = input("Usuario: ").strip()
            
            auth_method = input("Método de autenticación (password/key): ").strip().lower()
            
            if auth_method == 'key':
                private_key_file = input("Ruta a la clave privada: ").strip()
                password = ""
            else:
                private_key_file = ""
                password = input("Contraseña: ").strip()
            
            remote_path = input("Carpeta remota (default: /backups): ").strip() or "/backups"
            
            if host and username:
                self.config['sftp'].update({
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password,
                    'private_key_file': private_key_file,
                    'remote_path': remote_path,
                    'enabled': True
                })
                if 'sftp' not in self.config['enabled_services']:
                    self.config['enabled_services'].append('sftp')
                print("SFTP configurado exitosamente")
            else:
                print("Servidor y usuario son requeridos")
        
        self.save_config()

def main():
    """Función principal"""
    cloud_manager = CloudBackupManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'setup':
            if len(sys.argv) > 2:
                service = sys.argv[2].lower()
                cloud_manager.setup_service(service)
            else:
                print("Servicios disponibles: google_drive, dropbox, ftp, sftp")
                print("Uso: python cloud_backup.py setup <servicio>")
        
        elif command == 'sync':
            if len(sys.argv) > 2:
                backup_file = sys.argv[2]
                cloud_manager.sync_backup_to_cloud(backup_file)
            else:
                print("Uso: python cloud_backup.py sync <archivo_backup>")
        
        elif command == 'status':
            print("\nServicios configurados:")
            for service in cloud_manager.config['enabled_services']:
                print(f"- {service}: habilitado")
        
        else:
            print("Comandos disponibles:")
            print("  setup <servicio> - Configurar servicio de nube")
            print("  sync <archivo>   - Sincronizar backup con la nube")
            print("  status          - Ver servicios configurados")
    
    else:
        print("Sistema de Backup en la Nube")
        print("Uso: python cloud_backup.py <comando> [argumentos]")
        print("\nComandos:")
        print("  setup <servicio> - Configurar servicio")
        print("  sync <archivo>   - Sincronizar backup")
        print("  status          - Ver estado")

if __name__ == "__main__":
    main()
