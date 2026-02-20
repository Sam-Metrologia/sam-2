#!/usr/bin/env python
"""
Script para hacer backup de la base de datos SQLite
Ejecutar: python backup_database.py
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    """Crea backup de la base de datos"""
    # Directorio base
    BASE_DIR = Path(__file__).resolve().parent

    # Archivo de base de datos
    db_file = BASE_DIR / 'db.sqlite3'

    if not db_file.exists():
        print("[ERROR] No se encontro la base de datos db.sqlite3")
        return False

    # Crear directorio de backups si no existe
    backup_dir = BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)

    # Nombre del backup con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'db_backup_{timestamp}.sqlite3'

    try:
        # Copiar archivo
        shutil.copy2(db_file, backup_file)

        # Obtener tamaño
        size_mb = backup_file.stat().st_size / (1024 * 1024)

        print(f"[OK] Backup creado exitosamente:")
        print(f"   Archivo: {backup_file.name}")
        print(f"   Tamano: {size_mb:.2f} MB")
        print(f"   Ubicacion: {backup_file}")

        # Limpiar backups antiguos (mantener últimos 10)
        cleanup_old_backups(backup_dir)

        return True

    except Exception as e:
        print(f"[ERROR] Error al crear backup: {e}")
        return False

def cleanup_old_backups(backup_dir, keep_last=10):
    """Elimina backups antiguos, manteniendo solo los últimos N"""
    backups = sorted(backup_dir.glob('db_backup_*.sqlite3'), key=os.path.getmtime, reverse=True)

    if len(backups) > keep_last:
        deleted = 0
        for old_backup in backups[keep_last:]:
            try:
                old_backup.unlink()
                deleted += 1
            except Exception as e:
                print(f"[WARN] No se pudo eliminar {old_backup.name}: {e}")

        if deleted > 0:
            print(f"[INFO] Se eliminaron {deleted} backup(s) antiguo(s)")

if __name__ == '__main__':
    print("=" * 60)
    print("INICIANDO BACKUP DE BASE DE DATOS")
    print("=" * 60)
    backup_database()
    print("=" * 60)
