/**
 * onboarding_tour.js  v2.1
 * Tour guiado multi-página con Shepherd.js para usuarios trial de SAM Metrología.
 * Navega por TODAS las secciones de la plataforma (~21 pasos).
 * Persiste estado entre páginas usando localStorage.
 */
(function() {
    'use strict';

    var TOTAL_PASOS = 21;
    var LS_KEY = 'sam_tour_state';

    // =========================================================================
    // Páginas donde el tour NO debe ejecutarse ni redirigir
    // (términos, login, registro, etc.)
    // =========================================================================
    function esPaginaExcluida() {
        var path = window.location.pathname;
        if (path.includes('/terminos-condiciones')) return true;
        if (path.includes('/login'))                return true;
        if (path.includes('/logout'))               return true;
        if (path.includes('/solicitar-trial'))       return true;
        if (path.includes('/trial-exitoso'))         return true;
        return false;
    }

    // =========================================================================
    // Estado (localStorage)
    // =========================================================================
    function guardarEstado(step) {
        localStorage.setItem(LS_KEY, JSON.stringify({step: step, active: true}));
    }

    function obtenerEstado() {
        try {
            var s = localStorage.getItem(LS_KEY);
            return s ? JSON.parse(s) : null;
        } catch (e) {
            return null;
        }
    }

    function limpiarEstado() {
        localStorage.removeItem(LS_KEY);
    }

    // =========================================================================
    // Detectar página actual por URL
    // =========================================================================
    function detectarPagina() {
        var path = window.location.pathname;
        // IMPORTANTE: rutas más específicas primero
        // /core/prestamos/dashboard/ contiene "dashboard", debe chequearse antes
        if (path.includes('/prestamos'))             return 'prestamos';
        if (path.includes('/proveedores'))           return 'proveedores';
        if (path.includes('/procedimientos'))        return 'procedimientos';
        if (path.includes('/calendario'))            return 'calendario';
        if (path.includes('/aprobaciones'))          return 'aprobaciones';
        if (path.includes('/informes'))              return 'informes';
        if (path.match(/\/equipos\/\d+\//))          return 'detalle_equipo';
        if (path.includes('/dashboard'))             return 'dashboard';
        if (path === '/core/' || path === '/core')   return 'equipos';
        // Fallback: /core/home también es equipos
        if (path.includes('/home'))                  return 'equipos';
        return null;
    }

    // =========================================================================
    // CSS personalizado del tour
    // =========================================================================
    function inyectarEstilos() {
        if (document.getElementById('sam-tour-styles')) return;
        var style = document.createElement('style');
        style.id = 'sam-tour-styles';
        style.textContent = [
            '.shepherd-element { max-width: 420px !important; }',
            '.shepherd-content { border-radius: 12px; overflow: hidden; }',
            '.shepherd-header { padding: 14px 18px 10px !important; border-bottom: 3px solid #2563eb !important; background: #f8fafc !important; }',
            '.shepherd-title { font-size: 16px !important; font-weight: 700 !important; color: #1e293b !important; }',
            '.shepherd-text { padding: 14px 18px !important; font-size: 14px !important; line-height: 1.6 !important; color: #334155 !important; }',
            '.shepherd-footer { padding: 10px 18px 14px !important; }',
            '.sam-tour-step-counter { font-size: 12px; color: #94a3b8; margin-bottom: 6px; }',
            '.shepherd-button-primary { background-color: #2563eb !important; color: #fff !important; border: none !important; border-radius: 6px !important; padding: 8px 18px !important; font-weight: 600 !important; }',
            '.shepherd-button-primary:hover { background-color: #1d4ed8 !important; }',
            '.shepherd-button-secondary { background-color: #e2e8f0 !important; color: #475569 !important; border: none !important; border-radius: 6px !important; padding: 8px 18px !important; font-weight: 500 !important; }',
            '.shepherd-button-secondary:hover { background-color: #cbd5e1 !important; }',
            '.shepherd-cancel-icon { color: #94a3b8 !important; }',
            '.shepherd-cancel-icon:hover { color: #475569 !important; }',
            '.shepherd-modal-overlay-container { z-index: 9998 !important; }',
            '.shepherd-element { z-index: 9999 !important; }'
        ].join('\n');
        document.head.appendChild(style);
    }

    // =========================================================================
    // Texto con contador de pasos
    // =========================================================================
    function textoConContador(paso, texto) {
        return '<div class="sam-tour-step-counter">Paso ' + paso + ' de ' + TOTAL_PASOS + '</div>' +
               '<p>' + texto + '</p>';
    }

    // =========================================================================
    // Buscar elemento con fallback
    // =========================================================================
    function buscarElemento(selector, fallback) {
        var el = document.querySelector(selector);
        if (!el && fallback) {
            el = document.querySelector(fallback);
        }
        return el;
    }

    // =========================================================================
    // Buscar URL del equipo demo dinámicamente
    // =========================================================================
    function buscarUrlEquipoDemo() {
        // Busca fila con 'EQ-DEMO-001' en la tabla de equipos
        var rows = document.querySelectorAll('table tbody tr');
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].textContent.indexOf('EQ-DEMO-001') !== -1) {
                var link = rows[i].querySelector('a[href*="/equipos/"]');
                if (link) return link.getAttribute('href');
            }
        }
        // Fallback: buscar cualquier link a detalle de equipo
        var anyLink = document.querySelector('a[href*="/equipos/"]');
        if (anyLink) return anyLink.getAttribute('href');
        return null;
    }

    // =========================================================================
    // Definición de pasos por página
    // =========================================================================
    function obtenerTodosLosPasos() {
        return [
            // --- DASHBOARD (pasos 1-5) ---
            { stepNum: 1, pagina: 'dashboard', id: 'bienvenida', title: 'Bienvenido a SAM Metrolog\u00eda', isModal: true,
              text: 'Te vamos a dar un recorrido completo por la plataforma para que conozcas todas las funciones. Hemos creado un equipo de demostraci\u00f3n para que veas c\u00f3mo funciona todo.' },
            { stepNum: 2, pagina: 'dashboard', id: 'sidebar', title: 'Men\u00fa de Navegaci\u00f3n',
              selector: '#sidebar', fallback: '.sidebar', position: 'right',
              text: 'Este es tu men\u00fa de navegaci\u00f3n. Desde aqu\u00ed accedes a todas las secciones: equipos, calibraciones, informes, pr\u00e9stamos, calendario y m\u00e1s.' },
            { stepNum: 3, pagina: 'dashboard', id: 'estadisticas', title: 'M\u00e9tricas en Tiempo Real',
              selector: '#stats-grid', fallback: '.stats-grid', position: 'bottom',
              text: 'Tu panel de m\u00e9tricas en tiempo real. Muestra el estado general de tus equipos, calibraciones pendientes, mantenimientos y comprobaciones.' },
            { stepNum: 4, pagina: 'dashboard', id: 'graficos', title: 'Gr\u00e1ficos de Cumplimiento',
              selector: '.chart-container', fallback: 'canvas', position: 'top',
              text: 'Los gr\u00e1ficos muestran el cumplimiento de tus actividades metrol\u00f3gicas. Se actualizan autom\u00e1ticamente cuando registres actividades.' },
            { stepNum: 5, pagina: 'dashboard', id: 'ir-equipos', title: 'Vamos a Equipos',
              selector: 'a[href*="home"]', fallback: '.fa-boxes', position: 'right',
              text: 'Ahora vamos a ver la secci\u00f3n de Equipos, el coraz\u00f3n de SAM.',
              navigateTo: '/core/' },

            // --- EQUIPOS LISTA (pasos 6-9) ---
            { stepNum: 6, pagina: 'equipos', id: 'lista-equipos', title: 'Listado de Equipos',
              selector: '.home-title', fallback: 'h1', position: 'bottom',
              text: 'Aqu\u00ed ves todos tus equipos de medici\u00f3n. Puedes buscar por c\u00f3digo, nombre o marca, y filtrar por tipo o estado.' },
            { stepNum: 7, pagina: 'equipos', id: 'editar-formato', title: 'Formato de Empresa',
              selector: 'a[href*="editar_empresa_formato"]', fallback: null, position: 'bottom',
              text: 'En \'Editar Formato\' configuras la codificaci\u00f3n de los documentos de tu empresa: c\u00f3digos de formatos, versi\u00f3n y estructura de reportes para calibraciones, mantenimientos y comprobaciones.' },
            { stepNum: 8, pagina: 'equipos', id: 'botones-equipo', title: 'Agregar Equipos',
              selector: 'a[href*="a\u00f1adir_equipo"]', fallback: null, position: 'bottom',
              text: 'Puedes agregar equipos uno por uno con \'A\u00f1adir Equipo\', o importar muchos a la vez desde un archivo Excel con \'Importar Equipos\'.' },
            { stepNum: 9, pagina: 'equipos', id: 'equipo-demo', title: 'Equipo de Demostraci\u00f3n',
              selector: null, fallback: null, position: 'bottom', isDynamic: true,
              text: 'Este es tu equipo de demostraci\u00f3n. Vamos a ver su detalle completo.',
              navigateTo: '__EQUIPO_DEMO__' },

            // --- DETALLE EQUIPO (pasos 10-14) ---
            { stepNum: 10, pagina: 'detalle_equipo', id: 'info-equipo', title: 'Ficha del Equipo',
              selector: '.bg-gray-50.p-4', fallback: '.card', position: 'bottom',
              text: 'La ficha del equipo muestra toda la informaci\u00f3n: c\u00f3digo, marca, modelo, ubicaci\u00f3n, estado y especificaciones t\u00e9cnicas.' },
            { stepNum: 11, pagina: 'detalle_equipo', id: 'botones-accion', title: 'Acciones del Equipo',
              selector: '.flex.flex-wrap.gap-2', fallback: '.btn-group', position: 'bottom',
              text: 'Desde aqu\u00ed puedes: editar el equipo, descargar su Hoja de Vida en PDF, ver historial de pr\u00e9stamos, inactivar o dar de baja.' },
            { stepNum: 12, pagina: 'detalle_equipo', id: 'calibraciones', title: 'Calibraciones',
              selector: 'a[href*="a\u00f1adir_calibracion"]', fallback: null, position: 'top',
              text: 'Calibraciones: hay dos formas de registrarlas. 1) Subir el certificado PDF del proveedor con \'A\u00f1adir Calibraci\u00f3n\', o 2) usar los formatos de la plataforma con \'Confirmaci\u00f3n Metrol\u00f3gica\' que genera el PDF autom\u00e1ticamente.' },
            { stepNum: 13, pagina: 'detalle_equipo', id: 'mantenimientos', title: 'Mantenimientos',
              selector: 'a[href*="a\u00f1adir_mantenimiento"]', fallback: null, position: 'top',
              text: 'Mantenimientos: igual que calibraciones, puedes registrar uno simple subiendo documentos, o usar \'Mantenimiento con Actividades\' para el formato detallado de la plataforma.' },
            { stepNum: 14, pagina: 'detalle_equipo', id: 'comprobaciones', title: 'Comprobaciones Intermedias',
              selector: 'a[href*="a\u00f1adir_comprobacion"]', fallback: null, position: 'top',
              text: 'Comprobaciones Intermedias: verificaciones entre calibraciones para asegurar que el equipo sigue midiendo correctamente. Tambi\u00e9n puedes subirlas o usar el formato de la plataforma.',
              navigateTo: '/core/proveedores/' },

            // --- PROVEEDORES (paso 15) ---
            { stepNum: 15, pagina: 'proveedores', id: 'proveedores', title: 'Proveedores',
              selector: 'h1', fallback: '.page-title', position: 'bottom',
              text: 'Aqu\u00ed gestionas los laboratorios de calibraci\u00f3n y proveedores de servicio metrol\u00f3gico. Puedes registrar sus datos de contacto, tipo de servicio y asignarlos a las calibraciones y mantenimientos.',
              navigateTo: '/core/procedimientos/' },

            // --- PROCEDIMIENTOS (paso 16) ---
            { stepNum: 16, pagina: 'procedimientos', id: 'procedimientos', title: 'Procedimientos',
              selector: 'h1', fallback: '.page-title', position: 'bottom',
              text: 'Los Procedimientos son los documentos t\u00e9cnicos de tu empresa (seg\u00fan ISO/IEC 17020). Aqu\u00ed guardas las instrucciones de calibraci\u00f3n, mantenimiento y verificaci\u00f3n con c\u00f3digo, versi\u00f3n y fecha.',
              navigateTo: '/core/prestamos/dashboard/' },

            // --- PRESTAMOS (paso 17) ---
            { stepNum: 17, pagina: 'prestamos', id: 'prestamos', title: 'Control de Pr\u00e9stamos',
              selector: 'h1', fallback: '.page-title', position: 'bottom',
              text: 'Control de Pr\u00e9stamos: registra la salida y devoluci\u00f3n de equipos del laboratorio. Incluye: responsable del pr\u00e9stamo, fecha de entrega y devoluci\u00f3n esperada, estado (activo, devuelto, vencido), y alertas autom\u00e1ticas cuando un pr\u00e9stamo supera la fecha l\u00edmite.',
              navigateTo: '/core/calendario/' },

            // --- CALENDARIO (paso 18) ---
            { stepNum: 18, pagina: 'calendario', id: 'calendario', title: 'Calendario',
              selector: '#calendar', fallback: 'h1', position: 'bottom',
              text: 'El Calendario muestra visualmente todas tus actividades programadas con c\u00f3digos de color: calibraciones (azul), mantenimientos (verde) y comprobaciones (naranja). Puedes filtrar por tipo o responsable, hacer clic en un evento para ver su detalle, y exportar a iCal para sincronizar con Google Calendar o Outlook.',
              navigateTo: '/core/aprobaciones/' },

            // --- APROBACIONES (paso 19) ---
            { stepNum: 19, pagina: 'aprobaciones', id: 'aprobaciones', title: 'Flujo de Aprobaciones',
              selector: 'h1', fallback: '.page-title', position: 'bottom',
              text: 'Flujo de Aprobaciones: el T\u00e9cnico genera documentos (confirmaci\u00f3n metrol\u00f3gica, intervalos de calibraci\u00f3n, comprobaciones) y el Administrador o Gerencia los revisa y aprueba o rechaza. Importante: un usuario NO puede aprobar sus propios documentos, garantizando la imparcialidad seg\u00fan ISO/IEC 17020.',
              navigateTo: '/core/informes/' },

            // --- INFORMES (paso 20) ---
            { stepNum: 20, pagina: 'informes', id: 'informes', title: 'Informes y Reportes',
              selector: 'h1', fallback: '.page-title', position: 'bottom',
              text: 'Desde Informes generas documentos profesionales: Hojas de Vida de equipos en PDF, reportes de vencimientos pr\u00f3ximos, exportar listados completos a Excel, y descargar paquetes ZIP con toda la documentaci\u00f3n de un equipo (certificados, reportes, comprobaciones) para auditor\u00edas o clientes.',
              navigateTo: '/core/dashboard/' },

            // --- FINAL (paso 21) ---
            { stepNum: 21, pagina: 'dashboard', id: 'final', title: '\u00a1Tour Completado!', isModal: true,
              text: '\u00a1Felicidades! Ya conoces todas las secciones de SAM Metrolog\u00eda. Tu siguiente paso: registra una calibraci\u00f3n para el equipo demo. Si necesitas volver a ver este recorrido, usa el bot\u00f3n \'Repetir tour completo\' en el checklist del panel.' }
        ];
    }

    // =========================================================================
    // Obtener pasos para la página actual a partir de un stepNum dado
    // =========================================================================
    function obtenerPasosPagina(pagina, fromStep) {
        var todos = obtenerTodosLosPasos();
        var pasos = [];
        for (var i = 0; i < todos.length; i++) {
            var p = todos[i];
            if (p.stepNum >= fromStep && p.pagina === pagina) {
                pasos.push(p);
            }
            // Si ya estamos en la página y encontramos un paso que navega, incluirlo y parar
            if (pasos.length > 0 && p.navigateTo && p.pagina === pagina && p.stepNum >= fromStep) {
                break;
            }
        }
        return pasos;
    }

    // =========================================================================
    // Obtener CSRF token
    // =========================================================================
    function obtenerCSRF() {
        var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) return csrfInput.value;
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    // =========================================================================
    // Marcar tour completado (POST al servidor)
    // =========================================================================
    function marcarTourCompletado() {
        fetch('/core/onboarding/completar-tour/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': obtenerCSRF(),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });
    }

    // =========================================================================
    // Crear tour para la página actual
    // =========================================================================
    function crearTourPagina(pasos) {
        var tour = new Shepherd.Tour({
            useModalOverlay: true,
            defaultStepOptions: {
                classes: 'shadow-lg rounded-lg',
                scrollTo: { behavior: 'smooth', block: 'center' },
                cancelIcon: { enabled: true },
            }
        });

        for (var i = 0; i < pasos.length; i++) {
            (function(paso, idx) {
                var isLast = (idx === pasos.length - 1);
                var isFirst = (idx === 0);
                var stepConfig = {
                    id: paso.id,
                    title: paso.title,
                    text: textoConContador(paso.stepNum, paso.text),
                };

                // Attach to element or show as modal
                if (!paso.isModal) {
                    var element = null;
                    if (paso.isDynamic && paso.id === 'equipo-demo') {
                        // Buscar fila del equipo demo
                        var rows = document.querySelectorAll('table tbody tr');
                        for (var r = 0; r < rows.length; r++) {
                            if (rows[r].textContent.indexOf('EQ-DEMO-001') !== -1) {
                                element = rows[r];
                                break;
                            }
                        }
                    } else if (paso.selector) {
                        element = buscarElemento(paso.selector, paso.fallback);
                    }

                    if (element) {
                        stepConfig.attachTo = { element: element, on: paso.position || 'bottom' };
                    }
                }

                // Buttons
                var buttons = [];
                if (!isFirst) {
                    buttons.push({ text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' });
                }

                if (paso.stepNum === TOTAL_PASOS) {
                    // Last step of entire tour
                    buttons.push({
                        text: 'Finalizar',
                        classes: 'shepherd-button-primary',
                        action: function() {
                            limpiarEstado();
                            marcarTourCompletado();
                            tour.complete();
                        }
                    });
                } else if (paso.navigateTo) {
                    // Step that navigates to another page
                    buttons.push({
                        text: 'Siguiente',
                        classes: 'shepherd-button-primary',
                        action: function() {
                            var nextStep = paso.stepNum + 1;
                            guardarEstado(nextStep);
                            var url = paso.navigateTo;
                            if (url === '__EQUIPO_DEMO__') {
                                url = buscarUrlEquipoDemo();
                                if (!url) {
                                    // If no demo equipment found, skip to proveedores
                                    guardarEstado(15);
                                    url = '/core/proveedores/';
                                }
                            }
                            window.location.href = url;
                        }
                    });
                } else {
                    buttons.push({ text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' });
                }

                stepConfig.buttons = buttons;
                tour.addStep(stepConfig);
            })(pasos[i], i);
        }

        tour.on('cancel', function() {
            limpiarEstado();
            marcarTourCompletado();
        });

        return tour;
    }

    // =========================================================================
    // Buscar el siguiente paso que tenga navigateTo para saltar páginas
    // =========================================================================
    function buscarSiguientePaginaDesde(fromStep) {
        var todos = obtenerTodosLosPasos();
        // Buscar el paso actual o el siguiente que navegue a otra página
        for (var i = 0; i < todos.length; i++) {
            if (todos[i].stepNum >= fromStep && todos[i].navigateTo) {
                var nextStep = todos[i].stepNum + 1;
                var url = todos[i].navigateTo;
                if (url === '__EQUIPO_DEMO__') {
                    // Saltar detalle equipo, ir a proveedores
                    return { step: 15, url: '/core/proveedores/' };
                }
                return { step: nextStep, url: url };
            }
        }
        // Si no hay más navegaciones, ir al final en dashboard
        return { step: 21, url: '/core/dashboard/' };
    }

    // =========================================================================
    // Ejecutar tour en la página actual
    // =========================================================================
    function ejecutarTour(fromStep) {
        var pagina = detectarPagina();

        // Si la página no se reconoce (403, error, redirect), saltar a la siguiente
        if (!pagina) {
            var siguiente = buscarSiguientePaginaDesde(fromStep);
            guardarEstado(siguiente.step);
            window.location.href = siguiente.url;
            return;
        }

        var pasos = obtenerPasosPagina(pagina, fromStep);
        if (pasos.length === 0) {
            // Estamos en una página reconocida pero no hay pasos desde este step.
            // Buscar a qué página debería ir el step actual.
            var todos = obtenerTodosLosPasos();
            for (var i = 0; i < todos.length; i++) {
                if (todos[i].stepNum === fromStep) {
                    var targetPagina = todos[i].pagina;
                    var urlMap = {
                        'dashboard': '/core/dashboard/',
                        'equipos': '/core/',
                        'proveedores': '/core/proveedores/',
                        'procedimientos': '/core/procedimientos/',
                        'prestamos': '/core/prestamos/dashboard/',
                        'calendario': '/core/calendario/',
                        'aprobaciones': '/core/aprobaciones/',
                        'informes': '/core/informes/'
                    };
                    if (urlMap[targetPagina] && targetPagina !== pagina) {
                        window.location.href = urlMap[targetPagina];
                        return;
                    }
                    break;
                }
            }
            // Si estamos en la página correcta pero no hay pasos, saltar al siguiente
            var sig = buscarSiguientePaginaDesde(fromStep);
            guardarEstado(sig.step);
            window.location.href = sig.url;
            return;
        }

        inyectarEstilos();
        var tour = crearTourPagina(pasos);
        tour.start();
    }

    // =========================================================================
    // Iniciar tour completo (botón "Repetir tour")
    // =========================================================================
    function iniciarTourOnboarding() {
        limpiarEstado();
        guardarEstado(1);
        var pagina = detectarPagina();
        if (pagina === 'dashboard') {
            ejecutarTour(1);
        } else {
            window.location.href = '/core/dashboard/';
        }
    }

    // Exponer globalmente para el botón "Repetir tour"
    window.iniciarTourOnboarding = iniciarTourOnboarding;

    // =========================================================================
    // Auto-inicio / resume en cada carga de página
    // =========================================================================
    document.addEventListener('DOMContentLoaded', function() {
        // NO ejecutar el tour en páginas excluidas (términos, login, etc.)
        if (esPaginaExcluida()) return;

        var estado = obtenerEstado();

        // Auto-inicio: primera vez (variable del servidor indica que tour no se ha completado)
        // Solo arranca si estamos en el dashboard (después de aceptar términos)
        if (!estado && typeof samOnboardingTourCompletado !== 'undefined'
            && samOnboardingTourCompletado === false) {
            var pagina = detectarPagina();
            if (pagina !== 'dashboard') {
                // No estamos en el dashboard: no hacer nada, esperar a que
                // el usuario llegue al dashboard (después de aceptar términos)
                return;
            }
            setTimeout(function() {
                guardarEstado(1);
                ejecutarTour(1);
            }, 800);
            return;
        }

        // Resume: tour activo desde navegación anterior
        if (estado && estado.active) {
            setTimeout(function() { ejecutarTour(estado.step); }, 500);
        }
    });

})();
