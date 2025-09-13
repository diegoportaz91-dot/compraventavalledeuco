# 🚀 Guía Rápida - Sistema de Backup

## ⚡ Comandos Esenciales

### Backups Inmediatos
```bash
# Backup completo manual
python backup_system.py backup manual

# Backup incremental (más rápido)
python incremental_backup.py backup

# Verificar estado del sistema
python backup_monitor.py check
```

### Restauración
```bash
# Ver backups disponibles
python restore_system.py list

# Restaurar (modo interactivo)
python restore_system.py

# Restaurar archivo específico
python restore_system.py restore ruta/al/backup.zip
```

### Interfaz Web
```bash
# Iniciar panel de control web
python backup_web_interface.py 5001

# Acceder en navegador
http://localhost:5001
```

## 📊 Estado Actual

- ✅ **Sistema**: Funcionando
- ✅ **Tareas Programadas**: 4/4 activas
- ✅ **Último Backup**: Automático
- ✅ **Espacio**: 23+ GB disponibles

## ⏰ Programación Automática

| Tipo | Frecuencia | Hora |
|------|------------|------|
| Diario | Todos los días | 02:00 AM |
| Semanal | Domingos | 02:30 AM |
| Mensual | Día 1 | 03:00 AM |
| Limpieza | Diario | 04:00 AM |

## 🛡️ Archivos Protegidos

- Base de datos SQLite
- Imágenes de vehículos (`static/uploads/`)
- Imágenes de gestores
- Archivos de configuración

## 🚨 En Caso de Emergencia

1. **Pérdida de datos**:
   ```bash
   python restore_system.py list
   python restore_system.py
   ```

2. **Sistema no funciona**:
   ```bash
   python backup_monitor.py check
   python backup_scheduler.py list
   ```

3. **Backup manual urgente**:
   ```bash
   python backup_system.py backup manual
   ```

## ☁️ Configuración Opcional

### Alertas por Email
```bash
python backup_monitor.py setup-email
```

### Sincronización en la Nube
```bash
python cloud_backup.py setup dropbox
python cloud_backup.py setup google_drive
```

## 📱 Panel Web - Funciones

- **Dashboard**: Estado en tiempo real
- **Backup Manual**: Ejecutar inmediatamente
- **Restaurar**: Desde cualquier backup
- **Descargar**: Backups localmente
- **Logs**: Ver actividad del sistema
- **Monitoreo**: Salud del sistema

## 🔧 Solución de Problemas

### Error: "No se encuentra la base de datos"
- Normal si la app no se ha ejecutado aún
- El backup continuará con imágenes y configuración

### Error: "Tareas programadas no funcionan"
```bash
python backup_scheduler.py setup
```

### Error: "Espacio insuficiente"
```bash
python backup_system.py cleanup
```

### Verificar instalación
```bash
python backup_installer.py --verify
```

## 📞 Comandos de Diagnóstico

```bash
# Estado completo del sistema
python backup_monitor.py check

# Ver tareas programadas
python backup_scheduler.py list

# Verificar backups incrementales
python incremental_backup.py status

# Probar backup
python backup_scheduler.py test
```

---

**💡 Tip**: Usa la interfaz web (`python backup_web_interface.py 5001`) para gestión visual completa del sistema.
