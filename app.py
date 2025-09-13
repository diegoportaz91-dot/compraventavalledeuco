import os
import logging
import hashlib
import secrets
from datetime import timedelta
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.permanent_session_lifetime = timedelta(minutes=15)

# configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///vehicle_marketplace.db")
# Fix for Heroku PostgreSQL URL format
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
    # Generar un salt aleatorio
    salt = secrets.token_hex(16)
    
    # Combinar contraseña con salt
    salted_password = password + salt
    
    # Generar hash SHA-256
    password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    
    # Combinar salt y hash
    full_hash = salt + password_hash
    
    return full_hash

# Import routes after db is initialized
import routes

# ========== RUTAS DE SISTEMA DE BACKUP ==========
from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
from pathlib import Path
import subprocess
import sys

def admin_required(f):
    """Decorador para requerir autenticación de administrador"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
            flash('Acceso denegado. Debes iniciar sesión como administrador.', 'error')
            return redirect('/panel')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/backup')
@admin_required
def admin_backup_dashboard():
    """Panel de control de backup en el admin"""
    try:
        from backup_system.backup_integration import BackupIntegration
        backup_integration = BackupIntegration()
        status = backup_integration.get_backup_status()
        
        # Obtener lista de backups recientes
        backup_dirs = ['backups/daily', 'backups/weekly', 'backups/monthly', 'backups']
        recent_backups = []
        
        for backup_dir in backup_dirs:
            backup_path = Path(backup_dir)
            if backup_path.exists():
                for backup_file in backup_path.glob('*.zip'):
                    file_stat = backup_file.stat()
                    recent_backups.append({
                        'name': backup_file.name,
                        'path': str(backup_file),
                        'size': file_stat.st_size,
                        'date': datetime.fromtimestamp(file_stat.st_mtime),
                        'type': backup_dir.split('/')[-1] if '/' in backup_dir else 'manual'
                    })
        
        # Ordenar por fecha (más recientes primero)
        recent_backups.sort(key=lambda x: x['date'], reverse=True)
        recent_backups = recent_backups[:10]  # Solo los 10 más recientes
        
        return render_template('admin_backup_dashboard.html', 
                             backup_status=status, 
                             recent_backups=recent_backups)
    except Exception as e:
        flash(f'Error al cargar panel de backup: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/backup/run', methods=['POST'])
@admin_required
def admin_run_backup():
    """Ejecutar backup desde el panel admin"""
    try:
        from backup_system.backup_integration import BackupIntegration
        
        backup_integration = BackupIntegration()
        backup_type = request.form.get('type', 'manual')
        
        if backup_type == 'incremental':
            result = subprocess.run([
                sys.executable,
                str(Path(__file__).parent / 'backup_system' / 'incremental_backup.py'),
                'backup'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                flash('Backup incremental ejecutado exitosamente', 'success')
            else:
                flash(f'Error en backup incremental: {result.stderr}', 'error')
        else:
            result = backup_integration.run_manual_backup()
            
            if result and result.get('success', True):
                flash('Backup manual ejecutado exitosamente', 'success')
            else:
                flash(f'Error en backup manual: {result.get("error", "Error desconocido")}', 'error')
        
        return redirect(url_for('admin_backup_dashboard'))
    except Exception as e:
        flash(f'Error ejecutando backup: {str(e)}', 'error')
        return redirect(url_for('admin_backup_dashboard'))

@app.route('/admin/backup/status')
@admin_required
def admin_backup_status():
    """API para obtener estado del backup"""
    try:
        from backup_system.backup_integration import BackupIntegration
        backup_integration = BackupIntegration()
        status = backup_integration.get_backup_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/backup/interface')
@admin_required
def admin_backup_interface():
    """Redirige a la interfaz web completa de backup"""
    return redirect('http://localhost:5001')

# Initialize database and create admin user
with app.app_context():
    # Create all tables
    db.create_all()
    
    # Create admin user if not exists
    from models import Admin
    
    # Solo crear admin si no existe para mantener ID consistente
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
        # Actualizar contraseña si cambió
        admin_password = os.environ.get("ADMIN_PASSWORD", "DiegoPortaz7")
        new_hash = generate_password_hash_sha256(admin_password)
        if existing_admin.password_hash != new_hash:
            existing_admin.password_hash = new_hash
            db.session.commit()
            logging.info("Admin password updated")
        logging.info("Admin user already exists with ID: " + str(existing_admin.id))

# Inicializar sistema de backup integrado
from backup_system.backup_integration import init_backup_system
backup_system = init_backup_system(app)
logging.info("Sistema de backup integrado y activo")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)