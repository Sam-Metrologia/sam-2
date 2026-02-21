/**
 * onboarding_tour.js
 * Tour guiado con Shepherd.js para usuarios trial de SAM Metrologia.
 */

function iniciarTourOnboarding() {
    var tour = new Shepherd.Tour({
        useModalOverlay: true,
        defaultStepOptions: {
            classes: 'shadow-lg rounded-lg',
            scrollTo: true,
            cancelIcon: { enabled: true },
        }
    });

    // Paso 1: Bienvenida (sin anchor, centrado)
    tour.addStep({
        id: 'bienvenida',
        title: 'Bienvenido a SAM Metrologia',
        text: 'Este tour te guiara por las funciones principales del sistema. ' +
              'SAM te ayuda a gestionar equipos, calibraciones y generar reportes ' +
              'cumpliendo con la norma ISO/IEC 17020:2012.',
        buttons: [
            {
                text: 'Siguiente',
                action: tour.next,
                classes: 'shepherd-button-primary'
            }
        ]
    });

    // Paso 2: Estadisticas (cards de equipos)
    var statsGrid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3');
    if (statsGrid) {
        tour.addStep({
            id: 'estadisticas',
            title: 'Resumen de tus equipos',
            text: 'Aqui veras el resumen de tus equipos: totales, activos, ' +
                  'calibraciones vencidas y proximas actividades.',
            attachTo: { element: '.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3', on: 'bottom' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Paso 3: Crear equipo (link en sidebar o boton)
    var sidebarEquipos = document.querySelector('a[href*="equipos"]');
    if (sidebarEquipos) {
        tour.addStep({
            id: 'crear-equipo',
            title: 'Empieza creando un equipo',
            text: 'El primer paso es registrar tus equipos de medicion. ' +
                  'Desde aqui puedes acceder al listado y agregar nuevos equipos.',
            attachTo: { element: 'a[href*="equipos"]', on: 'right' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Paso 4: Calibraciones (graficos)
    var chartContainer = document.querySelector('.chart-container');
    if (chartContainer) {
        tour.addStep({
            id: 'calibraciones',
            title: 'Registra calibraciones',
            text: 'Despues de crear equipos, registra sus calibraciones. ' +
                  'Aqui veras graficos con el estado de tus calibraciones y actividades.',
            attachTo: { element: '.chart-container', on: 'top' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Paso 5: Reportes
    var linkInformes = document.querySelector('a[href*="informes"]');
    if (linkInformes) {
        tour.addStep({
            id: 'reportes',
            title: 'Genera reportes PDF',
            text: 'Genera hojas de vida, reportes de vencimientos y mas. ' +
                  'Tus clientes recibiran documentos profesionales.',
            attachTo: { element: 'a[href*="informes"]', on: 'right' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                {
                    text: 'Finalizar',
                    action: tour.complete,
                    classes: 'shepherd-button-primary'
                }
            ]
        });
    } else {
        // Si no hay link de informes, agregar boton finalizar al ultimo paso existente
        var steps = tour.steps;
        if (steps.length > 0) {
            var lastStep = steps[steps.length - 1];
            lastStep.options.buttons = [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Finalizar', action: tour.complete, classes: 'shepherd-button-primary' }
            ];
        }
    }

    // Al completar el tour, marcar como completado via POST
    tour.on('complete', function() {
        fetch('/onboarding/completar-tour/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')
                    ? document.querySelector('[name=csrfmiddlewaretoken]').value
                    : document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });
    });

    tour.start();
}

// Auto-iniciar tour si no se ha completado
document.addEventListener('DOMContentLoaded', function() {
    if (typeof samOnboardingTourCompletado !== 'undefined' && samOnboardingTourCompletado === false) {
        // Esperar un momento para que el dashboard cargue completamente
        setTimeout(function() {
            iniciarTourOnboarding();
        }, 800);
    }
});
