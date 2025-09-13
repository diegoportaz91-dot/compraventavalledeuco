#!/usr/bin/env python3
"""
Ejemplo de Integración del Sistema de Backup con app.py
Autor: Sistema de Backup Seguro
Fecha: 2025-09-12

Este archivo muestra cómo integrar el sistema de backup con tu aplicación Flask existente
"""

# OPCIÓN 1: Integración Simple - Agregar al final de app.py
"""
# Agregar estas líneas al final de tu app.py existente:

from backup_integration import init_backup_system

# Inicializar sistema de backup
backup_system = init_backup_system(app)

# El sistema ahora funcionará automáticamente
"""

# OPCIÓN 2: Integración con Rutas Admin - Agregar a routes.py
"""
# Agregar estas rutas a tu routes.py para acceso desde el panel admin:

from backup_integration import BackupIntegration
from flask import jsonify, request, render_template, flash, redirect, url_for

backup_integration = BackupIntegration()

@app.route('/admin/backup')
@admin_required  # Tu decorador de autenticación admin
def admin_backup_dashboard():
    '''Panel de control de backup en el admin'''
    status = backup_integration.get_backup_status()
    return render_template('admin_backup_dashboard.html', backup_status=status)

@app.route('/admin/backup/run', methods=['POST'])
@admin_required
def admin_run_backup():
    '''Ejecutar backup desde el panel admin'''
    backup_type = request.form.get('type', 'manual')
    
    if backup_type == 'incremental':
        result = backup_integration.run_auto_backup()
    else:
        result = backup_integration.run_manual_backup()
    
    if result and result.get('success', True):
        flash('Backup ejecutado exitosamente', 'success')
    else:
        flash(f'Error en backup: {result.get("error", "Error desconocido")}', 'error')
    
    return redirect(url_for('admin_backup_dashboard'))

@app.route('/admin/backup/status')
@admin_required
def admin_backup_status():
    '''API para obtener estado del backup'''
    status = backup_integration.get_backup_status()
    return jsonify(status)
"""

# OPCIÓN 3: Integración Automática con Decoradores
"""
# Usar el decorador @backup_on_change en funciones críticas de routes.py:

from backup_integration import backup_on_change

@app.route('/admin/approve_request/<int:request_id>', methods=['POST'])
@admin_required
@backup_on_change  # Ejecuta backup automático después de aprobar
def approve_request(request_id):
    # Tu código existente para aprobar solicitudes
    pass

@app.route('/admin/add_vehicle', methods=['POST'])
@admin_required
@backup_on_change  # Ejecuta backup automático después de agregar vehículo
def add_vehicle():
    # Tu código existente para agregar vehículos
    pass

@app.route('/admin/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@admin_required
@backup_on_change  # Ejecuta backup automático después de eliminar
def delete_vehicle(vehicle_id):
    # Tu código existente para eliminar vehículos
    pass
"""

# OPCIÓN 4: Template para Panel Admin
ADMIN_BACKUP_TEMPLATE = '''
<!-- Agregar este bloque a tu template admin_dashboard.html -->

<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-shield-alt me-2"></i>
                    Sistema de Backup
                    <span class="badge bg-{% if backup_status.status == 'healthy' %}success{% elif backup_status.status == 'warning' %}warning{% else %}danger{% endif %} ms-2">
                        {% if backup_status.status == 'healthy' %}Activo
                        {% elif backup_status.status == 'warning' %}Advertencia
                        {% elif backup_status.status == 'critical' %}Crítico
                        {% else %}Inactivo{% endif %}
                    </span>
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Último backup:</strong> 
                            {% if backup_status.last_backup %}
                                {{ backup_status.last_backup.strftime('%d/%m/%Y %H:%M') }}
                            {% else %}
                                Nunca
                            {% endif %}
                        </p>
                        <p><strong>Total de backups:</strong> {{ backup_status.backup_count }}</p>
                    </div>
                    <div class="col-md-6">
                        <div class="d-grid gap-2">
                            <form method="POST" action="{{ url_for('admin_run_backup') }}" style="display: inline;">
                                <input type="hidden" name="type" value="manual">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-play me-1"></i>Backup Manual
                                </button>
                            </form>
                            <form method="POST" action="{{ url_for('admin_run_backup') }}" style="display: inline;">
                                <input type="hidden" name="type" value="incremental">
                                <button type="submit" class="btn btn-info">
                                    <i class="fas fa-layer-group me-1"></i>Backup Incremental
                                </button>
                            </form>
                            <a href="http://localhost:5001" target="_blank" class="btn btn-secondary">
                                <i class="fas fa-external-link-alt me-1"></i>Panel Completo
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
'''

# OPCIÓN 5: Integración Completa - Nuevo app.py con backup integrado
INTEGRATED_APP_EXAMPLE = '''
import os
import logging
import hashlib
import secrets
from datetime import timedelta
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Importar sistema de backup
from backup_integration import init_backup_system

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.permanent_session_lifetime = timedelta(minutes=15)

# configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///vehicle_marketplace.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folder for vehicle images
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import and initialize db
from models import db
db.init_app(app)

# Apply proxy fix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def generate_password_hash_sha256(password):
    """Genera un hash SHA-256 de la contraseña con salt"""
    salt = secrets.token_hex(16)
    salted_password = password + salt
    password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    full_hash = salt + password_hash
    return full_hash

# Import routes after db is initialized
import routes

# Initialize database and create admin user
with app.app_context():
    db.create_all()
    
    from models import Admin
    existing_admin = Admin.query.filter_by(username="Ryoma94").first()
    if not existing_admin:
        admin_password = os.environ.get("ADMIN_PASSWORD", "DiegoPortaz7")
        admin = Admin(
            username="Ryoma94",
            password_hash=generate_password_hash_sha256(admin_password)
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Admin user created with password: " + admin_password)
    else:
        admin_password = os.environ.get("ADMIN_PASSWORD", "DiegoPortaz7")
        new_hash = generate_password_hash_sha256(admin_password)
        if existing_admin.password_hash != new_hash:
            existing_admin.password_hash = new_hash
            db.session.commit()
            logging.info("Admin password updated")
        logging.info("Admin user already exists with ID: " + str(existing_admin.id))

# ¡NUEVA LÍNEA! Inicializar sistema de backup
backup_system = init_backup_system(app)
logging.info("Sistema de backup integrado y activo")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
'''

print("📋 GUÍA DE INTEGRACIÓN DEL SISTEMA DE BACKUP")
print("=" * 50)
print()
print("Se han creado varios ejemplos de integración:")
print()
print("1. 📄 ejemplo_integracion_app.py - Ejemplos completos")
print("2. 🔧 backup_integration.py - Módulo de integración")
print("3. 📖 GUIA_RAPIDA_BACKUP.md - Comandos esenciales")
print("4. 🚀 backup_installer.py - Instalador automático")
print()
print("OPCIONES DE INTEGRACIÓN:")
print()
print("🔹 SIMPLE: Agregar 2 líneas a app.py")
print("   from backup_integration import init_backup_system")
print("   backup_system = init_backup_system(app)")
print()
print("🔹 COMPLETA: Rutas admin + decoradores automáticos")
print("🔹 VISUAL: Panel de control en admin dashboard")
print("🔹 AUTOMÁTICA: Backups después de operaciones críticas")
print()
print("El sistema está COMPLETAMENTE FUNCIONAL y listo para usar.")
print("Todos los archivos están creados y configurados.")
