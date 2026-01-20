/**
 * SAM METROLOGÍA - ATAJOS DE TECLADO
 * Sistema de keyboard shortcuts para navegación rápida
 */

(function() {
    'use strict';

    // Configuración de atajos
    const SHORTCUTS = {
        'alt+n': {
            name: 'Nuevo Equipo',
            action: () => navigateTo('/core/equipos/añadir/'),
            description: 'Crear nuevo equipo'
        },
        'alt+c': {
            name: 'Nueva Calibración',
            action: () => showCalibrationDialog(),
            description: 'Registrar nueva calibración'
        },
        'alt+m': {
            name: 'Nuevo Mantenimiento',
            action: () => showMaintenanceDialog(),
            description: 'Registrar nuevo mantenimiento'
        },
        'alt+b': {
            name: 'Búsqueda',
            action: () => focusSearch(),
            description: 'Enfocar barra de búsqueda'
        },
        'alt+d': {
            name: 'Dashboard',
            action: () => navigateTo('/core/dashboard/'),
            description: 'Ir al panel de control'
        },
        'alt+e': {
            name: 'Lista Equipos',
            action: () => navigateTo('/core/'),
            description: 'Ver lista de equipos'
        },
        'alt+i': {
            name: 'Informes',
            action: () => navigateTo('/core/informes/'),
            description: 'Ir a informes'
        },
        '?': {
            name: 'Ayuda',
            action: () => toggleHelp(),
            description: 'Mostrar/ocultar ayuda de atajos'
        },
        'escape': {
            name: 'Cerrar',
            action: () => closeModals(),
            description: 'Cerrar modales/diálogos'
        }
    };

    /**
     * Navega a una URL
     */
    function navigateTo(url) {
        window.location.href = url;
    }

    /**
     * Muestra diálogo de calibración
     */
    function showCalibrationDialog() {
        // Intentar encontrar el botón de nueva calibración
        const calibBtn = document.querySelector('a[href*="calibraciones/añadir"]');
        if (calibBtn) {
            calibBtn.click();
        } else {
            showNotification('Selecciona un equipo primero', 'warning');
        }
    }

    /**
     * Muestra diálogo de mantenimiento
     */
    function showMaintenanceDialog() {
        // Intentar encontrar el botón de nuevo mantenimiento
        const maintBtn = document.querySelector('a[href*="mantenimientos/añadir"]');
        if (maintBtn) {
            maintBtn.click();
        } else {
            showNotification('Selecciona un equipo primero', 'warning');
        }
    }

    /**
     * Enfoca la barra de búsqueda
     */
    function focusSearch() {
        const searchInputs = document.querySelectorAll('input[type="search"], input[name="query"], input[placeholder*="uscar"]');
        if (searchInputs.length > 0) {
            searchInputs[0].focus();
            searchInputs[0].select();
        } else {
            showNotification('No hay campo de búsqueda en esta página', 'info');
        }
    }

    /**
     * Cierra modales abiertos
     */
    function closeModals() {
        // Cerrar ayuda si está abierta
        const helpModal = document.getElementById('keyboard-help-modal');
        if (helpModal && helpModal.style.display !== 'none') {
            toggleHelp();
            return;
        }

        // Cerrar otros modales
        const modals = document.querySelectorAll('.modal, [role="dialog"]');
        modals.forEach(modal => {
            if (modal.style.display !== 'none') {
                modal.style.display = 'none';
                // Trigger evento de cierre si existe
                const closeBtn = modal.querySelector('[data-dismiss="modal"], .close, .modal-close');
                if (closeBtn) closeBtn.click();
            }
        });
    }

    /**
     * Muestra/oculta el modal de ayuda
     */
    function toggleHelp() {
        let helpModal = document.getElementById('keyboard-help-modal');

        if (!helpModal) {
            helpModal = createHelpModal();
            document.body.appendChild(helpModal);
        }

        if (helpModal.style.display === 'none' || !helpModal.style.display) {
            helpModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        } else {
            helpModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * Crea el modal de ayuda
     */
    function createHelpModal() {
        const modal = document.createElement('div');
        modal.id = 'keyboard-help-modal';
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.2s ease;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 2rem;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: var(--shadow-xl);
            animation: slideIn 0.3s ease;
        `;

        let html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin: 0;">⌨️ Atajos de Teclado</h2>
                <button onclick="document.getElementById('keyboard-help-modal').style.display='none'; document.body.style.overflow='';"
                        style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary); padding: 0.5rem;"
                        aria-label="Cerrar">×</button>
            </div>
            <div style="display: grid; gap: 1rem;">
        `;

        Object.entries(SHORTCUTS).forEach(([key, shortcut]) => {
            const keyDisplay = key.replace('alt+', 'Alt + ').toUpperCase();
            html += `
                <div style="display: flex; justify-content: space-between; padding: 0.75rem; background: var(--bg-tertiary); border-radius: 8px;">
                    <span style="font-weight: 600;">${shortcut.description}</span>
                    <kbd style="background: var(--bg-primary); padding: 0.25rem 0.75rem; border-radius: 4px; font-family: monospace; font-size: 0.875rem; border: 1px solid var(--border-color);">${keyDisplay}</kbd>
                </div>
            `;
        });

        html += `
            </div>
            <div style="margin-top: 1.5rem; padding: 1rem; background: var(--accent-subtle); border-radius: 8px; border-left: 4px solid var(--accent-primary);">
                <p style="margin: 0; font-size: 0.875rem; color: var(--text-secondary);">
                    💡 <strong>Consejo:</strong> Presiona <kbd style="background: var(--bg-primary); padding: 0.2rem 0.5rem; border-radius: 4px;">?</kbd> en cualquier momento para ver esta ayuda.
                </p>
            </div>
        `;

        content.innerHTML = html;
        modal.appendChild(content);

        // Cerrar al hacer clic fuera
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                toggleHelp();
            }
        });

        return modal;
    }

    /**
     * Muestra una notificación temporal
     */
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 2px solid ${type === 'warning' ? 'var(--color-warning)' : 'var(--accent-primary)'};
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 9999;
            font-size: 0.9rem;
            max-width: 300px;
            animation: slideInRight 0.3s ease;
        `;

        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Maneja los eventos de teclado
     */
    function handleKeyPress(e) {
        // Ignorar si está escribiendo en un input/textarea
        if (e.target.matches('input, textarea, select, [contenteditable="true"]')) {
            // Excepto para Escape y ?
            if (e.key !== 'Escape' && e.key !== '?') {
                return;
            }
        }

        // Construir la combinación de teclas
        let combo = [];
        if (e.altKey) combo.push('alt');
        if (e.ctrlKey) combo.push('ctrl');
        if (e.shiftKey) combo.push('shift');
        combo.push(e.key.toLowerCase());

        const shortcutKey = combo.join('+');

        // Ejecutar atajo si existe
        if (SHORTCUTS[shortcutKey]) {
            e.preventDefault();
            SHORTCUTS[shortcutKey].action();

            // Mostrar feedback visual
            showShortcutFeedback(SHORTCUTS[shortcutKey].name);
        }
    }

    /**
     * Muestra feedback visual al usar un atajo
     */
    function showShortcutFeedback(shortcutName) {
        const feedback = document.createElement('div');
        feedback.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 0.75rem 1.5rem;
            background: var(--accent-primary);
            color: white;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 9999;
            font-size: 0.875rem;
            font-weight: 600;
            opacity: 0;
            animation: fadeInOut 1.5s ease;
        `;

        feedback.textContent = `⌨️ ${shortcutName}`;
        document.body.appendChild(feedback);

        setTimeout(() => feedback.remove(), 1500);
    }

    /**
     * Agrega las animaciones CSS
     */
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(100px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes slideOutRight {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100px);
                }
            }

            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
                20% { opacity: 1; transform: translateX(-50%) translateY(0); }
                80% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
            }

            /* Scrollbar para el modal de ayuda en dark mode */
            [data-theme="dark"] #keyboard-help-modal ::-webkit-scrollbar {
                width: 8px;
            }

            [data-theme="dark"] #keyboard-help-modal ::-webkit-scrollbar-track {
                background: var(--bg-primary);
            }

            [data-theme="dark"] #keyboard-help-modal ::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 4px;
            }

            [data-theme="dark"] #keyboard-help-modal ::-webkit-scrollbar-thumb:hover {
                background: var(--text-secondary);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Inicializa el sistema de atajos
     */
    function init() {
        injectStyles();
        document.addEventListener('keydown', handleKeyPress);

        // Agregar indicador visual de que los atajos están disponibles
        console.log('⌨️ Atajos de teclado activados. Presiona "?" para ver la ayuda.');
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exportar para uso global si es necesario
    window.SAMKeyboard = {
        showHelp: toggleHelp,
        shortcuts: SHORTCUTS
    };

})();
