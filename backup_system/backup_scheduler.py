#!/usr/bin/env python3
"""
Programador de Backups Automatizado para Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este script programa y ejecuta backups automáticos usando Windows Task Scheduler
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class BackupScheduler:
    def __init__(self):
        """Inicializa el programador de backups"""
        self.project_path = Path(__file__).parent.absolute()
        self.python_exe = sys.executable
        self.backup_script = self.project_path / "backup_system.py"
        
    def create_daily_backup_task(self, time_str="02:00"):
        """Crea tarea programada para backup diario"""
        task_name = "MarketplaceVUco_DailyBackup"
        
        # Comando para ejecutar el backup
        command = f'"{self.python_exe}" "{self.backup_script}" backup daily'
        
        # Crear tarea usando schtasks
        schtasks_cmd = [
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', command,
            '/sc', 'daily',
            '/st', time_str,
            '/f'  # Forzar creación (sobrescribir si existe)
        ]
        
        try:
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
            logging.info(f"Tarea diaria creada: {task_name} a las {time_str}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creando tarea diaria: {e.stderr}")
            return False
    
    def create_weekly_backup_task(self, day="SUN", time_str="02:30"):
        """Crea tarea programada para backup semanal"""
        task_name = "MarketplaceVUco_WeeklyBackup"
        
        command = f'"{self.python_exe}" "{self.backup_script}" backup weekly'
        
        schtasks_cmd = [
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', command,
            '/sc', 'weekly',
            '/d', day,
            '/st', time_str,
            '/f'
        ]
        
        try:
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
            logging.info(f"Tarea semanal creada: {task_name} los {day} a las {time_str}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creando tarea semanal: {e.stderr}")
            return False
    
    def create_monthly_backup_task(self, day=1, time_str="03:00"):
        """Crea tarea programada para backup mensual"""
        task_name = "MarketplaceVUco_MonthlyBackup"
        
        command = f'"{self.python_exe}" "{self.backup_script}" backup monthly'
        
        schtasks_cmd = [
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', command,
            '/sc', 'monthly',
            '/d', str(day),
            '/st', time_str,
            '/f'
        ]
        
        try:
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
            logging.info(f"Tarea mensual creada: {task_name} el día {day} a las {time_str}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creando tarea mensual: {e.stderr}")
            return False
    
    def create_cleanup_task(self, time_str="04:00"):
        """Crea tarea para limpieza de backups antiguos"""
        task_name = "MarketplaceVUco_BackupCleanup"
        
        command = f'"{self.python_exe}" "{self.backup_script}" cleanup'
        
        schtasks_cmd = [
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', command,
            '/sc', 'daily',
            '/st', time_str,
            '/f'
        ]
        
        try:
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
            logging.info(f"Tarea de limpieza creada: {task_name} a las {time_str}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creando tarea de limpieza: {e.stderr}")
            return False
    
    def list_backup_tasks(self):
        """Lista todas las tareas de backup programadas"""
        task_names = [
            "MarketplaceVUco_DailyBackup",
            "MarketplaceVUco_WeeklyBackup", 
            "MarketplaceVUco_MonthlyBackup",
            "MarketplaceVUco_BackupCleanup"
        ]
        
        print("\nTareas de backup programadas:")
        print("-" * 50)
        
        for task_name in task_names:
            try:
                result = subprocess.run(
                    ['schtasks', '/query', '/tn', task_name, '/fo', 'csv'],
                    capture_output=True, text=True, check=True
                )
                
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parsear información de la tarea
                    data = lines[1].split(',')
                    status = data[3].strip('"') if len(data) > 3 else "Desconocido"
                    next_run = data[4].strip('"') if len(data) > 4 else "No programado"
                    
                    print(f"✓ {task_name}")
                    print(f"  Estado: {status}")
                    print(f"  Próxima ejecución: {next_run}")
                else:
                    print(f"✗ {task_name} - No encontrada")
                    
            except subprocess.CalledProcessError:
                print(f"✗ {task_name} - No encontrada")
            
            print()
    
    def delete_backup_tasks(self):
        """Elimina todas las tareas de backup"""
        task_names = [
            "MarketplaceVUco_DailyBackup",
            "MarketplaceVUco_WeeklyBackup",
            "MarketplaceVUco_MonthlyBackup", 
            "MarketplaceVUco_BackupCleanup"
        ]
        
        for task_name in task_names:
            try:
                subprocess.run(
                    ['schtasks', '/delete', '/tn', task_name, '/f'],
                    capture_output=True, text=True, check=True
                )
                logging.info(f"Tarea eliminada: {task_name}")
            except subprocess.CalledProcessError:
                logging.warning(f"Tarea no encontrada para eliminar: {task_name}")
    
    def setup_all_tasks(self):
        """Configura todas las tareas de backup"""
        print("Configurando tareas programadas de backup...")
        
        # Eliminar tareas existentes primero
        self.delete_backup_tasks()
        
        success_count = 0
        total_tasks = 4
        
        # Crear tareas
        if self.create_daily_backup_task("02:00"):
            success_count += 1
        
        if self.create_weekly_backup_task("SUN", "02:30"):
            success_count += 1
            
        if self.create_monthly_backup_task(1, "03:00"):
            success_count += 1
            
        if self.create_cleanup_task("04:00"):
            success_count += 1
        
        print(f"\nTareas configuradas: {success_count}/{total_tasks}")
        
        if success_count == total_tasks:
            print("✓ Todas las tareas se configuraron exitosamente")
            
            # Crear archivo de configuración
            config = {
                "backup_schedule_configured": True,
                "configured_date": datetime.now().isoformat(),
                "tasks": {
                    "daily": {"time": "02:00", "enabled": True},
                    "weekly": {"day": "SUN", "time": "02:30", "enabled": True},
                    "monthly": {"day": 1, "time": "03:00", "enabled": True},
                    "cleanup": {"time": "04:00", "enabled": True}
                }
            }
            
            with open('backup_schedule_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            return True
        else:
            print("✗ Algunas tareas no se pudieron configurar")
            return False
    
    def test_backup_execution(self):
        """Ejecuta un backup de prueba"""
        print("Ejecutando backup de prueba...")
        
        try:
            result = subprocess.run(
                [self.python_exe, str(self.backup_script), 'backup', 'manual'],
                capture_output=True, text=True, timeout=300  # 5 minutos timeout
            )
            
            if result.returncode == 0:
                print("✓ Backup de prueba ejecutado exitosamente")
                print("Salida:")
                print(result.stdout)
                return True
            else:
                print("✗ Error en backup de prueba")
                print("Error:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ Backup de prueba excedió el tiempo límite")
            return False
        except Exception as e:
            print(f"✗ Error ejecutando backup de prueba: {e}")
            return False

def main():
    """Función principal"""
    scheduler = BackupScheduler()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'setup':
            scheduler.setup_all_tasks()
            
        elif command == 'list':
            scheduler.list_backup_tasks()
            
        elif command == 'delete':
            print("Eliminando todas las tareas de backup...")
            scheduler.delete_backup_tasks()
            print("Tareas eliminadas")
            
        elif command == 'test':
            scheduler.test_backup_execution()
            
        else:
            print("Comandos disponibles:")
            print("  setup  - Configurar todas las tareas programadas")
            print("  list   - Listar tareas existentes")
            print("  delete - Eliminar todas las tareas")
            print("  test   - Ejecutar backup de prueba")
    
    else:
        print("Programador de Backups para Marketplace de Vehículos")
        print("=" * 50)
        print()
        print("Este script configura backups automáticos usando Windows Task Scheduler:")
        print("- Backup diario: 02:00 AM")
        print("- Backup semanal: Domingos 02:30 AM") 
        print("- Backup mensual: Día 1 de cada mes 03:00 AM")
        print("- Limpieza: Diaria 04:00 AM")
        print()
        print("Uso: python backup_scheduler.py <comando>")
        print()
        print("Comandos:")
        print("  setup  - Configurar todas las tareas")
        print("  list   - Ver tareas configuradas")
        print("  delete - Eliminar tareas")
        print("  test   - Probar backup manual")

if __name__ == "__main__":
    main()
