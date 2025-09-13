#!/usr/bin/env python3
"""
Sistema de Monitoreo y Alertas para Backups
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script monitorea el estado del sistema de backup y envía alertas
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# Importaciones opcionales para email
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class BackupMonitor:
    def __init__(self, config_file='backup_monitor_config.json'):
        """Inicializa el monitor de backups"""
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        """Carga la configuración del monitor"""
        default_config = {
            "monitoring": {
                "check_interval_hours": 6,
                "max_backup_age_hours": 26,
                "min_backup_size_mb": 1,
                "alert_on_failure": True,
                "alert_on_old_backup": True
            },
            "email_alerts": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": [],
                "subject_prefix": "[Backup Alert]"
            },
            "paths": {
                "backup_dir": "backups",
                "log_files": [
                    "backup_system.log",
                    "restore_system.log",
                    "backup_scheduler.log"
                ]
            },
            "thresholds": {
                "disk_space_warning_gb": 5,
                "backup_size_increase_percent": 200,
                "consecutive_failures": 3
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Error cargando configuración del monitor: {e}")
        
        self.config = default_config
        self.save_config()
    
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración del monitor: {e}")
    
    def check_backup_health(self):
        """Verifica el estado general del sistema de backup"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'issues': [],
            'warnings': [],
            'info': []
        }
        
        # Verificar backups recientes
        backup_status = self.check_recent_backups()
        if backup_status['status'] != 'ok':
            health_report['issues'].extend(backup_status['issues'])
            health_report['status'] = 'warning'
        
        # Verificar espacio en disco
        disk_status = self.check_disk_space()
        if disk_status['status'] != 'ok':
            if disk_status['status'] == 'critical':
                health_report['issues'].extend(disk_status['issues'])
                health_report['status'] = 'critical'
            else:
                health_report['warnings'].extend(disk_status['warnings'])
                if health_report['status'] == 'healthy':
                    health_report['status'] = 'warning'
        
        # Verificar logs de errores
        log_status = self.check_error_logs()
        if log_status['errors'] > 0:
            health_report['issues'].append(f"Se encontraron {log_status['errors']} errores en los logs")
            health_report['status'] = 'warning'
        
        # Verificar tareas programadas
        task_status = self.check_scheduled_tasks()
        if not task_status['all_active']:
            health_report['warnings'].append("Algunas tareas programadas no están activas")
            if health_report['status'] == 'healthy':
                health_report['status'] = 'warning'
        
        # Información adicional
        health_report['info'].append(f"Último backup: {backup_status.get('last_backup', 'No encontrado')}")
        health_report['info'].append(f"Espacio libre: {disk_status.get('free_space_gb', 0):.1f} GB")
        health_report['info'].append(f"Tareas activas: {task_status.get('active_tasks', 0)}/4")
        
        return health_report
    
    def check_recent_backups(self):
        """Verifica si hay backups recientes"""
        backup_dir = Path(self.config['paths']['backup_dir'])
        max_age_hours = self.config['monitoring']['max_backup_age_hours']
        min_size_mb = self.config['monitoring']['min_backup_size_mb']
        
        status = {
            'status': 'ok',
            'issues': [],
            'last_backup': None
        }
        
        if not backup_dir.exists():
            status['status'] = 'error'
            status['issues'].append("Directorio de backups no encontrado")
            return status
        
        # Buscar el backup más reciente
        latest_backup = None
        latest_time = None
        
        for backup_file in backup_dir.rglob('*.zip'):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if latest_time is None or file_time > latest_time:
                latest_backup = backup_file
                latest_time = file_time
        
        if latest_backup is None:
            status['status'] = 'error'
            status['issues'].append("No se encontraron backups")
            return status
        
        # Verificar antigüedad
        age_hours = (datetime.now() - latest_time).total_seconds() / 3600
        status['last_backup'] = latest_time.strftime('%Y-%m-%d %H:%M:%S')
        
        if age_hours > max_age_hours:
            status['status'] = 'warning'
            status['issues'].append(f"Último backup tiene {age_hours:.1f} horas (máximo: {max_age_hours})")
        
        # Verificar tamaño
        size_mb = latest_backup.stat().st_size / (1024 * 1024)
        if size_mb < min_size_mb:
            status['status'] = 'warning'
            status['issues'].append(f"Último backup muy pequeño: {size_mb:.1f} MB")
        
        return status
    
    def check_disk_space(self):
        """Verifica el espacio disponible en disco"""
        backup_dir = Path(self.config['paths']['backup_dir'])
        warning_gb = self.config['thresholds']['disk_space_warning_gb']
        
        status = {
            'status': 'ok',
            'issues': [],
            'warnings': [],
            'free_space_gb': 0
        }
        
        try:
            # Obtener información del disco
            if os.name == 'nt':  # Windows
                import shutil
                total, used, free = shutil.disk_usage(backup_dir.parent if backup_dir.exists() else '.')
            else:  # Unix/Linux
                statvfs = os.statvfs(backup_dir.parent if backup_dir.exists() else '.')
                free = statvfs.f_frsize * statvfs.f_bavail
            
            free_gb = free / (1024**3)
            status['free_space_gb'] = free_gb
            
            if free_gb < 1:  # Menos de 1 GB
                status['status'] = 'critical'
                status['issues'].append(f"Espacio crítico en disco: {free_gb:.1f} GB")
            elif free_gb < warning_gb:
                status['status'] = 'warning'
                status['warnings'].append(f"Poco espacio en disco: {free_gb:.1f} GB")
            
        except Exception as e:
            status['status'] = 'error'
            status['issues'].append(f"Error verificando espacio en disco: {e}")
        
        return status
    
    def check_error_logs(self):
        """Verifica errores en los logs del sistema"""
        log_files = self.config['paths']['log_files']
        error_count = 0
        recent_errors = []
        
        # Buscar errores en las últimas 24 horas
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'ERROR' in line:
                                try:
                                    # Intentar extraer timestamp del log
                                    timestamp_str = line.split(' - ')[0]
                                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                                    
                                    if log_time > cutoff_time:
                                        error_count += 1
                                        recent_errors.append({
                                            'file': log_file,
                                            'time': timestamp_str,
                                            'message': line.strip()
                                        })
                                except (ValueError, IndexError):
                                    # Si no se puede parsear el timestamp, contar el error de todas formas
                                    error_count += 1
                
                except Exception as e:
                    logging.warning(f"Error leyendo log {log_file}: {e}")
        
        return {
            'errors': error_count,
            'recent_errors': recent_errors
        }
    
    def check_scheduled_tasks(self):
        """Verifica el estado de las tareas programadas"""
        task_names = [
            "MarketplaceVUco_DailyBackup",
            "MarketplaceVUco_WeeklyBackup",
            "MarketplaceVUco_MonthlyBackup",
            "MarketplaceVUco_BackupCleanup"
        ]
        
        active_tasks = 0
        task_status = {}
        
        for task_name in task_names:
            try:
                import subprocess
                result = subprocess.run(
                    ['schtasks', '/query', '/tn', task_name],
                    capture_output=True, text=True, check=True
                )
                active_tasks += 1
                task_status[task_name] = 'active'
            except subprocess.CalledProcessError:
                task_status[task_name] = 'inactive'
        
        return {
            'all_active': active_tasks == len(task_names),
            'active_tasks': active_tasks,
            'total_tasks': len(task_names),
            'task_status': task_status
        }
    
    def send_email_alert(self, subject, message):
        """Envía alerta por email"""
        if not self.config['email_alerts']['enabled'] or not EMAIL_AVAILABLE:
            return False
        
        try:
            # Configurar email
            msg = MIMEMultipart()
            msg['From'] = self.config['email_alerts']['from_email']
            msg['To'] = ', '.join(self.config['email_alerts']['to_emails'])
            msg['Subject'] = f"{self.config['email_alerts']['subject_prefix']} {subject}"
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # Enviar email
            server = smtplib.SMTP(
                self.config['email_alerts']['smtp_server'],
                self.config['email_alerts']['smtp_port']
            )
            server.starttls()
            server.login(
                self.config['email_alerts']['username'],
                self.config['email_alerts']['password']
            )
            
            text = msg.as_string()
            server.sendmail(
                self.config['email_alerts']['from_email'],
                self.config['email_alerts']['to_emails'],
                text
            )
            server.quit()
            
            logging.info(f"Alerta enviada por email: {subject}")
            return True
            
        except Exception as e:
            logging.error(f"Error enviando alerta por email: {e}")
            return False
    
    def generate_health_report_text(self, health_report):
        """Genera reporte de salud en formato texto"""
        status_emoji = {
            'healthy': '[OK]',
            'warning': '[WARNING]',
            'critical': '[CRITICAL]'
        }
        
        report = f"""
{status_emoji.get(health_report['status'], '[UNKNOWN]')} REPORTE DE SALUD DEL SISTEMA DE BACKUP
========================================

Estado General: {health_report['status'].upper()}
Fecha: {health_report['timestamp']}

"""
        
        if health_report['issues']:
            report += "PROBLEMAS CRITICOS:\n"
            for issue in health_report['issues']:
                report += f"  - {issue}\n"
            report += "\n"
        
        if health_report['warnings']:
            report += "ADVERTENCIAS:\n"
            for warning in health_report['warnings']:
                report += f"  - {warning}\n"
            report += "\n"
        
        if health_report['info']:
            report += "INFORMACION:\n"
            for info in health_report['info']:
                report += f"  - {info}\n"
            report += "\n"
        
        report += "RECOMENDACIONES:\n"
        
        if health_report['status'] == 'critical':
            report += "  - Revisar inmediatamente el sistema de backup\n"
            report += "  - Verificar espacio en disco\n"
            report += "  - Ejecutar backup manual si es necesario\n"
        elif health_report['status'] == 'warning':
            report += "  - Revisar logs de errores\n"
            report += "  - Verificar tareas programadas\n"
            report += "  - Considerar limpiar backups antiguos\n"
        else:
            report += "  - Sistema funcionando correctamente\n"
            report += "  - Continuar con monitoreo regular\n"
        
        return report
    
    def run_health_check(self):
        """Ejecuta verificación completa de salud"""
        logging.info("Iniciando verificación de salud del sistema de backup")
        
        health_report = self.check_backup_health()
        report_text = self.generate_health_report_text(health_report)
        
        print(report_text)
        
        # Guardar reporte
        report_file = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        # Enviar alerta si es necesario
        if health_report['status'] in ['warning', 'critical'] and self.config['monitoring']['alert_on_failure']:
            subject = f"Sistema de Backup - Estado: {health_report['status'].upper()}"
            self.send_email_alert(subject, report_text)
        
        logging.info(f"Verificación completada. Estado: {health_report['status']}")
        return health_report
    
    def setup_email_alerts(self):
        """Configuración interactiva de alertas por email"""
        print("\n=== Configuración de Alertas por Email ===")
        
        enable = input("¿Habilitar alertas por email? (s/N): ").strip().lower() == 's'
        
        if not enable:
            self.config['email_alerts']['enabled'] = False
            self.save_config()
            print("Alertas por email deshabilitadas")
            return
        
        print("\nConfigurando servidor SMTP...")
        smtp_server = input("Servidor SMTP (default: smtp.gmail.com): ").strip() or "smtp.gmail.com"
        smtp_port = int(input("Puerto SMTP (default: 587): ").strip() or "587")
        
        print("\nCredenciales de email...")
        username = input("Usuario/Email: ").strip()
        password = input("Contraseña (o App Password para Gmail): ").strip()
        from_email = input(f"Email remitente (default: {username}): ").strip() or username
        
        print("\nDestinatarios...")
        to_emails = []
        while True:
            email = input("Email destinatario (Enter para terminar): ").strip()
            if not email:
                break
            to_emails.append(email)
        
        if not to_emails:
            print("Se requiere al menos un destinatario")
            return
        
        # Actualizar configuración
        self.config['email_alerts'].update({
            'enabled': True,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'from_email': from_email,
            'to_emails': to_emails
        })
        
        self.save_config()
        
        # Probar envío
        test = input("¿Enviar email de prueba? (s/N): ").strip().lower() == 's'
        if test:
            if self.send_email_alert("Prueba de Configuración", "Este es un email de prueba del sistema de monitoreo de backups."):
                print("✅ Email de prueba enviado exitosamente")
            else:
                print("❌ Error enviando email de prueba")

def main():
    """Función principal"""
    monitor = BackupMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'check':
            monitor.run_health_check()
            
        elif command == 'setup-email':
            monitor.setup_email_alerts()
            
        elif command == 'test-email':
            if monitor.config['email_alerts']['enabled']:
                health_report = monitor.check_backup_health()
                report_text = monitor.generate_health_report_text(health_report)
                monitor.send_email_alert("Prueba de Monitoreo", report_text)
            else:
                print("Alertas por email no están configuradas")
        
        else:
            print("Comandos disponibles:")
            print("  check       - Ejecutar verificación de salud")
            print("  setup-email - Configurar alertas por email")
            print("  test-email  - Enviar email de prueba")
    
    else:
        print("Monitor de Sistema de Backup")
        print("Uso: python backup_monitor.py <comando>")
        print("\nComandos:")
        print("  check       - Verificar salud del sistema")
        print("  setup-email - Configurar alertas")
        print("  test-email  - Probar alertas")

if __name__ == "__main__":
    main()
