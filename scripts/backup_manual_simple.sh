#!/bin/bash
# Backup Manual Simple - Para ejecutar 1 vez al mes
# GRATIS - Guarda en Google Drive o cualquier lugar

# Variables
FECHA=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="sam_backup_$FECHA.sql.gz"

echo "🔄 Iniciando backup manual..."

# Obtener DATABASE_URL de Render
# Copiar desde: Render Dashboard -> sam-metrologia -> Environment -> DATABASE_URL
DATABASE_URL="postgresql://sam_user:password@dpg-xxx-a.oregon-postgres.render.com/sam_db"

# Crear backup y comprimir
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"

echo "✅ Backup creado: $BACKUP_FILE"
echo "📦 Tamaño: $(ls -lh $BACKUP_FILE | awk '{print $5}')"
echo ""
echo "🔐 SIGUIENTE PASO: Sube este archivo a:"
echo "   - Google Drive (carpeta SAM Backups)"
echo "   - Dropbox"
echo "   - OneDrive"
echo "   - O cualquier almacenamiento en la nube"
echo ""
echo "📅 Próximo backup: $(date -d '+1 month' +%Y-%m-%d)"
