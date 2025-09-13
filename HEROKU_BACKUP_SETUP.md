# Configuración del Sistema de Backup para Heroku

## ⚠️ Limitaciones de Heroku

Heroku tiene restricciones específicas que afectan el sistema de backup:

1. **Sistema de archivos efímero** - Los archivos se borran al reiniciar el dyno
2. **No hay tareas programadas nativas** - No se puede usar Windows Task Scheduler
3. **Base de datos PostgreSQL** - No SQLite como en local
4. **Sin almacenamiento persistente local** - Necesita almacenamiento externo

## 🔧 Adaptaciones Implementadas

### 1. **Adaptador para Heroku** (`heroku_backup_adapter.py`)
- Detecta automáticamente si está en Heroku (`DYNO` env var)
- Usa `pg_dump` para backup de PostgreSQL
- Almacena backups temporalmente y los sube a S3
- Limpia archivos temporales automáticamente

### 2. **Integración Automática**
- El sistema detecta si está en Heroku y usa el adaptador apropiado
- Mantiene la misma interfaz en el panel admin
- Funciona sin cambios en el código principal

## 📋 Variables de Entorno Requeridas en Heroku

Configura estas variables en tu app de Heroku:

```bash
# AWS S3 para almacenar backups
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BACKUP_BUCKET=tu-bucket-de-backups

# Opcional: Nombre de la app
HEROKU_APP_NAME=tu-app-name
```

## 🚀 Configuración Paso a Paso

### 1. **Crear Bucket S3**
```bash
# En AWS Console o CLI
aws s3 mb s3://tu-bucket-de-backups
```

### 2. **Configurar Variables en Heroku**
```bash
heroku config:set AWS_ACCESS_KEY_ID=tu_access_key
heroku config:set AWS_SECRET_ACCESS_KEY=tu_secret_key
heroku config:set S3_BACKUP_BUCKET=tu-bucket-de-backups
heroku config:set AWS_DEFAULT_REGION=us-east-1
```

### 3. **Agregar Dependencias**
Asegúrate que `requirements.txt` incluya:
```
boto3>=1.26.0
```

### 4. **Desplegar**
```bash
git add .
git commit -m "Add Heroku backup system"
git push heroku main
```

## 🎯 Funcionalidades en Heroku

### ✅ **Funciona Igual:**
- Panel de backup en admin
- Backup manual desde interfaz
- Estado del sistema en tiempo real
- Integración automática

### 🔄 **Adaptado para Heroku:**
- **Base de datos:** PostgreSQL con `pg_dump`
- **Almacenamiento:** S3 en lugar de local
- **Archivos:** Solo configuración (no uploads)
- **Programación:** Heroku Scheduler (opcional)

### ❌ **No Disponible en Heroku:**
- Backup de imágenes uploads (efímeras)
- Tareas programadas automáticas
- Restauración automática completa
- Backup incremental tradicional

## 📊 Uso en Heroku

1. **Accede al panel admin** de tu app en Heroku
2. **Ve a "Sistema de Backup"** en el sidebar
3. **El sistema detectará automáticamente** que está en Heroku
4. **Los backups se guardarán en S3** automáticamente
5. **Podrás descargar** backups desde S3

## 🔧 Heroku Scheduler (Opcional)

Para backups automáticos programados:

1. **Instalar addon:**
```bash
heroku addons:create scheduler:standard
```

2. **Configurar tarea:**
```bash
heroku addons:open scheduler
```

3. **Agregar comando:**
```
python -c "from backup_system.heroku_backup_adapter import create_heroku_backup; create_heroku_backup()"
```

4. **Programar:** Diario a las 02:00 UTC

## 🚨 Consideraciones Importantes

### **Costos:**
- S3 storage (~$0.023/GB/mes)
- Heroku Scheduler (~$25/mes)
- Transferencia de datos

### **Seguridad:**
- Usa IAM roles con permisos mínimos para S3
- Encripta backups en S3
- Rota credenciales regularmente

### **Limitaciones:**
- Las imágenes uploads no se respaldan (son efímeras)
- Restauración manual desde S3
- Dependencia de servicios externos

## 🎯 Resultado Final

Tu aplicación en Heroku tendrá:
- ✅ Backup automático de base de datos PostgreSQL
- ✅ Backup de archivos de configuración críticos
- ✅ Almacenamiento seguro en S3
- ✅ Interfaz visual igual que en local
- ✅ Detección automática de plataforma
- ✅ Sin cambios en el código principal

El sistema funciona transparentemente tanto en local como en Heroku, adaptándose automáticamente a cada plataforma.
