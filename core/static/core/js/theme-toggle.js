/**
 * SAM METROLOGÍA - SISTEMA DE TEMAS
 * Gestión del toggle entre Modo Oscuro y Modo Claro
 * con persistencia en localStorage
 */

(function() {
    'use strict';

    // Configuración
    const STORAGE_KEY = 'sam-theme-preference';
    const THEME_ATTRIBUTE = 'data-theme';
    const DEFAULT_THEME = 'light'; // Modo claro por defecto

    /**
     * Obtiene el tema almacenado o el predeterminado
     */
    function getSavedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
        } catch (e) {
            console.warn('No se pudo acceder a localStorage:', e);
            return DEFAULT_THEME;
        }
    }

    /**
     * Guarda la preferencia de tema
     */
    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            console.warn('No se pudo guardar en localStorage:', e);
        }
    }

    /**
     * Aplica el tema al documento
     */
    function applyTheme(theme) {
        const root = document.documentElement;

        if (theme === 'light') {
            root.setAttribute(THEME_ATTRIBUTE, 'light');
        } else {
            root.setAttribute(THEME_ATTRIBUTE, 'dark');
        }

        // Actualizar icono del toggle si existe
        updateToggleIcon(theme);

        // Emitir evento personalizado para que otros componentes puedan reaccionar
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme }
        }));
    }

    /**
     * Actualiza el icono del toggle
     */
    function updateToggleIcon(theme) {
        const toggleIcon = document.querySelector('.theme-toggle-icon');
        if (!toggleIcon) return;

        if (theme === 'light') {
            toggleIcon.classList.remove('fa-moon');
            toggleIcon.classList.add('fa-sun');
            toggleIcon.setAttribute('title', 'Cambiar a modo oscuro');
        } else {
            toggleIcon.classList.remove('fa-sun');
            toggleIcon.classList.add('fa-moon');
            toggleIcon.setAttribute('title', 'Cambiar a modo claro');
        }
    }

    /**
     * Alterna entre temas
     */
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute(THEME_ATTRIBUTE);
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        // Agregar clase de animación al botón
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.classList.add('changing');
            setTimeout(() => {
                toggleButton.classList.remove('changing');
            }, 600);
        }

        applyTheme(newTheme);
        saveTheme(newTheme);

        // Feedback visual
        showThemeFeedback(newTheme);
    }

    /**
     * Muestra feedback visual del cambio de tema
     */
    function showThemeFeedback(theme) {
        const themeName = theme === 'light' ? 'Modo Claro' : 'Modo Oscuro';

        // Crear elemento de notificación si no existe
        let notification = document.getElementById('theme-notification');

        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'theme-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                background-color: var(--bg-secondary);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                box-shadow: var(--shadow-lg);
                z-index: 9999;
                font-size: 0.9rem;
                font-weight: 500;
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: none;
            `;
            document.body.appendChild(notification);
        }

        notification.textContent = `✓ ${themeName} activado`;
        notification.style.opacity = '1';

        // Ocultar después de 2 segundos
        setTimeout(() => {
            notification.style.opacity = '0';
        }, 2000);
    }

    /**
     * Inicializa el sistema de temas
     */
    function initThemeSystem() {
        // Aplicar tema guardado inmediatamente (antes de que cargue la página)
        const savedTheme = getSavedTheme();
        applyTheme(savedTheme);

        // Configurar evento del toggle cuando el DOM esté listo
        document.addEventListener('DOMContentLoaded', function() {
            const toggleButton = document.querySelector('.theme-toggle');

            if (toggleButton) {
                toggleButton.addEventListener('click', toggleTheme);

                // Soporte para teclado
                toggleButton.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleTheme();
                    }
                });

                // Hacer el botón accesible
                toggleButton.setAttribute('role', 'button');
                toggleButton.setAttribute('tabindex', '0');
                toggleButton.setAttribute('aria-label', 'Alternar tema oscuro/claro');
            }

            // Escuchar cambios de preferencia del sistema (opcional)
            if (window.matchMedia) {
                const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

                darkModeQuery.addEventListener('change', function(e) {
                    // Solo aplicar si no hay preferencia guardada
                    if (!localStorage.getItem(STORAGE_KEY)) {
                        const systemTheme = e.matches ? 'dark' : 'light';
                        applyTheme(systemTheme);
                    }
                });
            }
        });
    }

    // Exportar funciones para uso global si es necesario
    window.SAMTheme = {
        toggle: toggleTheme,
        apply: applyTheme,
        get: getSavedTheme
    };

    // Inicializar
    initThemeSystem();

})();