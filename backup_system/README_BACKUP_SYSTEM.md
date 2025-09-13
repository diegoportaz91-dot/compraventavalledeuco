# Sistema de Backup Seguro para Marketplace de Vehículos

## 📋 Descripción General

Este sistema de backup automatizado protege todos los datos críticos de tu aplicación de marketplace de vehículos, incluyendo:

- **Base de datos SQLite** (`vehicle_marketplace.db`)
- **Imágenes de vehículos** (`static/uploads/`)
- **Imágenes de gestores** (`static/uploads/gestores/`)
- **Archivos de configuración** (app.py, models.py, routes.py, etc.)

## 🚀 Instalación Rápida

### 1. Instalar Dependencias

```bash
pip install schedule paramiko dropbox google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Configurar Backups Automáticos

```bash
# Configurar tareas programadas en Windows
python backup_scheduler.py setup

# Verificar configuración
python backup_scheduler.py list
```

### 3. Ejecutar Primer Backup

```bash
# Backup manual de prueba
python backup_system.py backup manual
```

## 📁 Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `backup_system.py` | Sistema principal de backup |
| `restore_system.py` | Sistema de restauración |
| `cloud_backup.py` | Sincronización con la nube |
| `backup_scheduler.py` | Programador automático |

## ⚙️ Configuración

### Backup Local

El sistema crea automáticamente la siguiente estructura:

```
backups/
├── daily/          # Backups diarios
├── weekly/         # Backups semanales
├── monthly/        # Backups mensuales
└── *.zip           # Backups manuales
```

### Configuración de Nube (Opcional)

#### Google Drive
```bash
python cloud_backup.py setup google_drive
```

#### Dropbox
```bash
python cloud_backup.py setup dropbox
```

#### FTP/SFTP
```bash
python cloud_backup.py setup ftp
python cloud_backup.py setup sftp
```

## 🔄 Programación Automática

### Horarios por Defecto

- **Diario**: 02:00 AM
- **Semanal**: Domingos 02:30 AM
- **Mensual**: Día 1 de cada mes 03:00 AM
- **Limpieza**: Diaria 04:00 AM (elimina backups > 30 días)

### Comandos de Programación

```bash
# Configurar todas las tareas
python backup_scheduler.py setup

# Ver tareas programadas
python backup_scheduler.py list

# Eliminar todas las tareas
python backup_scheduler.py delete

# Probar backup manual
python backup_scheduler.py test
```

## 💾 Uso del Sistema de Backup

### Backups Manuales

```bash
# Backup completo manual
python backup_system.py backup manual

# Backup diario programado
python backup_system.py backup daily

# Backup semanal programado
python backup_system.py backup weekly

# Backup mensual programado
python backup_system.py backup monthly

# Limpiar backups antiguos
python backup_system.py cleanup
```

### Sincronización con la Nube

```bash
# Sincronizar backup específico
python cloud_backup.py sync backups/backup_manual_20250912_231624.zip

# Ver servicios configurados
python cloud_backup.py status
```

## 🔧 Sistema de Restauración

### Listar Backups Disponibles

```bash
python restore_system.py list
```

### Restauración Completa

```bash
# Restaurar todo desde un backup específico
python restore_system.py restore backups/daily/backup_daily_20250912_020000.zip

# Restaurar solo la base de datos
python restore_system.py restore backup.zip database

# Restaurar solo imágenes
python restore_system.py restore backup.zip uploads

# Restaurar solo configuración
python restore_system.py restore backup.zip config
```

### Modo Interactivo

```bash
# Ejecutar sin parámetros para modo interactivo
python restore_system.py
```

## 🛡️ Características de Seguridad

### Verificación de Integridad

- **Base de datos**: Verificación PRAGMA integrity_check
- **Archivos**: Checksums SHA-256
- **Backups**: Verificación de integridad ZIP
- **Inventario**: Registro detallado de todos los archivos

### Backup de Seguridad

Antes de cada restauración, el sistema:
1. Crea un backup automático del estado actual
2. Verifica la integridad del backup a restaurar
3. Permite cancelar si hay problemas

### Retención de Datos

- **Retención por defecto**: 30 días
- **Limpieza automática**: Diaria a las 04:00 AM
- **Backups de seguridad**: Se mantienen durante restauraciones

## 📊 Monitoreo y Logs

### Archivos de Log

- `backup_system.log` - Logs del sistema de backup
- `restore_system.log` - Logs de restauración
- `backup_scheduler.log` - Logs del programador

### Manifiestos de Backup

Cada backup incluye un archivo `*_manifest.json` con:
- Fecha y hora del backup
- Tipo de backup (manual, daily, weekly, monthly)
- Archivos incluidos y tamaños
- Checksums de verificación
- Estado de éxito/error

## 🚨 Recuperación de Desastres

### Escenario 1: Pérdida de Base de Datos

```bash
# 1. Listar backups disponibles
python restore_system.py list

# 2. Restaurar solo la base de datos
python restore_system.py restore backup_reciente.zip database
```

### Escenario 2: Pérdida de Imágenes

```bash
# Restaurar solo las imágenes
python restore_system.py restore backup_reciente.zip uploads
```

### Escenario 3: Pérdida Completa

```bash
# 1. Reinstalar aplicación
# 2. Restaurar backup completo más reciente
python restore_system.py restore backup_completo.zip

# 3. Verificar funcionamiento
python backup_scheduler.py test
```

## ⚠️ Consideraciones Importantes

### Antes de Usar

1. **Probar el sistema** con backups de prueba
2. **Verificar permisos** de escritura en carpetas
3. **Configurar exclusiones** de antivirus si es necesario
4. **Documentar credenciales** de servicios en la nube

### Mejores Prácticas

1. **Verificar backups regularmente**
   ```bash
   python restore_system.py list
   ```

2. **Probar restauraciones periódicamente**
   ```bash
   python backup_scheduler.py test
   ```

3. **Monitorear logs de errores**
   ```bash
   type backup_system.log | findstr ERROR
   ```

4. **Mantener múltiples copias**
   - Local: Backups automáticos
   - Nube: Sincronización automática
   - Externa: Copias manuales ocasionales

### Limitaciones

- **Tamaño máximo**: Depende del espacio disponible
- **Servicios en la nube**: Requieren configuración adicional
- **Windows Task Scheduler**: Requiere permisos de administrador
- **Restauración**: Detiene temporalmente la aplicación

## 🔧 Configuración Avanzada

### Personalizar Horarios

Editar `backup_config.json`:

```json
{
  "backup_schedule": {
    "daily": "03:00",
    "weekly": "monday", 
    "monthly": 15
  },
  "retention_days": 60,
  "compression_level": 9
}
```

### Configurar Exclusiones

```json
{
  "config_files": [
    "app.py",
    "models.py",
    "routes.py",
    "requirements.txt"
  ]
}
```

### Configuración de Nube

Editar `cloud_backup_config.json`:

```json
{
  "enabled_services": ["dropbox", "google_drive"],
  "dropbox": {
    "enabled": true,
    "access_token": "tu_token_aqui",
    "folder_path": "/marketplace_backups"
  }
}
```

## 📞 Soporte y Solución de Problemas

### Problemas Comunes

**Error: "No se puede acceder a la base de datos"**
- Verificar que la aplicación esté detenida
- Comprobar permisos de archivo
- Verificar espacio en disco

**Error: "Tarea programada no se ejecuta"**
- Verificar permisos de administrador
- Comprobar que Python esté en PATH
- Revisar logs del sistema

**Error: "Backup corrupto"**
- Verificar integridad con `restore_system.py list`
- Usar backup anterior
- Revisar espacio en disco durante backup

### Comandos de Diagnóstico

```bash
# Verificar configuración
python backup_system.py

# Probar conectividad de nube
python cloud_backup.py status

# Verificar tareas programadas
python backup_scheduler.py list

# Verificar integridad de backups
python restore_system.py list
```

## 📈 Estadísticas y Reportes

El sistema genera automáticamente:

- **Manifiestos de backup** con metadatos completos
- **Logs detallados** de todas las operaciones
- **Inventarios de archivos** con checksums
- **Reportes de sincronización** con servicios en la nube

## 🔄 Actualizaciones del Sistema

Para mantener el sistema actualizado:

1. **Revisar logs regularmente**
2. **Probar restauraciones mensualmente**
3. **Actualizar credenciales de nube según sea necesario**
4. **Ajustar retención según crecimiento de datos**

---

## 📋 Lista de Verificación de Implementación

- [ ] Instalar dependencias Python
- [ ] Configurar tareas programadas
- [ ] Ejecutar primer backup de prueba
- [ ] Configurar al menos un servicio en la nube
- [ ] Probar restauración completa
- [ ] Documentar credenciales y configuración
- [ ] Establecer monitoreo de logs
- [ ] Programar verificaciones mensuales

**¡Tu sistema de backup está listo para proteger tu marketplace de vehículos!** 🚗💾
