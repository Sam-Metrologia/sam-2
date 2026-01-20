/**
 * SAM METROLOGÍA - CONFIGURACIÓN DE GRÁFICOS
 * Adapta Chart.js al tema oscuro/claro
 */

(function() {
    'use strict';

    /**
     * Obtiene los colores según el tema actual
     */
    function getChartColors() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const isDark = currentTheme === 'dark';

        if (isDark) {
            return {
                text: '#e6edf3',
                grid: '#374151',
                border: '#4b5563',
                tooltipBackground: '#1f2937',
                tooltipBorder: '#4b5563'
            };
        } else {
            return {
                text: '#1f2937',
                grid: '#e5e7eb',
                border: '#d1d5db',
                tooltipBackground: '#ffffff',
                tooltipBorder: '#d1d5db'
            };
        }
    }

    /**
     * Configuración por defecto para Chart.js
     */
    function getChartDefaults() {
        const colors = getChartColors();

        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: colors.text,
                        font: {
                            family: "'Inter', sans-serif",
                            size: 12
                        },
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBackground,
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('es-CO', {
                                    style: 'currency',
                                    currency: 'COP',
                                    maximumFractionDigits: 0
                                }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: colors.text,
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    }
                },
                y: {
                    ticks: {
                        color: colors.text,
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    }
                }
            }
        };
    }

    /**
     * Actualiza todos los gráficos existentes
     */
    function updateAllCharts() {
        if (typeof Chart === 'undefined') return;

        // Actualizar instancias existentes
        Chart.helpers.each(Chart.instances, function(chart) {
            const colors = getChartColors();

            // Actualizar colores de leyenda
            if (chart.options.plugins && chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = colors.text;
            }

            // Actualizar colores de tooltips
            if (chart.options.plugins && chart.options.plugins.tooltip) {
                chart.options.plugins.tooltip.backgroundColor = colors.tooltipBackground;
                chart.options.plugins.tooltip.titleColor = colors.text;
                chart.options.plugins.tooltip.bodyColor = colors.text;
                chart.options.plugins.tooltip.borderColor = colors.tooltipBorder;
            }

            // Actualizar colores de ejes
            if (chart.options.scales) {
                if (chart.options.scales.x) {
                    chart.options.scales.x.ticks.color = colors.text;
                    chart.options.scales.x.grid.color = colors.grid;
                }
                if (chart.options.scales.y) {
                    chart.options.scales.y.ticks.color = colors.text;
                    chart.options.scales.y.grid.color = colors.grid;
                }
            }

            // Forzar re-render completo
            chart.update('active');
        });
    }

    /**
     * Configurar Chart.js al cargar la página
     */
    function initChartTheme() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js no está cargado');
            return;
        }

        // Aplicar configuración por defecto
        const defaults = getChartDefaults();

        Chart.defaults.color = getChartColors().text;
        Chart.defaults.borderColor = getChartColors().border;

        // Escuchar cambios de tema
        document.addEventListener('themeChanged', function(e) {
            updateAllCharts();
        });
    }

    // Inicializar cuando Chart.js esté disponible
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initChartTheme, 100);
        });
    } else {
        setTimeout(initChartTheme, 100);
    }

    // Exportar configuración para uso global
    window.SAMChartConfig = {
        getDefaults: getChartDefaults,
        getColors: getChartColors,
        update: updateAllCharts
    };

})();