#!/usr/bin/env python
"""
Script de Auto-actualización de Documentación
==============================================

Este script actualiza automáticamente los archivos de documentación
con datos reales del proyecto (tests, coverage, última auditoría, etc.)

Uso:
    python update_documentation.py

El script ejecutará:
1. pytest para obtener conteo de tests
2. coverage para obtener porcentaje de cobertura
3. Identificar la auditoría más reciente
4. Actualizar archivos de documentación con datos reales

Archivos que se actualizan:
- 📚-LEER-PRIMERO-DOCS/00-START-HERE.md
- 📚-LEER-PRIMERO-DOCS/CLAUDE.md
- 📚-LEER-PRIMERO-DOCS/DEVELOPER-GUIDE.md
- CLAUDE.md (raíz)
"""

import subprocess
import re
import os
from datetime import datetime
from pathlib import Path
import json


class DocumentationUpdater:
    """Actualiza documentación con datos reales del proyecto"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.docs_dir = self.project_root / "📚-LEER-PRIMERO-DOCS"
        self.auditorias_dir = self.project_root / "auditorias"

        # Datos a recolectar
        self.data = {
            'total_tests': 0,
            'tests_passing': 0,
            'coverage_percent': 0.0,
            'latest_audit': None,
            'latest_audit_score': None,
            'update_date': datetime.now().strftime("%d de %B de %Y")
        }

    def run_tests(self):
        """Ejecutar pytest y obtener conteo de tests"""
        print("🧪 Ejecutando tests...")
        try:
            result = subprocess.run(
                ['pytest', '--collect-only', '-q'],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parsear output: "762 tests collected in 0.15s"
            match = re.search(r'(\d+) tests? collected', result.stdout)
            if match:
                self.data['total_tests'] = int(match.group(1))
                print(f"   ✓ Total tests: {self.data['total_tests']}")

            # Ejecutar tests para ver cuántos pasan
            result = subprocess.run(
                ['pytest', '-v', '--tb=no'],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parsear: "738 passed in 4.05s" o "736 passed, 2 failed"
            match_passed = re.search(r'(\d+) passed', result.stdout)
            if match_passed:
                self.data['tests_passing'] = int(match_passed.group(1))
                print(f"   ✓ Tests pasando: {self.data['tests_passing']}")

        except subprocess.TimeoutExpired:
            print("   ⚠ Timeout ejecutando tests, usando datos manuales")
        except FileNotFoundError:
            print("   ⚠ pytest no encontrado, usando datos manuales")
        except Exception as e:
            print(f"   ⚠ Error ejecutando tests: {e}")

    def run_coverage(self):
        """Ejecutar coverage y obtener porcentaje"""
        print("📊 Ejecutando coverage...")
        try:
            result = subprocess.run(
                ['pytest', '--cov=core', '--cov-report=term-missing', '--cov-report=json'],
                capture_output=True,
                text=True,
                timeout=180
            )

            # Leer coverage.json
            coverage_file = self.project_root / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    self.data['coverage_percent'] = coverage_data['totals']['percent_covered']
                    print(f"   ✓ Coverage: {self.data['coverage_percent']:.2f}%")
            else:
                # Parsear del output
                match = re.search(r'TOTAL.*?(\d+)%', result.stdout)
                if match:
                    self.data['coverage_percent'] = float(match.group(1))
                    print(f"   ✓ Coverage: {self.data['coverage_percent']:.2f}%")

        except subprocess.TimeoutExpired:
            print("   ⚠ Timeout ejecutando coverage, usando datos manuales")
        except FileNotFoundError:
            print("   ⚠ pytest-cov no encontrado, usando datos manuales")
        except Exception as e:
            print(f"   ⚠ Error ejecutando coverage: {e}")

    def find_latest_audit(self):
        """Encontrar la auditoría más reciente"""
        print("📋 Buscando auditoría más reciente...")
        try:
            audit_files = list(self.auditorias_dir.glob("AUDITORIA*.md"))
            if not audit_files:
                print("   ⚠ No se encontraron auditorías")
                return

            # Ordenar por fecha de modificación
            latest = max(audit_files, key=lambda f: f.stat().st_mtime)
            self.data['latest_audit'] = latest.name
            print(f"   ✓ Auditoría más reciente: {latest.name}")

            # Intentar extraer puntuación de la auditoría
            with open(latest, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar: "Puntuación Final: X/10" o "Puntuación Global: X/10"
                match = re.search(r'Puntuación (?:Final|Global):\s*(\d+(?:\.\d+)?)/10', content)
                if match:
                    self.data['latest_audit_score'] = match.group(1)
                    print(f"   ✓ Puntuación: {self.data['latest_audit_score']}/10")

        except Exception as e:
            print(f"   ⚠ Error buscando auditoría: {e}")

    def update_start_here(self):
        """Actualizar 00-START-HERE.md"""
        print("\n📝 Actualizando 00-START-HERE.md...")
        file_path = self.docs_dir / "00-START-HERE.md"

        if not file_path.exists():
            print("   ⚠ Archivo no encontrado")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Actualizar conteo de tests
        if self.data['tests_passing'] and self.data['total_tests']:
            content = re.sub(
                r'(\d+)/(\d+) tests deben pasar \([\d.]+%\)',
                f"{self.data['tests_passing']}/{self.data['total_tests']} tests deben pasar (100%)",
                content
            )

        # Actualizar puntuación global
        if self.data['latest_audit_score']:
            content = re.sub(
                r'\*\*Puntuación Global:\*\* \d+(?:\.\d+)?/10.*?\n',
                f"**Puntuación Global:** {self.data['latest_audit_score']}/10 (Auditoría {self.data['update_date']})\n",
                content
            )

        # Actualizar referencia a auditoría
        if self.data['latest_audit']:
            content = re.sub(
                r'`\.\./auditorias/AUDITORIA.*?\.md`',
                f"`../auditorias/{self.data['latest_audit']}`",
                content
            )

        # Actualizar fecha
        content = re.sub(
            r'\*\*Última Actualización:\*\* .*?\n',
            f"**Última Actualización:** {self.data['update_date']}\n",
            content
        )

        # Guardar solo si cambió
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("   ✓ Actualizado")
        else:
            print("   ℹ Sin cambios")

    def update_claude_md(self):
        """Actualizar CLAUDE.md en docs y raíz"""
        print("\n📝 Actualizando CLAUDE.md...")

        for file_path in [self.docs_dir / "CLAUDE.md", self.project_root / "CLAUDE.md"]:
            if not file_path.exists():
                print(f"   ⚠ {file_path.name} no encontrado")
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # Actualizar conteo de tests en comentarios
            if self.data['total_tests']:
                content = re.sub(
                    r'# Run all tests with pytest \(RECOMMENDED - \d+ tests\)',
                    f"# Run all tests with pytest (RECOMMENDED - {self.data['total_tests']} tests)",
                    content
                )

            # Actualizar stats de coverage si aparecen
            if self.data['coverage_percent']:
                content = re.sub(
                    r'Coverage: \d+(?:\.\d+)?%',
                    f"Coverage: {self.data['coverage_percent']:.2f}%",
                    content
                )

            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"   ✓ {file_path.name} actualizado")
            else:
                print(f"   ℹ {file_path.name} sin cambios")

    def run(self):
        """Ejecutar actualización completa"""
        print("=" * 60)
        print("📚 ACTUALIZADOR AUTOMÁTICO DE DOCUMENTACIÓN")
        print("=" * 60)
        print()

        # Recolectar datos
        self.run_tests()
        self.run_coverage()
        self.find_latest_audit()

        # Actualizar archivos
        self.update_start_here()
        self.update_claude_md()

        print("\n" + "=" * 60)
        print("✅ ACTUALIZACIÓN COMPLETADA")
        print("=" * 60)
        print("\nDatos actualizados:")
        print(f"  • Total tests: {self.data['total_tests']}")
        print(f"  • Tests pasando: {self.data['tests_passing']}")
        print(f"  • Coverage: {self.data['coverage_percent']:.2f}%")
        print(f"  • Auditoría: {self.data['latest_audit'] or 'N/A'}")
        print(f"  • Puntuación: {self.data['latest_audit_score'] or 'N/A'}/10")
        print(f"  • Fecha: {self.data['update_date']}")
        print()


if __name__ == '__main__':
    updater = DocumentationUpdater()
    updater.run()
