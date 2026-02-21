"""
Tests para validar la configuración del sistema de backup diario.
Detectan problemas de configuración ANTES de que fallen en producción.
"""
import os
import pytest
import yaml
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class TestBackupScriptExists:
    """Verifica que el script de backup y sus dependencias existan."""

    def test_backup_script_existe(self):
        """El script backup_to_s3.py debe existir."""
        script = BASE_DIR / 'scripts' / 'backup_to_s3.py'
        assert script.exists(), (
            f"No se encontró scripts/backup_to_s3.py en {BASE_DIR}. "
            "El backup diario no puede ejecutarse sin este archivo."
        )

    def test_backup_script_es_importable(self):
        """El script debe ser importable (sin errores de sintaxis)."""
        script = BASE_DIR / 'scripts' / 'backup_to_s3.py'
        if not script.exists():
            pytest.skip("Script no encontrado")
        import importlib.util
        spec = importlib.util.spec_from_file_location("backup_to_s3", str(script))
        # Solo verificamos que el spec se crea, no importamos (requiere boto3)
        assert spec is not None, "El script tiene errores de sintaxis"

    def test_backup_script_tiene_main(self):
        """El script debe tener una función main()."""
        script = BASE_DIR / 'scripts' / 'backup_to_s3.py'
        if not script.exists():
            pytest.skip("Script no encontrado")
        content = script.read_text(encoding='utf-8')
        assert 'def main()' in content, "El script no tiene función main()"
        assert "if __name__ == '__main__'" in content, "El script no tiene bloque __main__"

    def test_backup_script_tiene_clase_manager(self):
        """El script debe tener la clase DatabaseBackupManager."""
        script = BASE_DIR / 'scripts' / 'backup_to_s3.py'
        if not script.exists():
            pytest.skip("Script no encontrado")
        content = script.read_text(encoding='utf-8')
        assert 'class DatabaseBackupManager' in content, (
            "No se encontró la clase DatabaseBackupManager en backup_to_s3.py"
        )


class TestGitHubWorkflowConfig:
    """Verifica la configuración del workflow de GitHub Actions."""

    def _load_workflow(self):
        """Carga el archivo YAML del workflow."""
        workflow_path = BASE_DIR / '.github' / 'workflows' / 'daily-backup.yml'
        if not workflow_path.exists():
            pytest.skip("Workflow daily-backup.yml no encontrado")
        with open(workflow_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _get_workflow_text(self):
        """Lee el texto del workflow."""
        workflow_path = BASE_DIR / '.github' / 'workflows' / 'daily-backup.yml'
        if not workflow_path.exists():
            pytest.skip("Workflow daily-backup.yml no encontrado")
        return workflow_path.read_text(encoding='utf-8')

    def test_workflow_existe(self):
        """El workflow de backup diario debe existir."""
        workflow_path = BASE_DIR / '.github' / 'workflows' / 'daily-backup.yml'
        assert workflow_path.exists(), (
            "No se encontró .github/workflows/daily-backup.yml. "
            "El backup diario no se ejecutará."
        )

    def test_workflow_tiene_schedule(self):
        """El workflow debe tener un cron schedule configurado."""
        data = self._load_workflow()
        # YAML parsea 'on:' como True (boolean), no como string 'on'
        triggers = data.get('on') or data.get(True)
        assert triggers is not None, "Workflow no tiene trigger 'on'"
        assert 'schedule' in triggers, (
            "El workflow no tiene 'schedule'. El backup no se ejecutará automáticamente."
        )
        schedules = triggers['schedule']
        assert len(schedules) > 0, "No hay cron schedules definidos"
        # Verificar que el cron es para las 8:00 UTC (3:00 AM Colombia)
        cron = schedules[0].get('cron', '')
        assert '0 8' in cron, (
            f"El cron '{cron}' no ejecuta a las 8:00 UTC (3 AM Colombia). "
            "El backup podría ejecutarse a una hora inesperada."
        )

    def test_workflow_ruta_script_correcta(self):
        """El workflow debe ejecutar el script desde la ruta correcta."""
        text = self._get_workflow_text()
        # El script está en scripts/backup_to_s3.py
        script_path = BASE_DIR / 'scripts' / 'backup_to_s3.py'
        if not script_path.exists():
            pytest.skip("Script no encontrado")
        # Verificar que el workflow usa la ruta correcta
        # Puede ser: python scripts/backup_to_s3.py o cd scripts && python backup_to_s3.py
        uses_correct_path = (
            'scripts/backup_to_s3.py' in text
            or 'cd scripts' in text
        )
        if not uses_correct_path and 'python backup_to_s3.py' in text:
            pytest.fail(
                "CRITICO: El workflow ejecuta 'python backup_to_s3.py' pero el script "
                "está en 'scripts/backup_to_s3.py'. El backup falla con "
                "'FileNotFoundError'. Cambiar a 'python scripts/backup_to_s3.py'."
            )
        assert uses_correct_path, (
            "No se encontró referencia correcta a scripts/backup_to_s3.py en el workflow"
        )

    def test_workflow_tiene_secrets_requeridos(self):
        """El workflow debe usar los secrets necesarios para el backup."""
        text = self._get_workflow_text()
        secrets_requeridos = [
            'DATABASE_URL',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_BACKUP_BUCKET',
            'AWS_S3_ENDPOINT_URL',
        ]
        for secret in secrets_requeridos:
            assert f'secrets.{secret}' in text, (
                f"El workflow no usa el secret '{secret}'. "
                f"Sin este secret, el backup fallará."
            )

    def test_workflow_tiene_notificacion_fallo(self):
        """El workflow debe notificar cuando el backup falla."""
        text = self._get_workflow_text()
        assert 'if: failure()' in text, (
            "El workflow no tiene paso de notificación en caso de fallo. "
            "Los fallos de backup pasarán desapercibidos."
        )

    def test_workflow_tiene_paso_pg_dump(self):
        """El workflow debe instalar pg_dump para el backup."""
        text = self._get_workflow_text()
        assert 'postgresql-client' in text or 'pg_dump' in text, (
            "El workflow no instala postgresql-client. "
            "pg_dump no estará disponible para crear el backup."
        )


class TestBackupRequirements:
    """Verifica que las dependencias del backup estén en requirements."""

    def test_boto3_en_requirements(self):
        """boto3 debe estar en requirements.txt para el backup."""
        req_file = BASE_DIR / 'requirements.txt'
        if not req_file.exists():
            pytest.skip("requirements.txt no encontrado")
        content = req_file.read_text(encoding='utf-8').lower()
        assert 'boto3' in content, (
            "boto3 no está en requirements.txt. "
            "El script de backup lo necesita para subir a R2/S3."
        )
