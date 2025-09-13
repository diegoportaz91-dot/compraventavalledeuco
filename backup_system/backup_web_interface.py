#!/usr/bin/env python3
"""
Interfaz Web para Gestión de Backups - Marketplace de Vehículos
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Interfaz web simple para gestionar el sistema de backups
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file, flash, redirect, url_for
import subprocess
import threading
import time

# Configuración de logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = 'backup_interface_secret_key_change_in_production'

class BackupWebInterface:
    def __init__(self):
        self.project_path = Path(__file__).parent.absolute()
        self.backup_scripts = {
            'backup_system': self.project_path / 'backup_system.py',
            'restore_system': self.project_path / 'restore_system.py',
            'incremental_backup': self.project_path / 'incremental_backup.py',
            'backup_monitor': self.project_path / 'backup_monitor.py',
            'cloud_backup': self.project_path / 'cloud_backup.py'
        }
        
    def run_command(self, command, timeout=300):
        """Ejecuta un comando y retorna el resultado"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=str(self.project_path)
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Comando excedió el tiempo límite',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def get_backup_status(self):
        """Obtiene el estado actual del sistema de backup"""
        status = {
            'last_backup': None,
            'backup_count': 0,
            'total_size_mb': 0,
            'health_status': 'unknown',
            'scheduled_tasks': 0
        }
        
        try:
            # Verificar backups existentes
            backup_dirs = ['backups/daily', 'backups/weekly', 'backups/monthly', 'backups']
            
            for backup_dir in backup_dirs:
                backup_path = self.project_path / backup_dir
                if backup_path.exists():
                    for backup_file in backup_path.glob('*.zip'):
                        status['backup_count'] += 1
                        status['total_size_mb'] += backup_file.stat().st_size / (1024 * 1024)
                        
                        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        if status['last_backup'] is None or file_time > status['last_backup']:
                            status['last_backup'] = file_time
            
            # Verificar tareas programadas
            task_names = [
                "MarketplaceVUco_DailyBackup",
                "MarketplaceVUco_WeeklyBackup", 
                "MarketplaceVUco_MonthlyBackup",
                "MarketplaceVUco_BackupCleanup"
            ]
            
            for task_name in task_names:
                result = self.run_command(['schtasks', '/query', '/tn', task_name])
                if result['success']:
                    status['scheduled_tasks'] += 1
            
            # Determinar estado de salud básico
            if status['last_backup']:
                hours_since_backup = (datetime.now() - status['last_backup']).total_seconds() / 3600
                if hours_since_backup < 26:  # Menos de 26 horas
                    status['health_status'] = 'healthy'
                elif hours_since_backup < 48:  # Menos de 48 horas
                    status['health_status'] = 'warning'
                else:
                    status['health_status'] = 'critical'
            else:
                status['health_status'] = 'no_backups'
                
        except Exception as e:
            logging.error(f"Error obteniendo estado de backup: {e}")
            status['health_status'] = 'error'
        
        return status
    
    def get_backup_list(self):
        """Obtiene lista de backups disponibles"""
        backups = []
        
        backup_dirs = {
            'daily': 'backups/daily',
            'weekly': 'backups/weekly', 
            'monthly': 'backups/monthly',
            'manual': 'backups',
            'incremental': 'backups/incremental'
        }
        
        for backup_type, backup_dir in backup_dirs.items():
            backup_path = self.project_path / backup_dir
            if backup_path.exists():
                for backup_file in backup_path.glob('*.zip'):
                    file_stat = backup_file.stat()
                    
                    # Buscar manifiesto
                    manifest_file = backup_file.parent / f"{backup_file.stem}_manifest.json"
                    manifest_data = {}
                    
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest_data = json.load(f)
                        except:
                            pass
                    
                    backups.append({
                        'name': backup_file.name,
                        'type': backup_type,
                        'path': str(backup_file),
                        'size_mb': file_stat.st_size / (1024 * 1024),
                        'created': datetime.fromtimestamp(file_stat.st_mtime),
                        'success': manifest_data.get('success', True),
                        'files_count': manifest_data.get('files_backed_up', 0)
                    })
        
        # Ordenar por fecha (más reciente primero)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

backup_interface = BackupWebInterface()

# Plantilla HTML principal
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Backup - Marketplace VUco</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .status-healthy { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-critical { color: #dc3545; }
        .status-unknown { color: #6c757d; }
        .backup-card { transition: transform 0.2s; }
        .backup-card:hover { transform: translateY(-2px); }
        .log-output { 
            background: #f8f9fa; 
            border: 1px solid #dee2e6; 
            border-radius: 0.375rem; 
            padding: 1rem; 
            font-family: 'Courier New', monospace; 
            font-size: 0.875rem;
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-database me-2"></i>
                Sistema de Backup - Marketplace VUco
            </a>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' if category == 'success' else 'info' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Estado del Sistema -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <i class="fas fa-heartbeat fa-2x status-{{ status.health_status }} mb-2"></i>
                        <h5 class="card-title">Estado del Sistema</h5>
                        <p class="card-text status-{{ status.health_status }}">
                            {% if status.health_status == 'healthy' %}Saludable
                            {% elif status.health_status == 'warning' %}Advertencia
                            {% elif status.health_status == 'critical' %}Crítico
                            {% elif status.health_status == 'no_backups' %}Sin Backups
                            {% else %}Desconocido{% endif %}
                        </p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <i class="fas fa-archive fa-2x text-info mb-2"></i>
                        <h5 class="card-title">Total Backups</h5>
                        <p class="card-text">{{ status.backup_count }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <i class="fas fa-hdd fa-2x text-secondary mb-2"></i>
                        <h5 class="card-title">Espacio Usado</h5>
                        <p class="card-text">{{ "%.1f"|format(status.total_size_mb) }} MB</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <i class="fas fa-clock fa-2x text-warning mb-2"></i>
                        <h5 class="card-title">Último Backup</h5>
                        <p class="card-text">
                            {% if status.last_backup %}
                                {{ status.last_backup.strftime('%d/%m/%Y %H:%M') }}
                            {% else %}
                                Nunca
                            {% endif %}
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Acciones Rápidas -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-bolt me-2"></i>Acciones Rápidas</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-success w-100" onclick="executeBackup('manual')">
                                    <i class="fas fa-play me-1"></i>Backup Manual
                                </button>
                            </div>
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-info w-100" onclick="executeBackup('incremental')">
                                    <i class="fas fa-layer-group me-1"></i>Incremental
                                </button>
                            </div>
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-warning w-100" onclick="checkHealth()">
                                    <i class="fas fa-stethoscope me-1"></i>Verificar Salud
                                </button>
                            </div>
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-secondary w-100" onclick="showLogs()">
                                    <i class="fas fa-file-alt me-1"></i>Ver Logs
                                </button>
                            </div>
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-primary w-100" onclick="location.reload()">
                                    <i class="fas fa-sync me-1"></i>Actualizar
                                </button>
                            </div>
                            <div class="col-md-2 mb-2">
                                <button class="btn btn-outline-danger w-100" onclick="showRestoreModal()">
                                    <i class="fas fa-undo me-1"></i>Restaurar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Lista de Backups -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-list me-2"></i>Backups Disponibles</h5>
                    </div>
                    <div class="card-body">
                        {% if backups %}
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Nombre</th>
                                            <th>Tipo</th>
                                            <th>Fecha</th>
                                            <th>Tamaño</th>
                                            <th>Estado</th>
                                            <th>Acciones</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for backup in backups %}
                                        <tr>
                                            <td>{{ backup.name }}</td>
                                            <td>
                                                <span class="badge bg-{% if backup.type == 'daily' %}primary{% elif backup.type == 'weekly' %}info{% elif backup.type == 'monthly' %}success{% elif backup.type == 'incremental' %}warning{% else %}secondary{% endif %}">
                                                    {{ backup.type.title() }}
                                                </span>
                                            </td>
                                            <td>{{ backup.created.strftime('%d/%m/%Y %H:%M') }}</td>
                                            <td>{{ "%.1f"|format(backup.size_mb) }} MB</td>
                                            <td>
                                                {% if backup.success %}
                                                    <i class="fas fa-check-circle text-success"></i> OK
                                                {% else %}
                                                    <i class="fas fa-exclamation-triangle text-warning"></i> Con errores
                                                {% endif %}
                                            </td>
                                            <td>
                                                <button class="btn btn-sm btn-outline-primary me-1" onclick="downloadBackup('{{ backup.path }}')">
                                                    <i class="fas fa-download"></i>
                                                </button>
                                                <button class="btn btn-sm btn-outline-success me-1" onclick="restoreBackup('{{ backup.path }}')">
                                                    <i class="fas fa-undo"></i>
                                                </button>
                                                <button class="btn btn-sm btn-outline-danger" onclick="deleteBackup('{{ backup.path }}')">
                                                    <i class="fas fa-trash"></i>
                                                </button>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="text-center py-4">
                                <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                                <h5 class="text-muted">No hay backups disponibles</h5>
                                <p class="text-muted">Ejecuta tu primer backup para comenzar</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal de Logs -->
    <div class="modal fade" id="logsModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Logs del Sistema</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="logsContent" class="log-output">
                        Cargando logs...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal de Progreso -->
    <div class="modal fade" id="progressModal" tabindex="-1" data-bs-backdrop="static">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Ejecutando Operación</h5>
                </div>
                <div class="modal-body text-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p id="progressText">Procesando...</p>
                    <div id="progressOutput" class="log-output mt-3" style="display: none;"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function executeBackup(type) {
            showProgress('Ejecutando backup ' + type + '...');
            
            fetch('/api/backup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type: type})
            })
            .then(response => response.json())
            .then(data => {
                hideProgress();
                if (data.success) {
                    showAlert('Backup ejecutado exitosamente', 'success');
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showAlert('Error ejecutando backup: ' + data.error, 'error');
                }
            })
            .catch(error => {
                hideProgress();
                showAlert('Error de conexión: ' + error, 'error');
            });
        }

        function checkHealth() {
            showProgress('Verificando salud del sistema...');
            
            fetch('/api/health')
            .then(response => response.json())
            .then(data => {
                hideProgress();
                showAlert('Verificación completada. Estado: ' + data.status, 'info');
            })
            .catch(error => {
                hideProgress();
                showAlert('Error verificando salud: ' + error, 'error');
            });
        }

        function showLogs() {
            fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                document.getElementById('logsContent').innerHTML = data.logs.replace(/\\n/g, '<br>');
                new bootstrap.Modal(document.getElementById('logsModal')).show();
            })
            .catch(error => {
                showAlert('Error cargando logs: ' + error, 'error');
            });
        }

        function downloadBackup(path) {
            window.open('/api/download?path=' + encodeURIComponent(path), '_blank');
        }

        function restoreBackup(path) {
            if (confirm('¿Estás seguro de que quieres restaurar este backup? Esta operación sobrescribirá los datos actuales.')) {
                showProgress('Restaurando backup...');
                
                fetch('/api/restore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path})
                })
                .then(response => response.json())
                .then(data => {
                    hideProgress();
                    if (data.success) {
                        showAlert('Backup restaurado exitosamente', 'success');
                    } else {
                        showAlert('Error restaurando backup: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    hideProgress();
                    showAlert('Error de conexión: ' + error, 'error');
                });
            }
        }

        function deleteBackup(path) {
            if (confirm('¿Estás seguro de que quieres eliminar este backup?')) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('Backup eliminado exitosamente', 'success');
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showAlert('Error eliminando backup: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showAlert('Error de conexión: ' + error, 'error');
                });
            }
        }

        function showProgress(text) {
            document.getElementById('progressText').textContent = text;
            new bootstrap.Modal(document.getElementById('progressModal')).show();
        }

        function hideProgress() {
            bootstrap.Modal.getInstance(document.getElementById('progressModal'))?.hide();
        }

        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Página principal"""
    status = backup_interface.get_backup_status()
    backups = backup_interface.get_backup_list()
    
    return render_template_string(HTML_TEMPLATE, status=status, backups=backups)

@app.route('/api/backup', methods=['POST'])
def api_backup():
    """API para ejecutar backups"""
    data = request.get_json()
    backup_type = data.get('type', 'manual')
    
    if backup_type == 'incremental':
        script = 'incremental_backup.py'
        args = ['backup']
    else:
        script = 'backup_system.py'
        args = ['backup', backup_type]
    
    result = backup_interface.run_command([sys.executable, script] + args)
    
    return jsonify({
        'success': result['success'],
        'output': result['stdout'],
        'error': result['stderr'] if not result['success'] else None
    })

@app.route('/api/health')
def api_health():
    """API para verificar salud del sistema"""
    result = backup_interface.run_command([sys.executable, 'backup_monitor.py', 'check'])
    
    return jsonify({
        'success': result['success'],
        'output': result['stdout'],
        'status': 'healthy' if result['success'] else 'error'
    })

@app.route('/api/logs')
def api_logs():
    """API para obtener logs"""
    logs_content = ""
    log_files = ['backup_system.log', 'restore_system.log', 'backup_monitor.log', 'incremental_backup.log']
    
    for log_file in log_files:
        log_path = backup_interface.project_path / log_file
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Mostrar últimas 50 líneas
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    logs_content += f"=== {log_file} ===\\n"
                    logs_content += "".join(recent_lines)
                    logs_content += "\\n\\n"
            except Exception as e:
                logs_content += f"Error leyendo {log_file}: {e}\\n\\n"
    
    if not logs_content:
        logs_content = "No se encontraron logs"
    
    return jsonify({'logs': logs_content})

@app.route('/api/download')
def api_download():
    """API para descargar backups"""
    backup_path = request.args.get('path')
    
    if not backup_path or not os.path.exists(backup_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    
    try:
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore', methods=['POST'])
def api_restore():
    """API para restaurar backups"""
    data = request.get_json()
    backup_path = data.get('path')
    
    if not backup_path or not os.path.exists(backup_path):
        return jsonify({'success': False, 'error': 'Archivo no encontrado'})
    
    result = backup_interface.run_command([
        sys.executable, 'restore_system.py', 'restore', backup_path
    ], timeout=600)  # 10 minutos timeout
    
    return jsonify({
        'success': result['success'],
        'output': result['stdout'],
        'error': result['stderr'] if not result['success'] else None
    })

@app.route('/api/delete', methods=['POST'])
def api_delete():
    """API para eliminar backups"""
    data = request.get_json()
    backup_path = data.get('path')
    
    if not backup_path or not os.path.exists(backup_path):
        return jsonify({'success': False, 'error': 'Archivo no encontrado'})
    
    try:
        os.remove(backup_path)
        
        # Eliminar manifiesto asociado si existe
        manifest_path = Path(backup_path).parent / f"{Path(backup_path).stem}_manifest.json"
        if manifest_path.exists():
            os.remove(manifest_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def main():
    """Función principal"""
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5001
    
    print(f"Iniciando interfaz web de backup en http://localhost:{port}")
    print("Presiona Ctrl+C para detener")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
