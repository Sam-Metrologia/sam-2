/**
 * Sistema de Heartbeat para mantener sesión activa
 *
 * Detecta actividad del usuario (mouse, teclado, clicks, scroll) y envía
 * un "ping" al servidor cada 5 minutos si hay actividad para mantener
 * la sesión activa.
 *
 * La sesión expirará después de 30 minutos de INACTIVIDAD real.
 */

(function() {
    'use strict';

    // Variables de estado
    let lastActivityTime = Date.now();
    let heartbeatInterval;
    let warningShown = false;

    // Configuración
    const HEARTBEAT_INTERVAL = 5 * 60 * 1000; // 5 minutos
    const WARNING_TIME = 25 * 60 * 1000; // 25 minutos (5 min antes de expirar)
    const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutos
    const WARNING_CHECK_INTERVAL = 60 * 1000; // Verificar cada minuto

    /**
     * Detectar actividad del usuario
     */
    const activityEvents = [
        'mousedown',
        'mousemove',
        'keydown',
        'scroll',
        'touchstart',
        'click'
    ];

    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            lastActivityTime = Date.now();

            // Remover advertencia si el usuario vuelve a estar activo
            if (warningShown) {
                removeWarning();
                warningShown = false;
            }
        }, { passive: true });
    });

    /**
     * Obtener cookie CSRF para requests
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Enviar heartbeat al servidor
     */
    function sendHeartbeat() {
        const inactiveTime = Date.now() - lastActivityTime;

        // Solo enviar si ha habido actividad reciente (menos de 5 minutos)
        if (inactiveTime < HEARTBEAT_INTERVAL) {
            fetch('/core/session-heartbeat/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: Date.now(),
                    inactive_time: Math.floor(inactiveTime / 1000) // En segundos
                })
            })
            .then(response => {
                if (!response.ok) {
                    console.warn('Heartbeat failed:', response.status);
                }
                return response.json();
            })
            .then(data => {
                console.debug('Heartbeat sent successfully:', data);
            })
            .catch(err => {
                console.error('Heartbeat error:', err);
            });
        } else {
            console.debug('Skipping heartbeat - user inactive for', Math.floor(inactiveTime / 1000), 'seconds');
        }
    }

    /**
     * Mostrar advertencia de sesión próxima a expirar
     */
    function showWarning() {
        // No mostrar si ya existe
        if (document.getElementById('session-warning')) {
            return;
        }

        const warning = document.createElement('div');
        warning.id = 'session-warning';
        warning.className = 'alert alert-warning position-fixed top-0 start-50 translate-middle-x mt-3 shadow-lg';
        warning.style.cssText = 'z-index: 9999; max-width: 500px; animation: slideDown 0.3s ease-out;';
        warning.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <div class="flex-grow-1">
                    <strong>⚠️ Tu sesión está próxima a expirar</strong>
                    <br>
                    <small>Mueve el mouse o presiona una tecla para mantenerla activa.</small>
                </div>
                <button type="button" class="btn-close ms-2" aria-label="Close"></button>
            </div>
        `;

        // Agregar estilo de animación si no existe
        if (!document.getElementById('session-warning-styles')) {
            const style = document.createElement('style');
            style.id = 'session-warning-styles';
            style.textContent = `
                @keyframes slideDown {
                    from {
                        transform: translateX(-50%) translateY(-100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(-50%) translateY(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(warning);
        warningShown = true;

        // Agregar event listener al botón de cerrar
        const closeBtn = warning.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', removeWarning);
        }

        // Remover después de 15 segundos si no hay interacción
        setTimeout(() => {
            if (document.getElementById('session-warning')) {
                removeWarning();
            }
        }, 15000);
    }

    /**
     * Remover advertencia
     */
    function removeWarning() {
        const warning = document.getElementById('session-warning');
        if (warning) {
            warning.style.animation = 'slideDown 0.3s ease-out reverse';
            setTimeout(() => warning.remove(), 300);
        }
        warningShown = false;
    }

    /**
     * Verificar si mostrar advertencia
     */
    function checkInactivity() {
        const inactiveTime = Date.now() - lastActivityTime;

        // Mostrar advertencia si está inactivo por más de 25 minutos
        if (inactiveTime > WARNING_TIME && inactiveTime < SESSION_TIMEOUT && !warningShown) {
            showWarning();
        }

        // Si está activo, asegurar que no hay advertencia
        if (inactiveTime < WARNING_TIME && warningShown) {
            removeWarning();
        }
    }

    /**
     * Inicializar sistema de heartbeat
     */
    function init() {
        console.log('Session keepalive initialized');

        // Iniciar heartbeat cada 5 minutos
        heartbeatInterval = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);

        // Verificar inactividad cada minuto
        setInterval(checkInactivity, WARNING_CHECK_INTERVAL);

        // Enviar heartbeat inicial después de 1 minuto
        setTimeout(sendHeartbeat, 60000);
    }

    /**
     * Limpiar al cerrar página
     */
    window.addEventListener('beforeunload', () => {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
        }
    });

    // Iniciar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
