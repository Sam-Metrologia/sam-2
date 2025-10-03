/**
 * SAM METROLOGÍA - FORZADOR DE MODO OSCURO
 * Sobrescribe estilos inline que CSS no puede cambiar
 */

(function() {
    'use strict';

    function enforceModoDarkStyles() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        if (!isDark) {
            console.log('⏭️ Modo claro detectado - enforcer inactivo');
            return;
        }

        console.log('🎨 Aplicando forzado de estilos en modo oscuro...');

        // 1. ELIMINAR TODOS LOS FONDOS DE COLORES
        document.querySelectorAll('*').forEach(el => {
            const style = el.getAttribute('style');
            if (!style) return;

            // VERDE MENTA (#d1fae5, rgb(209, 250, 229))
            if (style.includes('#d1fae5') || style.includes('209, 250, 229') || style.includes('#a7f3d0')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
                el.style.border = '1px solid #10b981';
                el.querySelectorAll('*').forEach(child => {
                    if (!child.matches('button, a')) {
                        child.style.color = '#10b981';
                    }
                });
            }

            // ROJO (#ef4444, #fee2e2, #fecaca)
            if (style.includes('#fee2e2') || style.includes('254, 226, 226') ||
                style.includes('#fecaca') || style.includes('254, 202, 202') ||
                style.includes('#ef4444') || style.includes('239, 68, 68') ||
                style.includes('#f87171') || style.includes('248, 113, 113')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
                el.style.border = '1px solid #ef4444';
            }

            // NARANJA (#fb923c, #f59e0b, #ea580c)
            if (style.includes('#fef3c7') || style.includes('254, 243, 199') ||
                style.includes('#f59e0b') || style.includes('245, 158, 11') ||
                style.includes('#fb923c') || style.includes('251, 146, 60') ||
                style.includes('#ea580c') || style.includes('234, 88, 12')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
                el.style.border = '1px solid #f59e0b';
            }

            // AMARILLO (#fde68a, #fef3c7, #fbbf24)
            if (style.includes('#fde68a') || style.includes('253, 230, 138') ||
                style.includes('#fbbf24') || style.includes('251, 191, 36') ||
                style.includes('#facc15') || style.includes('250, 204, 21')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
                el.style.border = '1px solid #fbbf24';
            }

            // AZUL CLARO (#dbeafe, #bfdbfe, #93c5fd)
            if (style.includes('#dbeafe') || style.includes('219, 234, 254') ||
                style.includes('#bfdbfe') || style.includes('191, 219, 254') ||
                style.includes('#93c5fd') || style.includes('147, 197, 253')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
                el.style.border = '1px solid #3b82f6';
            }

            // BLANCO PURO (todos los formatos)
            if (style.includes('background: white') ||
                style.includes('background-color: white') ||
                style.includes('background: #fff;') ||
                style.includes('background: #fff ') ||
                style.includes('background-color: #fff;') ||
                style.includes('background-color: #fff ') ||
                style.includes('background: #ffffff') ||
                style.includes('background-color: #ffffff') ||
                style.includes('background: rgb(255, 255, 255)') ||
                style.includes('background-color: rgb(255, 255, 255)') ||
                style.includes('background:#fff') ||
                style.includes('background:#ffffff') ||
                style.includes('background:white')) {

                // No cambiar botones con clases de color
                if (!el.matches('button, a[class*="bg-blue"], a[class*="bg-green"], a[class*="bg-red"]')) {
                    el.style.backgroundColor = '#374151';
                    el.style.background = '#374151';
                }
            }

            // BORDES BLANCOS
            if (style.includes('border') && (style.includes('white') || style.includes('255, 255, 255'))) {
                el.style.borderColor = '#4b5563';
            }

            // GRADIENTES
            if (style.includes('linear-gradient') || style.includes('gradient')) {
                if (!el.matches('button, a')) {
                    el.style.background = '#374151';
                    el.style.backgroundImage = 'none';
                }
            }
        });

        // 2. FORZAR TÍTULOS VISIBLES
        document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
            const parent = h.closest('*[style*="background"]');
            if (parent) {
                h.style.color = '#ffffff';
            }
        });

        // 3. COLOREAR TÍTULOS DE INFORMES ESPECÍFICOS (SOLO EN MODO OSCURO)
        // En modo claro estos títulos ya tienen sus clases de Tailwind (text-yellow-600, text-green-600, text-red-600)
        document.querySelectorAll('h3, h4, h5').forEach(h => {
            const text = h.textContent.trim();

            if (text.includes('Próximas (15-30 días)')) {
                h.style.color = '#fbbf24'; // Amarillo
            } else if (text.includes('Próximas (0-15 días)')) {
                h.style.color = '#34d399'; // Verde
            } else if (text === 'Vencidas' || text.includes('Vencidas')) {
                h.style.color = '#f87171'; // Rojo
            }
        });

        // 4. LOS BOTONES CON COLORES (ZIP, Exportar, etc.) MANTIENEN SUS COLORES ORIGINALES
        // No es necesario forzar nada aquí, los botones ya tienen sus clases de Tailwind

        // 5. ASEGURAR TEXTO VISIBLE EN FICHAS DE COLOR
        document.querySelectorAll('*[style*="background"]').forEach(el => {
            const bgColor = window.getComputedStyle(el).backgroundColor;

            // Si tiene fondo oscuro, hacer texto claro
            if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)') {
                el.querySelectorAll('p, span, div').forEach(text => {
                    // NO modificar elementos con clases de estado de fechas
                    if (!text.matches('button, a, .badge, .text-red-600, .text-yellow-600, .text-green-600, .text-gray-500, .text-gray-900')) {
                        const currentColor = window.getComputedStyle(text).color;
                        // Si el texto es muy oscuro, hacerlo claro
                        if (currentColor.includes('rgb') &&
                            parseInt(currentColor.split(',')[0].replace('rgb(', '')) < 100) {
                            text.style.color = '#d1d5db';
                        }
                    }
                });
            }
        });

        // 6. FORZAR COLORES DE FECHAS EN TABLA DE EQUIPOS
        document.querySelectorAll('td.text-red-600').forEach(td => {
            td.style.color = '#ef4444';
            td.style.setProperty('color', '#ef4444', 'important');
        });
        document.querySelectorAll('td.text-yellow-600').forEach(td => {
            td.style.color = '#f59e0b';
            td.style.setProperty('color', '#f59e0b', 'important');
        });
        document.querySelectorAll('td.text-green-600').forEach(td => {
            td.style.color = '#22c55e';
            td.style.setProperty('color', '#22c55e', 'important');
        });

        // 7. PANEL DE DECISIONES - FONDOS GRISES Y BORDES AZULES
        document.querySelectorAll('*[style*="background: #f8fafc"]').forEach(el => {
            if (!el.matches('button, a')) {
                el.style.backgroundColor = '#374151';
                el.style.background = '#374151';
            }
        });

        // 8. PANEL DE DECISIONES - FICHAS CON FONDO BLANCO
        document.querySelectorAll('.decisiones-pilar-card, .decisiones-info-card, .decisiones-section-card').forEach(card => {
            card.style.backgroundColor = '#1f2937';
            card.style.background = '#1f2937';
            card.style.setProperty('background-color', '#1f2937', 'important');
        });

        // Panel de decisiones - contenedor principal
        document.querySelectorAll('.panel-decisiones-container').forEach(container => {
            container.style.backgroundColor = '#111827';
            container.style.setProperty('background-color', '#111827', 'important');
        });

        // 7. BADGES DE ESTADO (ÓPTIMO, BUENO, EN RIESGO, CRÍTICO)
        document.querySelectorAll('span[style*="background: #d1fae5"], span[style*="background: #dbeafe"], span[style*="background: #fef3c7"], span[style*="background: #fed7d7"]').forEach(badge => {
            // Mantener color del texto, solo cambiar fondo
            const currentBg = badge.style.background;
            if (currentBg.includes('#d1fae5')) {
                badge.style.backgroundColor = '#10b981';
                badge.style.background = '#10b981';
                badge.style.color = 'white';
            } else if (currentBg.includes('#dbeafe')) {
                badge.style.backgroundColor = '#3b82f6';
                badge.style.background = '#3b82f6';
                badge.style.color = 'white';
            } else if (currentBg.includes('#fef3c7')) {
                badge.style.backgroundColor = '#f59e0b';
                badge.style.background = '#f59e0b';
                badge.style.color = 'white';
            } else if (currentBg.includes('#fed7d7')) {
                badge.style.backgroundColor = '#ef4444';
                badge.style.background = '#ef4444';
                badge.style.color = 'white';
            }
        });

        // 9. PÁGINA IMPORTAR EQUIPOS - FICHAS INFORMATIVAS
        // Ficha verde - Actualización Selectiva
        document.querySelectorAll('.bg-green-50').forEach(card => {
            if (!card.matches('button, a')) {
                card.style.backgroundColor = '#1f4033';
                card.style.background = '#1f4033';
                card.style.border = '1px solid #10b981';
                card.style.setProperty('background-color', '#1f4033', 'important');
            }
        });

        // Ficha azul - Plantilla Mejorada
        document.querySelectorAll('.bg-blue-50').forEach(card => {
            if (!card.matches('button, a')) {
                card.style.backgroundColor = '#1e3a5f';
                card.style.background = '#1e3a5f';
                card.style.border = '1px solid #3b82f6';
                card.style.setProperty('background-color', '#1e3a5f', 'important');
            }
        });

        // Ficha amarilla - Consejos Importantes
        document.querySelectorAll('.bg-yellow-50').forEach(card => {
            if (!card.matches('button, a')) {
                card.style.backgroundColor = '#3d3416';
                card.style.background = '#3d3416';
                card.style.border = '1px solid #f59e0b';
                card.style.setProperty('background-color', '#3d3416', 'important');
            }
        });

        console.log('✅ Forzado de estilos completado');
    }

    // Ejecutar cuando cambie el tema
    document.addEventListener('themeChanged', function(e) {
        setTimeout(enforceModoDarkStyles, 300);
    });

    // Ejecutar al cargar si ya está en modo oscuro
    document.addEventListener('DOMContentLoaded', function() {
        enforceModoDarkStyles();

        // Re-ejecutar después de 500ms por si hay contenido dinámico
        setTimeout(enforceModoDarkStyles, 500);
    });

    // Observar cambios en el DOM
    const observer = new MutationObserver(function(mutations) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            enforceModoDarkStyles();
        }
    });

    // Iniciar observador cuando el DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false
        });
    });

})();
