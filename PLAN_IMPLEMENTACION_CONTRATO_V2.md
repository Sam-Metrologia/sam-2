# 📋 PLAN DE IMPLEMENTACIÓN - CONTRATO V2.0 Y BACKUPS

## 🎯 RESUMEN EJECUTIVO

**Fecha:** 11 de diciembre de 2025
**Versión:** 2.0
**Estado:** Pendiente de implementación

---

## 📊 CAMBIOS PRINCIPALES

### **1. PRECIOS ACTUALIZADOS**

| Concepto | Antes (v1.0) | Ahora (v2.0) | Cambio |
|----------|--------------|--------------|--------|
| **Plan Mensual** | $200.000 | $200.000 | Sin cambio |
| **Equipos incluidos** | 50 | 200 | +300% ⬆️ |
| **Almacenamiento** | 2 GB | 4 GB | +100% ⬆️ |
| **Usuarios** | 3 | 3 | Sin cambio |
| **Equipo adicional** | $2.000 | $1.000 | -50% ⬇️ |
| **Usuario adicional** | $50.000 | $25.000 | -50% ⬇️ |
| **GB adicional** | $50.000 | $25.000 | -50% ⬇️ |

### **2. MEJORAS LEGALES**

✅ Cláusula de limitación de responsabilidad corregida (riesgo legal eliminado)
✅ Derechos ARCO detallados (cumplimiento Ley 1581/2012)
✅ Compensación SLA con tabla clara
✅ Notificación preventiva en Regla de 7 Días
✅ Cláusula de fuerza mayor agregada
✅ Resolución alternativa de conflictos

### **3. BACKUPS IMPLEMENTADOS**

✅ Script de backup automático diario a S3
✅ Retención de 6 meses (cumple contrato)
✅ GitHub Actions para automatización
✅ Notificaciones de fallas

---

## 🔧 IMPLEMENTACIÓN TÉCNICA

### **PASO 1: Configurar Backups Automáticos**

#### **A. Crear Bucket S3 para Backups**

```bash
# 1. Ir a AWS Console → S3 → Create Bucket
# Nombre: sam-metrologia-backups
# Región: us-east-2 (Ohio)
# Configuración:
#   - Block all public access: ✅ Enabled
#   - Versioning: ✅ Enabled
#   - Encryption: AES-256
#   - Lifecycle rule:
#     * Name: delete-after-6-months
#     * Expiration: 180 days
```

#### **B. Configurar Variables de Entorno en Render**

Ir a **Render Dashboard → Environment Variables** y agregar:

```env
AWS_BACKUP_BUCKET=sam-metrologia-backups
```

#### **C. Configurar GitHub Secrets**

Ir a **GitHub → Settings → Secrets and Variables → Actions** y agregar:

```
DATABASE_URL=<valor-de-render>
AWS_ACCESS_KEY_ID=<tu-aws-key>
AWS_SECRET_ACCESS_KEY=<tu-aws-secret>
AWS_BACKUP_BUCKET=sam-metrologia-backups
AWS_S3_REGION_NAME=us-east-2
ADMIN_EMAIL=tu@email.com
```

#### **D. Activar GitHub Actions**

```bash
# 1. Los archivos ya están creados:
#    - backup_to_s3.py
#    - .github/workflows/daily-backup.yml

# 2. Hacer commit y push
cd /ruta/a/sam-2
git add backup_to_s3.py .github/
git commit -m "feat: Implementar backups automáticos diarios con retención 6 meses"
git push origin main

# 3. Verificar en GitHub
# GitHub → Actions → Debería aparecer "Backup Diario Automático"
# Se ejecutará automáticamente a las 3:00 AM (Colombia)

# 4. Probar manualmente
# GitHub → Actions → Backup Diario Automático → Run workflow
```

---

### **PASO 2: Actualizar Modelo de Empresa (Límites)**

#### **Editar `core/models.py`:**

```python
# Línea ~150 (modelo Empresa)

# CAMBIAR DE:
limite_equipos_empresa = models.IntegerField(default=50, verbose_name="Límite Máximo de Equipos")
limite_almacenamiento_mb = models.IntegerField(default=2048, verbose_name="Límite de Almacenamiento (MB)")

# A:
limite_equipos_empresa = models.IntegerField(default=200, verbose_name="Límite Máximo de Equipos")
limite_almacenamiento_mb = models.IntegerField(default=4096, verbose_name="Límite de Almacenamiento (MB)")
```

#### **Crear y aplicar migración:**

```bash
# En local
python manage.py makemigrations
python manage.py migrate

# Commit y push
git add core/models.py core/migrations/
git commit -m "feat: Actualizar límites de plan básico a 200 equipos y 4GB"
git push origin main

# Render aplicará automáticamente
```

---

### **PASO 3: Actualizar Contrato en Base de Datos**

#### **Crear script de migración de términos:**

```python
# Crear archivo: update_terms_v2.py

from django.core.management.base import BaseCommand
from core.models import TerminosYCondiciones
from datetime import date

class Command(BaseCommand):
    help = 'Actualiza a Términos y Condiciones v2.0'

    def handle(self, *args, **kwargs):
        # Leer contenido del nuevo contrato
        with open('contrato_actualizado_v2.html', 'r', encoding='utf-8') as f:
            contenido_html = f.read()

        # Crear nueva versión de términos
        nuevo_termino, created = TerminosYCondiciones.objects.update_or_create(
            version='2.0',
            defaults={
                'contenido_html': contenido_html,
                'fecha_vigencia': date(2025, 12, 11),
                'activo': True
            }
        )

        # Desactivar versiones anteriores
        TerminosYCondiciones.objects.exclude(version='2.0').update(activo=False)

        self.stdout.write(
            self.style.SUCCESS(f'✅ Términos v2.0 {"creados" if created else "actualizados"}')
        )
```

#### **Ejecutar actualización:**

```bash
python manage.py update_terms_v2
```

---

## ⚖️ QUÉ HACER CON CONTRATOS YA FIRMADOS

### **OPCIÓN 1: Actualización Automática (RECOMENDADO)**

**Fundamento Legal:**
Cláusula 12 del contrato actual permite modificaciones con 30 días de anticipación.

**Proceso:**

1. **Enviar notificación masiva** a todos los clientes existentes:

```
Asunto: 📋 Actualización de Términos y Condiciones - SAM Metrología v2.0

Estimado cliente,

Conforme a la Cláusula 12 de su contrato actual, le notificamos que
hemos actualizado nuestros Términos y Condiciones a la versión 2.0.

📅 Fecha de entrada en vigor: 10 de enero de 2026 (30 días desde hoy)

🎁 MEJORAS PARA USTED:
✅ Más equipos incluidos: 50 → 200 equipos (+300%)
✅ Más almacenamiento: 2GB → 4GB (+100%)
✅ Precio de extras reducido: equipos $2.000 → $1.000 (-50%)
✅ Backups mejorados: retención de 6 meses garantizada
✅ Compensación SLA más clara
✅ Mejor protección de datos (Ley 1581/2012)

💰 SU PRECIO NO CAMBIA: Sigue siendo $200.000/mes + IVA

📄 Puede revisar el contrato completo en:
https://app.sammetrologia.com/terminos/v2

⚖️ DERECHO DE CANCELACIÓN SIN PENALIZACIÓN:
Si no está de acuerdo con las nuevas condiciones, puede cancelar
dentro de los próximos 30 días sin penalización y con reembolso
proporcional del periodo no utilizado.

Si no recibimos notificación de cancelación, se entenderá que acepta
las nuevas condiciones a partir del 10 de enero de 2026.

Saludos cordiales,
Equipo SAM Metrología
```

2. **Configurar modal en la plataforma** para re-aceptación:

```python
# En middleware de términos
def process_request(self, request):
    if request.user.is_authenticated:
        # Verificar si aceptó la versión actual
        ultima_version = TerminosYCondiciones.objects.filter(activo=True).first()
        aceptacion = AceptacionTerminos.objects.filter(
            usuario=request.user,
            terminos__version=ultima_version.version
        ).first()

        if not aceptacion:
            # Redirigir a página de re-aceptación
            return redirect('core:terminos_condiciones')
```

3. **Tracking de aceptaciones:**

```python
# Generar reporte de aceptaciones
from core.models import CustomUser, AceptacionTerminos

usuarios_pendientes = CustomUser.objects.exclude(
    aceptaciones_terminos__terminos__version='2.0'
).count()

print(f"Usuarios pendientes de aceptar v2.0: {usuarios_pendientes}")
```

---

### **OPCIÓN 2: Migración Manual con Confirmación Individual**

**Para clientes corporativos grandes:**

1. Contactar por teléfono/email personalizado
2. Explicar cambios (son beneficiosos)
3. Solicitar confirmación escrita explícita
4. Mantener registro en CRM

---

## 📈 CRONOGRAMA DE IMPLEMENTACIÓN

| Fecha | Actividad | Responsable |
|-------|-----------|-------------|
| **11 Dic 2025** | ✅ Crear contrato v2.0 | Completado |
| **11 Dic 2025** | ✅ Implementar scripts de backup | Completado |
| **12 Dic 2025** | Configurar S3 bucket y GitHub Actions | Equipo DevOps |
| **12 Dic 2025** | Actualizar modelo Empresa (límites) | Equipo Dev |
| **13 Dic 2025** | Probar backups automáticos | Equipo QA |
| **13 Dic 2025** | Subir términos v2.0 a producción | Equipo Dev |
| **14 Dic 2025** | Enviar notificación masiva a clientes | Equipo Comercial |
| **14 Dic - 13 Ene 2026** | Periodo de gracia de 30 días | - |
| **14 Ene 2026** | Entrada en vigor obligatoria v2.0 | - |

---

## ✅ CHECKLIST DE VERIFICACIÓN

### **Backups:**
- [ ] Bucket S3 creado y configurado
- [ ] Variables de entorno en Render configuradas
- [ ] GitHub Secrets configurados
- [ ] GitHub Actions activado y funcionando
- [ ] Primer backup manual ejecutado exitosamente
- [ ] Backup automático programado (3:00 AM diario)
- [ ] Retención de 6 meses verificada en S3 Lifecycle

### **Base de Datos:**
- [ ] Límites de equipos actualizados (50 → 200)
- [ ] Límites de almacenamiento actualizados (2GB → 4GB)
- [ ] Migración aplicada en producción
- [ ] Términos v2.0 subidos a base de datos
- [ ] Versiones anteriores marcadas como inactivas

### **Comunicación:**
- [ ] Email de notificación redactado y aprobado
- [ ] Lista de clientes existentes obtenida
- [ ] Email masivo enviado (30 días antes)
- [ ] Modal de re-aceptación implementado
- [ ] Tracking de aceptaciones configurado

### **Legal:**
- [ ] Revisar con abogado (opcional pero recomendado)
- [ ] Política de Privacidad separada creada
- [ ] DIAN notificada de cambios (si aplica facturación)

---

## 🚨 RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Clientes rechazan v2.0 | Baja | Medio | Los cambios son beneficiosos (+equipos, +GB) |
| Falla en backups automáticos | Baja | Alto | Monitoreo diario + alertas email |
| Problemas legales con migración | Baja | Alto | Período de gracia 30 días + derecho a cancelar |
| GitHub Actions falla | Media | Medio | Backup manual semanal como respaldo |

---

## 📞 CONTACTOS CLAVE

- **Soporte Técnico:** soporte@sammetrologia.com
- **Legal:** legal@sammetrologia.com (si existe)
- **Comercial:** ventas@sammetrologia.com

---

## 📚 DOCUMENTOS RELACIONADOS

1. `contrato_actualizado_v2.html` - Contrato completo v2.0
2. `backup_to_s3.py` - Script de backups
3. `.github/workflows/daily-backup.yml` - Automatización
4. `temp_contrato.html` - Contrato v1.0 (referencia)

---

**Preparado por:** Claude Code (Anthropic)
**Fecha:** 11 de diciembre de 2025
**Versión del documento:** 1.0
