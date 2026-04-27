"""Patch manual-plataforma.html con las mejoras de la auditoría 2026-04-26."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PATH = r'C:\Users\LENOVO\OneDrive\Escritorio\sam-website\manual-plataforma.html'

with open(PATH, encoding='utf-8', errors='replace') as f:
    content = f.read()

print(f'Tamaño original: {len(content):,} chars')

# ─── 1. Versión v1.0 → v8.5 ──────────────────────────────────────────────
content = content.replace('Manual de Usuario v1.0', 'Manual de Usuario v8.5')
print(f'Versiones actualizadas. Ocurrencias de v8.5: {content.count("v8.5")}')

# ─── 2. Sidebar: catalogos entre equipos y calibraciones ─────────────────
old_sb = (
    '    <a class="sb-link" href="#equipos"><span class="num">2</span>Gestión de equipos</a>\n'
    '    <a class="sb-link" href="#calibraciones"><span class="num">3</span>Calibraciones</a>'
)
new_sb = (
    '    <a class="sb-link" href="#equipos"><span class="num">2</span>Gestión de equipos</a>\n'
    '    <a class="sb-link" href="#catalogos"><span class="num">2.1</span>Catálogos</a>\n'
    '    <a class="sb-link" href="#calibraciones"><span class="num">3</span>Calibraciones</a>'
)
if old_sb in content:
    content = content.replace(old_sb, new_sb, 1)
    print('Sidebar: enlace catálogos agregado')
else:
    print('ERROR: no encontré el bloque del sidebar para catálogos')

# ─── 3. Sidebar: FAQ después de suscripcion ───────────────────────────────
old_sb2 = (
    '    <a class="sb-link" href="#suscripcion"><span class="num">17</span>Suscripción y planes</a>\n'
    '  </div>'
)
new_sb2 = (
    '    <a class="sb-link" href="#suscripcion"><span class="num">17</span>Suscripción y planes</a>\n'
    '    <a class="sb-link" href="#faq"><span class="num">18</span>Preguntas frecuentes</a>\n'
    '  </div>'
)
if old_sb2 in content:
    content = content.replace(old_sb2, new_sb2, 1)
    print('Sidebar: enlace FAQ agregado')
else:
    print('ERROR: no encontré el bloque del sidebar para FAQ')

# ─── 4. Sección Catálogos (antes del comentario de calibraciones) ─────────
CATALOGO = """
  <!-- ══ 2.1 CATÁLOGOS ══ -->
  <section class="section" id="catalogos">
    <div class="section-header">
      <div class="section-num">2.1</div>
      <h2>Catálogos</h2>
      <div class="role-tags"><span class="role role-admin">Admin y Gerencia</span></div>
    </div>

    <p>Los catálogos son las tablas de referencia que usa SAM para clasificar y organizar la información. Configurarlos correctamente <strong>antes de registrar equipos</strong> es clave para mantener consistencia en toda la organización.</p>

    <h3>Magnitudes</h3>
    <p>Una <strong>magnitud</strong> es el tipo de cantidad física que mide un equipo: Masa, Longitud, Temperatura, Presión, Humedad, Volumen, etc. Cada equipo se asocia a una magnitud, que luego determina las unidades y puntos de medición disponibles en confirmaciones y comprobaciones.</p>
    <div class="table-wrap"><table>
      <tr><th>Magnitud</th><th>Unidades típicas</th><th>Equipos representativos</th></tr>
      <tr><td>Masa</td><td>kg, g, mg</td><td>Balanzas, pesas patrón</td></tr>
      <tr><td>Longitud</td><td>mm, cm, m</td><td>Calibradores, micrómetros</td></tr>
      <tr><td>Temperatura</td><td>°C, °F, K</td><td>Termómetros, cámaras climáticas</td></tr>
      <tr><td>Presión</td><td>Pa, bar, psi</td><td>Manómetros, transductores</td></tr>
      <tr><td>Volumen</td><td>mL, L, m³</td><td>Pipetas, buretas, medidores de flujo</td></tr>
    </table></div>

    <h3>Familias de equipos</h3>
    <p>Las <strong>familias</strong> agrupan equipos similares dentro de una magnitud. Permiten filtrar el inventario y generar reportes por grupo. Ejemplo: dentro de "Masa" pueden existir las familias "Balanzas analíticas", "Balanzas de plataforma" y "Pesas patrón".</p>

    <h3>Proveedores de calibración</h3>
    <p>El catálogo de <strong>proveedores</strong> lista los laboratorios acreditados que realizan calibraciones externas. Al registrar una calibración, seleccionas el proveedor del catálogo o lo ingresas manualmente si aún no está registrado. Mantener el catálogo actualizado permite generar análisis de costos y desempeño por laboratorio en el Panel de Decisiones.</p>

    <div class="box box-info"><strong>¿Dónde se configura?</strong><p>Ve a <strong>Configuración → Catálogos</strong> en el menú lateral. Solo los roles Administrador y Gerencia pueden crear o modificar catálogos.</p></div>

    <div class="box box-warn"><strong>Configura primero, registra después</strong><p>Cambiar la magnitud de un equipo después de haber registrado confirmaciones y comprobaciones puede afectar la visualización de gráficas históricas. Define los catálogos antes de empezar a registrar equipos.</p></div>
  </section>

  <!-- ══ 3. CALIBRACIONES ══ -->"""

MARKER_CAL = '  <!-- ══ 3. CALIBRACIONES ══ -->'
if MARKER_CAL in content:
    content = content.replace(MARKER_CAL, CATALOGO, 1)
    print('Sección Catálogos insertada')
else:
    print('ERROR: no encontré el marcador de calibraciones')

# ─── 5. Expandir comprobaciones: añadir 6.3 y 6.4 ───────────────────────
OLD_COMP_END = (
    '    </ul>\n'
    '  </section>\n'
    '\n'
    '  <!-- ══ 7. MANTENIMIENTOS ══ -->'
)
NEW_COMP_END = """
    <h3>6.3 ¿Cuándo y con qué frecuencia?</h3>
    <p>La frecuencia depende de la criticidad del equipo y las exigencias del proceso:</p>
    <div class="table-wrap"><table>
      <tr><th>Nivel de criticidad</th><th>Frecuencia recomendada</th><th>Ejemplo</th></tr>
      <tr><td><strong>Alta</strong></td><td>Diaria o antes de cada uso</td><td>Balanza de precisión en producción farmacéutica</td></tr>
      <tr><td><strong>Media</strong></td><td>Semanal o mensual</td><td>Termómetro de laboratorio de ensayo</td></tr>
      <tr><td><strong>Baja</strong></td><td>Trimestral o semestral</td><td>Regla de referencia en bodega</td></tr>
    </table></div>
    <p>El sistema te permite configurar el intervalo de comprobación para cada equipo. Cuando vence, aparece una alerta en el Dashboard y en el Calendario de actividades.</p>

    <h3>6.4 Diferencia con la calibración</h3>
    <div class="table-wrap"><table>
      <tr><th></th><th>Calibración</th><th>Comprobación intermedia</th></tr>
      <tr><td><strong>¿Quién la realiza?</strong></td><td>Laboratorio externo acreditado</td><td>El propio laboratorio / técnico interno</td></tr>
      <tr><td><strong>¿Qué produce?</strong></td><td>Certificado de calibración oficial</td><td>Registro interno de verificación</td></tr>
      <tr><td><strong>¿Frecuencia?</strong></td><td>Según intervalo definido (meses/años)</td><td>Más frecuente (días o semanas)</td></tr>
      <tr><td><strong>¿Norma?</strong></td><td>ISO 17025 / ISO 10012</td><td>ISO 17020 / ISO 17025</td></tr>
    </table></div>
    <div class="box box-tip"><strong>Consejo</strong><p>Si una comprobación arroja un resultado fuera del EMP, <strong>no uses el equipo</strong> hasta investigar la causa. Puede ser necesario enviarlo a recalibración anticipada.</p></div>
  </section>

  <!-- ══ 7. MANTENIMIENTOS ══ -->"""

if OLD_COMP_END in content:
    content = content.replace(OLD_COMP_END, NEW_COMP_END, 1)
    print('Comprobaciones expandido (6.3 y 6.4 agregados)')
else:
    print('ERROR: no encontré el cierre de comprobaciones')

# ─── 6. Chatbot: agregar límite de 20 mensajes/hora ──────────────────────
OLD_CHAT_TIP = '    <div class="box box-tip"><strong>Úsalo como primer punto de ayuda</strong><p>Antes de escribir al soporte, pregúntale al Señor SAM. Conoce todos los módulos de la plataforma y puede guiarte paso a paso.</p></div>\n  </section>\n\n  <!-- ══ 17. SUSCRIPCIÓN ══ -->'
NEW_CHAT_TIP = """    <h3>Límite de uso</h3>
    <p>Para garantizar la disponibilidad del servicio, el chatbot tiene un límite de <strong>20 mensajes por hora por usuario</strong>. Si alcanzas el límite, el sistema te notifica y puedes continuar en la siguiente hora. Para consultas urgentes, escribe a <a href="mailto:soporte@sammetrologia.com">soporte@sammetrologia.com</a>.</p>

    <div class="box box-tip"><strong>Úsalo como primer punto de ayuda</strong><p>Antes de escribir al soporte, pregúntale al Señor SAM. Conoce todos los módulos de la plataforma y puede guiarte paso a paso.</p></div>
  </section>

  <!-- ══ 17. SUSCRIPCIÓN ══ -->"""

if OLD_CHAT_TIP in content:
    content = content.replace(OLD_CHAT_TIP, NEW_CHAT_TIP, 1)
    print('Chatbot: límite de mensajes agregado')
else:
    print('ERROR: no encontré el bloque del chatbot para expandir')

# ─── 7. Sección FAQ (antes del <hr class="divider">) ─────────────────────
FAQ = """
  <!-- ══ 18. FAQ ══ -->
  <section class="section" id="faq">
    <div class="section-header">
      <div class="section-num">18</div>
      <h2>Preguntas Frecuentes</h2>
      <div class="role-tags"><span class="role role-all">Todos los roles</span></div>
    </div>

    <h3>Acceso y cuenta</h3>

    <h4>¿Olvidé mi contraseña, qué hago?</h4>
    <p>En la pantalla de inicio de sesión haz clic en <strong>"¿Olvidaste tu contraseña?"</strong>. El sistema enviará un enlace de restablecimiento al correo registrado. Si no tienes correo configurado, contáctale a tu administrador.</p>

    <h4>¿Por qué no veo todos los equipos?</h4>
    <p>SAM es un sistema multiempresa. Solo ves los equipos de la empresa a la que pertenece tu usuario. Si necesitas acceso a otra empresa, solicítalo al Administrador o Superusuario.</p>

    <h4>¿Cuánto tiempo dura la sesión activa?</h4>
    <p>Las sesiones se cierran automáticamente después de <strong>8 horas de inactividad</strong>. Guarda tu trabajo antes de alejarte del computador.</p>

    <h3>Equipos y calibraciones</h3>

    <h4>¿Puedo registrar una calibración sin adjuntar el PDF del certificado?</h4>
    <p>Sí, el PDF no es obligatorio en el formulario. Sin embargo, adjuntarlo es una buena práctica y es requerido en auditorías de acreditación. Puedes cargarlo después editando el registro de calibración.</p>

    <h4>¿Cuántos puntos de medición debo ingresar en la confirmación metrológica?</h4>
    <p>Se recomiendan al menos <strong>3 puntos representativos</strong> del rango de trabajo (mínimo, medio y máximo). Para equipos críticos o con requerimientos normativos estrictos, usa 5 o más puntos.</p>

    <h4>¿Qué pasa si el equipo es Apto en algunos puntos y No Apto en otros?</h4>
    <p>El sistema marca la confirmación como <strong>No Apto</strong> si algún punto supera el EMP. Puedes documentar que el equipo es apto para un rango de uso reducido, siempre que la restricción quede anotada y firmada por el responsable metrológico.</p>

    <h4>¿Puedo cambiar el intervalo de calibración de un equipo?</h4>
    <p>Sí. Ve al detalle del equipo y edita el campo "Intervalo de calibración". El sistema recalculará la próxima fecha automáticamente. El cambio queda registrado en el historial del equipo.</p>

    <h3>Reportes y documentos</h3>

    <h4>¿Los PDFs generados tienen validez para una auditoría de acreditación?</h4>
    <p>Sí. Los reportes incluyen número de registro, versión del formato, fecha de emisión y nombre del técnico responsable, conforme a los requisitos de ISO 17020 e ISO 17025.</p>

    <h4>El ZIP tarda mucho en generarse, ¿es normal?</h4>
    <p>Los ZIP se generan en segundo plano porque pueden contener muchos documentos. Recibirás una notificación cuando esté listo. Si después de 15 minutos no hay notificación, reintenta la descarga o contacta soporte.</p>

    <h3>Planes y facturación</h3>

    <h4>¿Qué pasa con mis datos si el trial expira sin activar un plan?</h4>
    <p>Tienes <strong>15 días adicionales</strong> después del vencimiento del trial para activar un plan. Pasado ese plazo, los datos se eliminan permanentemente. SAM envía alertas por email 7 días antes del vencimiento.</p>

    <h4>¿Cómo agrego más equipos si llegué al límite de mi plan?</h4>
    <p>Ve a <strong>Administración → Suscripción</strong> y contrata el add-on de <strong>+50 equipos por bloque</strong>. También puedes hacer upgrade a un plan superior para obtener un límite más alto desde esa misma pantalla.</p>

    <h4>¿El sistema factura automáticamente?</h4>
    <p>Si tienes activada la <strong>renovación automática</strong>, el sistema intenta cobrar 5 días antes del vencimiento usando el método de pago registrado y te notifica por email 7 días antes. Si el cobro falla, recibes una alerta para actualizar tu método de pago.</p>

    <h3>Soporte técnico</h3>

    <h4>¿Cómo contacto al equipo de soporte?</h4>
    <p>Tienes tres canales disponibles:</p>
    <ul>
      <li><strong>Chatbot "Señor SAM"</strong>: disponible en la esquina inferior derecha de la plataforma. Respuesta inmediata, límite de 20 mensajes/hora.</li>
      <li><strong>Email</strong>: <a href="mailto:soporte@sammetrologia.com">soporte@sammetrologia.com</a></li>
      <li><strong>Teléfono</strong>: +57 324 799 0534</li>
    </ul>
  </section>

"""

HR_MARKER = '  <hr class="divider">'
if HR_MARKER in content:
    content = content.replace(HR_MARKER, FAQ + HR_MARKER, 1)
    print('Sección FAQ insertada')
else:
    print('ERROR: no encontré el marcador <hr class="divider">')

print(f'Tamaño final: {len(content):,} chars')

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)
print('Archivo guardado OK')
