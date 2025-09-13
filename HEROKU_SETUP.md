# Configuración para Heroku

## Variables de Entorno Requeridas

Antes de desplegar en Heroku, debes configurar las siguientes variables de entorno en tu aplicación:

### Variables Obligatorias:

1. **DATABASE_URL**: Se configura automáticamente cuando agregas el addon de PostgreSQL
   ```
   heroku addons:create heroku-postgresql:mini
   ```

2. **SESSION_SECRET**: Clave secreta para las sesiones
   ```
   heroku config:set SESSION_SECRET="tu-clave-secreta-muy-segura-aqui"
   ```

3. **ADMIN_PASSWORD**: Contraseña del administrador
   ```
   heroku config:set ADMIN_PASSWORD="tu-password-admin-seguro"
   ```

## Comandos para Desplegar

1. **Crear aplicación en Heroku:**
   ```bash
   heroku create tu-nombre-app
   ```

2. **Agregar PostgreSQL:**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Configurar variables de entorno:**
   ```bash
   heroku config:set SESSION_SECRET="clave-secreta-muy-larga-y-segura"
   heroku config:set ADMIN_PASSWORD="password-admin-seguro"
   ```

4. **Desplegar:**
   ```bash
   git add .
   git commit -m "Configuración para Heroku"
   git push heroku main
   ```

5. **Inicializar base de datos:**
   ```bash
   heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

## Archivos Configurados

- ✅ `Procfile`: Configurado para usar gunicorn
- ✅ `requirements.txt`: Todas las dependencias incluidas
- ✅ `runtime.txt`: Python 3.11.6
- ✅ `app.py`: Puerto dinámico y configuración de base de datos
- ✅ `.gitignore`: Archivos excluidos del repositorio
- ✅ Estructura de carpetas estáticas creada

## Notas Importantes

- La aplicación usará PostgreSQL en producción (Heroku) y SQLite en desarrollo local
- Los archivos subidos se almacenarán en el sistema de archivos de Heroku (temporal)
- Para archivos permanentes, considera usar un servicio como AWS S3
- El modo debug está desactivado en producción por seguridad
