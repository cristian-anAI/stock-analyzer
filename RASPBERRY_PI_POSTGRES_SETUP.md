# PostgreSQL en Raspberry Pi - Guía Completa de Instalación

Esta guía te ayudará a instalar y configurar PostgreSQL en tu Raspberry Pi para que funcione como base de datos centralizada 24/7 para Stock Analyzer.

## Requisitos

- **Raspberry Pi** (3, 4, o 5) con Raspberry Pi OS instalado
- **Conexión a internet**
- **Espacio en disco**: Mínimo 2GB libres (recomendado 8GB+)
- **Acceso SSH** o teclado/monitor conectado
- **IP fija** o hostname estable en tu red local

---

## 1. Preparación del Sistema

### 1.1. Actualizar el sistema

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2. Verificar espacio disponible

```bash
df -h
```

Asegúrate de tener al menos 2GB libres en `/`.

---

## 2. Instalación de PostgreSQL

### 2.1. Instalar PostgreSQL

```bash
sudo apt install postgresql postgresql-contrib -y
```

### 2.2. Verificar instalación

```bash
sudo systemctl status postgresql
```

Deberías ver `active (running)`.

### 2.3. Verificar versión

```bash
psql --version
```

Debería mostrar algo como `psql (PostgreSQL) 13.x` o superior.

---

## 3. Configuración Inicial de PostgreSQL

### 3.1. Acceder a PostgreSQL como superusuario

```bash
sudo -u postgres psql
```

Verás el prompt de PostgreSQL: `postgres=#`

### 3.2. Crear usuario para Stock Analyzer

```sql
CREATE USER stock_analyzer_user WITH PASSWORD 'TU_CONTRASEÑA_SEGURA_AQUI';
```

**IMPORTANTE**: Cambia `TU_CONTRASEÑA_SEGURA_AQUI` por una contraseña fuerte.

### 3.3. Crear base de datos de producción

```sql
CREATE DATABASE stock_analyzer_prod OWNER stock_analyzer_user;
```

### 3.4. Otorgar permisos

```sql
GRANT ALL PRIVILEGES ON DATABASE stock_analyzer_prod TO stock_analyzer_user;
```

### 3.5. Salir de psql

```sql
\q
```

---

## 4. Configurar Acceso Remoto

Por defecto, PostgreSQL solo acepta conexiones locales. Necesitas habilitar acceso desde tu PC de desarrollo.

### 4.1. Obtener IP de la Raspberry Pi

```bash
hostname -I
```

Ejemplo: `192.168.1.50`

**IMPORTANTE**: Apunta esta IP, la necesitarás más adelante.

### 4.2. Editar postgresql.conf

```bash
sudo nano /etc/postgresql/13/main/postgresql.conf
```

**Nota**: La versión puede variar (13, 14, 15). Ajusta según tu versión.

Busca la línea:

```conf
#listen_addresses = 'localhost'
```

Cámbiala a:

```conf
listen_addresses = '*'
```

Guarda con `Ctrl+O`, Enter, `Ctrl+X`.

### 4.3. Editar pg_hba.conf

```bash
sudo nano /etc/postgresql/13/main/pg_hba.conf
```

Al **final del archivo**, agrega:

```conf
# Permitir conexiones desde la red local
host    all             all             192.168.1.0/24          md5
```

**IMPORTANTE**: Ajusta `192.168.1.0/24` según tu red local.
- Si tu red es `192.168.0.x`, usa `192.168.0.0/24`
- Si tu red es `10.0.0.x`, usa `10.0.0.0/24`

Guarda con `Ctrl+O`, Enter, `Ctrl+X`.

### 4.4. Reiniciar PostgreSQL

```bash
sudo systemctl restart postgresql
```

### 4.5. Verificar que escucha en todas las interfaces

```bash
sudo ss -tunlp | grep 5432
```

Deberías ver algo como:

```
tcp   LISTEN 0      128       0.0.0.0:5432       0.0.0.0:*    users:(("postgres",pid=1234,fd=5))
```

Si ves `0.0.0.0:5432`, está correcto.

---

## 5. Transferir Schema a Raspberry Pi

### 5.1. Desde tu PC, copiar schema.sql a la Raspberry

**Opción A: Con SCP (recomendado)**

```bash
scp database/schema.sql pi@192.168.1.50:/home/pi/
```

Cambia `192.168.1.50` por la IP de tu Raspberry.

**Opción B: Copiar manualmente**

1. Abre `database/schema.sql` en tu PC
2. Copia todo el contenido
3. En la Raspberry, ejecuta:

```bash
nano ~/schema.sql
```

4. Pega el contenido, guarda con `Ctrl+O`, Enter, `Ctrl+X`

### 5.2. Ejecutar el schema en PostgreSQL

```bash
sudo -u postgres psql -d stock_analyzer_prod -f /home/pi/schema.sql
```

Verás muchos mensajes de `CREATE TABLE`, `CREATE INDEX`, etc.

### 5.3. Verificar que las tablas se crearon

```bash
sudo -u postgres psql -d stock_analyzer_prod
```

Dentro de psql:

```sql
\dt
```

Deberías ver las 18 tablas listadas.

```sql
\q
```

---

## 6. Probar Conexión desde tu PC

### 6.1. Instalar psycopg2 en tu PC (si no lo has hecho)

```bash
pip install psycopg2-binary python-dotenv
```

### 6.2. Actualizar .env.prod en tu PC

Edita `c:\repos\stock-analyzer\.env.prod`:

```env
# Database Configuration
POSTGRES_DB=stock_analyzer_prod
POSTGRES_USER=stock_analyzer_user
POSTGRES_PASSWORD=TU_CONTRASEÑA_SEGURA_AQUI
POSTGRES_HOST=192.168.1.50  # IP de tu Raspberry Pi
POSTGRES_PORT=5432

# Database URL (para SQLAlchemy)
DATABASE_URL=postgresql://stock_analyzer_user:TU_CONTRASEÑA_SEGURA_AQUI@192.168.1.50:5432/stock_analyzer_prod
```

**IMPORTANTE**: Cambia:
- `TU_CONTRASEÑA_SEGURA_AQUI` por la contraseña que creaste
- `192.168.1.50` por la IP de tu Raspberry

### 6.3. Probar conexión con Python

```bash
python src/api/database/database_postgres.py
```

Deberías ver:

```
=== PostgreSQL Database Verification ===

1. Verifying schema...
✓ Table 'system_config' exists
✓ Table 'market_status' exists
...
✓ PostgreSQL database is working correctly!
```

---

## 7. Migrar Datos de SQLite a PostgreSQL

### 7.1. Ejecutar script de migración

```bash
python database/migrate_sqlite_to_postgres.py
```

El script:
1. Lee todos los datos de `trading.db` (SQLite)
2. Los inserta en PostgreSQL en la Raspberry
3. Verifica que todo se migró correctamente

### 7.2. Verificar migración

Deberías ver:

```
✓ Migrated 17 rows from 'positions'
✓ Migrated 43 rows from 'autotrader_transactions'
...
✓ Migration verification PASSED
```

---

## 8. Configurar Backup Automático (Recomendado)

### 8.1. Crear script de backup en la Raspberry

```bash
sudo nano /home/pi/backup_postgres.sh
```

Contenido:

```bash
#!/bin/bash

# Configuración
BACKUP_DIR="/home/pi/postgres_backups"
DATE=$(date +"%Y%m%d_%H%M%S")
DB_NAME="stock_analyzer_prod"
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# Crear directorio si no existe
mkdir -p $BACKUP_DIR

# Realizar backup
sudo -u postgres pg_dump $DB_NAME > $BACKUP_FILE

# Comprimir backup
gzip $BACKUP_FILE

# Eliminar backups antiguos (mantener últimos 7 días)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completado: ${BACKUP_FILE}.gz"
```

Dar permisos de ejecución:

```bash
chmod +x /home/pi/backup_postgres.sh
```

### 8.2. Programar backup diario con cron

```bash
crontab -e
```

Agrega al final:

```cron
# Backup PostgreSQL diario a las 2 AM
0 2 * * * /home/pi/backup_postgres.sh >> /home/pi/backup_postgres.log 2>&1
```

Guarda con `Ctrl+O`, Enter, `Ctrl+X`.

### 8.3. Probar backup manualmente

```bash
/home/pi/backup_postgres.sh
```

Verifica que se creó:

```bash
ls -lh ~/postgres_backups/
```

---

## 9. Actualizar Aplicación para Usar PostgreSQL

### 9.1. En tu PC, actualiza el código

Ya está hecho - [database.py](src/api/database/database.py) detecta automáticamente si usar PostgreSQL o SQLite según `DATABASE_URL`.

### 9.2. Configurar entorno de producción

Cuando despliegues la aplicación en producción, asegúrate de que el `.env.prod` tenga:

```env
DATABASE_URL=postgresql://stock_analyzer_user:TU_PASSWORD@192.168.1.50:5432/stock_analyzer_prod
```

### 9.3. Reiniciar API

```bash
# Si usas el script
python run_api.py

# O con Uvicorn directamente
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verás en los logs:

```
INFO - Using PostgreSQL database
INFO - Connected to PostgreSQL: PostgreSQL 13.x on armv7l-unknown-linux-gnueabihf
```

---

## 10. Monitoreo y Mantenimiento

### 10.1. Ver logs de PostgreSQL

```bash
sudo tail -f /var/log/postgresql/postgresql-13-main.log
```

### 10.2. Ver conexiones activas

```bash
sudo -u postgres psql -d stock_analyzer_prod
```

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'stock_analyzer_prod';
```

### 10.3. Ver tamaño de la base de datos

```sql
SELECT pg_size_pretty(pg_database_size('stock_analyzer_prod'));
```

### 10.4. Optimizar base de datos (ejecutar semanalmente)

```sql
VACUUM ANALYZE;
```

---

## 11. Seguridad Adicional (Recomendado)

### 11.1. Cambiar puerto de PostgreSQL (opcional)

Edita `postgresql.conf`:

```bash
sudo nano /etc/postgresql/13/main/postgresql.conf
```

Busca:

```conf
#port = 5432
```

Cambia a (por ejemplo):

```conf
port = 5433
```

**Recuerda**: Actualizar también `DATABASE_URL` en `.env.prod`.

### 11.2. Firewall (si usas ufw)

```bash
sudo ufw allow from 192.168.1.0/24 to any port 5432
```

### 11.3. Crear usuario de solo lectura (para análisis)

```sql
CREATE USER readonly_user WITH PASSWORD 'otra_password';
GRANT CONNECT ON DATABASE stock_analyzer_prod TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

---

## 12. Solución de Problemas

### Problema: No puedo conectar desde mi PC

**Verificar:**

1. ¿La Raspberry está encendida?
   ```bash
   ping 192.168.1.50
   ```

2. ¿PostgreSQL está corriendo?
   ```bash
   sudo systemctl status postgresql
   ```

3. ¿El firewall está bloqueando?
   ```bash
   sudo ufw status
   ```

4. ¿La IP es correcta?
   ```bash
   hostname -I
   ```

### Problema: "password authentication failed"

**Solución:**

1. Verifica la contraseña en `DATABASE_URL`
2. Verifica que el usuario existe:
   ```sql
   sudo -u postgres psql
   \du
   ```

3. Reinicia PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

### Problema: "FATAL: no pg_hba.conf entry"

**Solución:**

1. Verifica que agregaste la línea en `pg_hba.conf`
2. Verifica que la red es correcta (`192.168.1.0/24`)
3. Reinicia PostgreSQL

### Problema: La Raspberry se queda sin espacio

**Solución:**

1. Verificar espacio:
   ```bash
   df -h
   ```

2. Limpiar backups antiguos:
   ```bash
   rm ~/postgres_backups/*.sql.gz
   ```

3. Optimizar base de datos:
   ```sql
   VACUUM FULL;
   ```

---

## 13. Rendimiento de Raspberry Pi

### Especificaciones recomendadas:

- **Raspberry Pi 4 (4GB RAM)**: Excelente para esta aplicación
- **Raspberry Pi 3B+ (1GB RAM)**: Suficiente, pero puede ser lenta con muchos datos
- **Raspberry Pi 5 (8GB RAM)**: Sobrada, tendrás margen para crecer

### Optimizaciones para Raspberry Pi:

Edita `postgresql.conf`:

```bash
sudo nano /etc/postgresql/13/main/postgresql.conf
```

Ajusta según tu modelo:

**Para Raspberry Pi 4 (4GB RAM):**

```conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

**Para Raspberry Pi 3B+ (1GB RAM):**

```conf
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 2MB
maintenance_work_mem = 32MB
```

Reinicia PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## 14. Próximos Pasos

Una vez tengas PostgreSQL funcionando en la Raspberry:

1. **Ejecuta la migración de datos** (Paso 7)
2. **Configura el backup automático** (Paso 8)
3. **Actualiza tu aplicación** para apuntar a la Raspberry (Paso 9)
4. **Implementa el data accumulator** para guardar datos históricos diariamente

### Data Accumulator PostgreSQL

Cuando PostgreSQL esté listo, ejecuta:

```bash
# Instalar dependencias primero
pip install -r requirements.txt

# Ejecutar acumulador manualmente
python tools/backtest/box_strategy/data_accumulator_postgres.py

# O programa con cron (diario a las 4 PM ET)
crontab -e
```

Agrega:

```cron
0 16 * * 1-5 cd /ruta/a/stock-analyzer && python tools/backtest/box_strategy/data_accumulator_postgres.py
```

---

## Resumen de URLs y Credenciales

**Para guardar en lugar seguro:**

```
=== PostgreSQL en Raspberry Pi ===

IP Raspberry: 192.168.1.50 (CAMBIAR)
Puerto: 5432
Base de datos: stock_analyzer_prod
Usuario: stock_analyzer_user
Contraseña: TU_CONTRASEÑA_SEGURA_AQUI (CAMBIAR)

DATABASE_URL para .env.prod:
postgresql://stock_analyzer_user:TU_CONTRASEÑA_SEGURA_AQUI@192.168.1.50:5432/stock_analyzer_prod

Backup location: /home/pi/postgres_backups/
Backup schedule: Diario a las 2 AM
Backup retention: 7 días
```

---

## ¿Necesitas ayuda?

Si encuentras algún problema durante la instalación:

1. Revisa la sección "Solución de Problemas" (Paso 12)
2. Verifica los logs de PostgreSQL: `sudo tail -f /var/log/postgresql/postgresql-13-main.log`
3. Consulta la documentación oficial de PostgreSQL: https://www.postgresql.org/docs/

---

**¡Listo!** Tu Raspberry Pi ahora funciona como servidor de base de datos 24/7 para Stock Analyzer.
