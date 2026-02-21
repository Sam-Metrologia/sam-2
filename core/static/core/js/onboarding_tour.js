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

    // Paso 1: Bienvenida (centrado, sin anchor)
    tour.addStep({
        id: 'bienvenida',
        title: 'Bienvenido a SAM Metrologia',
        text: 'Este tour te guiara por las funciones principales del sistema. ' +
              'SAM te ayuda a gestionar equipos, calibraciones y generar reportes ' +
              'cumpliendo con la norma ISO/IEC 17020:2012.',
        buttons: [
            { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
        ]
    });

    // Paso 2: Estadisticas (cards de equipos) - usa ID estable
    var statsGrid = document.getElementById('stats-grid');
    if (statsGrid) {
        tour.addStep({
            id: 'estadisticas',
            title: 'Resumen de tus equipos',
            text: 'Aqui veras el resumen de tus equipos: totales, activos, ' +
                  'calibraciones vencidas y proximas actividades.',
            attachTo: { element: '#stats-grid', on: 'bottom' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Paso 3: Equipos - buscar por icono fa-boxes en el sidebar
    var iconEquipos = document.querySelector('.fa-boxes');
    var linkEquipos = iconEquipos ? iconEquipos.closest('a') : null;
    if (linkEquipos) {
        tour.addStep({
            id: 'crear-equipo',
            title: 'Empieza creando un equipo',
            text: 'El primer paso es registrar tus equipos de medicion. ' +
                  'Desde aqui puedes acceder al listado y agregar nuevos equipos.',
            attachTo: { element: linkEquipos, on: 'right' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Siguiente', action: tour.next, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Paso 4: Graficos de calibraciones
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

    // Paso 5: Informes - buscar link con texto "Informes" en sidebar
    var linkInformes = null;
    var allLinks = document.querySelectorAll('a');
    for (var i = 0; i < allLinks.length; i++) {
        if (allLinks[i].textContent.trim().indexOf('Informes') !== -1 &&
            allLinks[i].querySelector('.fa-chart-line')) {
            linkInformes = allLinks[i];
            break;
        }
    }
    if (linkInformes) {
        tour.addStep({
            id: 'reportes',
            title: 'Genera reportes PDF',
            text: 'Genera hojas de vida, reportes de vencimientos y mas. ' +
                  'Tus clientes recibiran documentos profesionales.',
            attachTo: { element: linkInformes, on: 'right' },
            buttons: [
                { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                { text: 'Finalizar', action: tour.complete, classes: 'shepherd-button-primary' }
            ]
        });
    }

    // Si el ultimo paso no tiene boton Finalizar, agregarlo
    var steps = tour.steps;
    if (steps.length > 1) {
        var lastStep = steps[steps.length - 1];
        var lastButtons = lastStep.options.buttons;
        var hasFinalizar = false;
        for (var j = 0; j < lastButtons.length; j++) {
            if (lastButtons[j].text === 'Finalizar') { hasFinalizar = true; break; }
        }
        if (!hasFinalizar) {
            lastStep.updateStepOptions({
                buttons: [
                    { text: 'Anterior', action: tour.back, classes: 'shepherd-button-secondary' },
                    { text: 'Finalizar', action: tour.complete, classes: 'shepherd-button-primary' }
                ]
            });
        }
    }

    // Al completar o cancelar el tour, marcar como completado via POST
    function marcarTourCompletado() {
        var csrfToken = '';
        var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            csrfToken = csrfInput.value;
        } else {
            var match = document.cookie.match(/csrftoken=([^;]+)/);
            if (match) csrfToken = match[1];
        }
        fetch('/onboarding/completar-tour/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });
    }

    tour.on('complete', marcarTourCompletado);
    tour.on('cancel', marcarTourCompletado);

    tour.start();
}

// Auto-iniciar tour si no se ha completado
document.addEventListener('DOMContentLoaded', function() {
    if (typeof samOnboardingTourCompletado !== 'undefined' && samOnboardingTourCompletado === false) {
        setTimeout(function() {
            iniciarTourOnboarding();
        }, 800);
    }
});
