document.addEventListener('DOMContentLoaded', () => {
    const grdSelect = document.getElementById('grd-select');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const searchButton = document.getElementById('search-button');
    const chartCanvas = document.getElementById('historicalChart');
    const historicalTableContainer = document.getElementById('historical-table-container');

    let historicalChart = null; // Variable para la instancia del gráfico

    // 1. Obtener el parámetro 'grd_id' de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const grdIdFromUrl = urlParams.get('grd_id');

    async function fetchGrdList() {
        try {
            const response = await fetch('/api/grd_data');
            const data = await response.json();
            const uniqueGrdIds = new Set(data.map(grd => grd.grd_id));
            grdSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
            uniqueGrdIds.forEach(id => {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = `GRD ID: ${id}`;
                grdSelect.appendChild(option);
            });
            
            // 2. Si hay un ID en la URL, seleccionarlo y buscar los datos
            if (grdIdFromUrl) {
                grdSelect.value = grdIdFromUrl;
                // Configurar un rango de fechas por defecto (hoy)
                const today = new Date().toISOString().split('T')[0];
                startDateInput.value = today;
                endDateInput.value = today;
                fetchHistoricalData();
            }
        } catch (error) {
            console.error('Error al cargar la lista de GRDs:', error);
        }
    }

    async function fetchHistoricalData() {
        const grdId = grdSelect.value;
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;

        if (!grdId || !startDate || !endDate) {
            alert('Por favor, selecciona un GRD y un rango de fechas.');
            return;
        }

        historicalTableContainer.innerHTML = '<p>Cargando datos...</p>';

        try {
            const response = await fetch(`/api/historial?grd_id=${grdId}&start_date=${startDate}&end_date=${endDate}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.length === 0) {
                historicalTableContainer.innerHTML = '<p>No se encontraron datos para la selección.</p>';
                if (historicalChart) historicalChart.destroy();
                return;
            }
            
            // Calcular y mostrar estadísticas de bombas
            const stats = calculateBombaStats(data);
            const statsHTML = renderBombaStats(stats);

            renderHistoricalChart(data);
            renderHistoricalTable(data);

            // Insertar estadísticas antes de la tabla
            const tableContainer = document.getElementById('historical-table-container');
            tableContainer.insertAdjacentHTML('beforebegin', statsHTML);
            
        } catch (error) {
            console.error('Error al cargar el historial:', error);
            historicalTableContainer.innerHTML = `<p class="error">Error al cargar el historial. Revisa la consola del navegador para más detalles.</p>`;
            if (historicalChart) historicalChart.destroy();
        }
    }

    function renderHistoricalChart(data) {
        const labels = data.map(item => item.timestamp);
        const nivelMetros = data.map(item => item.nivel_agua.metros);
        const presionBar = data.map(item => item.presion);
        const bomba1 = data.map(item => item.estado_bomba_1 === 'Encendida' ? 1 : 0);
        const bomba2 = data.map(item => item.estado_bomba_2 === 'Encendida' ? 1 : 0);
        
        if (historicalChart) {
            historicalChart.destroy();
        }
        
        const ctx = chartCanvas.getContext('2d');
        historicalChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Nivel de Agua (m)',
                        data: nivelMetros,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgb(75, 192, 192)',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Presión (bar)',
                        data: presionBar,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgb(255, 99, 132)',
                        borderWidth: 1,
                        yAxisID: 'y2'
                    },
                    {
                        label: 'Bomba 1',
                        data: bomba1,
                        type: 'line',
                        borderColor: 'rgb(54, 162, 235)',
                        borderWidth: 2,
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgb(54, 162, 235)',
                        yAxisID: 'y3'
                    },
                     {
                        label: 'Bomba 2',
                        data: bomba2,
                        type: 'line',
                        borderColor: 'rgb(255, 159, 64)',
                        borderWidth: 2,
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgb(255, 159, 64)',
                        yAxisID: 'y3'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                stacked: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Fecha y Hora'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Nivel (m)'
                        },
                        ticks: {
                            color: 'rgb(75, 192, 192)'
                        }
                    },
                    y2: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Presión (bar)'
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: 'rgb(255, 99, 132)'
                        }
                    },
                    y3: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Bombas (1=On)'
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        min: 0,
                        max: 1.2,
                        ticks: {
                            stepSize: 1,
                            beginAtZero: true,
                            callback: function(value, index, ticks) {
                                return value === 1 ? 'Encendida' : 'Apagada';
                            }
                        }
                    }
                }
            }
        });
    }

    function calculateBombaStats(data) {
        if (!data || data.length === 0) return null;

        const stats = {
            bomba1: { encendida: 0, apagada: 0, cambios: 0 },
            bomba2: { encendida: 0, apagada: 0, cambios: 0 }
        };

        let previousBomba1 = null;
        let previousBomba2 = null;

        data.forEach(item => {
            const b1 = item.estado_bomba_1;
            const b2 = item.estado_bomba_2;

            // Contar tiempo encendido/apagado (simplificado)
            if (b1 === 'Encendida') stats.bomba1.encendida++;
            else if (b1 === 'Apagada') stats.bomba1.apagada++;

            if (b2 === 'Encendida') stats.bomba2.encendida++;
            else if (b2 === 'Apagada') stats.bomba2.apagada++;

            // Contar cambios
            if (previousBomba1 !== null && previousBomba1 !== b1) stats.bomba1.cambios++;
            if (previousBomba2 !== null && previousBomba2 !== b2) stats.bomba2.cambios++;

            previousBomba1 = b1;
            previousBomba2 = b2;
        });

        return stats;
    }

    function renderBombaStats(stats) {
        if (!stats) return '';

        const totalRecords = stats.bomba1.encendida + stats.bomba1.apagada;
        const bomba1Uptime = totalRecords > 0 ? (stats.bomba1.encendida / totalRecords * 100).toFixed(1) : 0;
        const bomba2Uptime = totalRecords > 0 ? (stats.bomba2.encendida / totalRecords * 100).toFixed(1) : 0;

        return `
            <div class="bomba-stats" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">
                <h3>Estadísticas de Bombas</h3>
                <div style="display: flex; gap: 20px;">
                    <div>
                        <h4>Bomba 1</h4>
                        <p>Tiempo encendida: ${bomba1Uptime}%</p>
                        <p>Cambios de estado: ${stats.bomba1.cambios}</p>
                    </div>
                    <div>
                        <h4>Bomba 2</h4>
                        <p>Tiempo encendida: ${bomba2Uptime}%</p>
                        <p>Cambios de estado: ${stats.bomba2.cambios}</p>
                    </div>
                </div>
            </div>
        `;
    }

    function renderHistoricalTable(data) {
        let tableHTML = `
            <table class="historical-table">
                <thead>
                    <tr>
                        <th>Fecha y Hora</th>
                        <th>Nivel de Agua (m)</th>
                        <th>Nivel de Agua (%)</th>
                        <th>Presión (bar)</th>
                        <th>Bomba 1</th>
                        <th>Bomba 2</th>
                        <th>Eventos</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Crear un mapa de eventos por timestamp para acceso rápido
        const eventsMap = {};
        data.forEach(item => {
            if (item.eventos && item.eventos.length > 0) {
                eventsMap[item.timestamp] = item.eventos;
            }
        });

        data.forEach(item => {
            const eventos = eventsMap[item.timestamp] || [];
            const eventosText = eventos.map(e =>
                `${e.bomba}: ${e.estado_anterior} → ${e.estado_nuevo}`
            ).join('; ');

            const hasEvents = eventos.length > 0;
            const rowClass = hasEvents ? 'event-row' : '';

            tableHTML += `
                <tr class="${rowClass}">
                    <td>${item.timestamp}</td>
                    <td>${item.nivel_agua.metros !== undefined ? item.nivel_agua.metros.toFixed(2) : '--'}</td>
                    <td>${item.nivel_agua.porcentaje !== undefined ? item.nivel_agua.porcentaje.toFixed(2) : '--'}</td>
                    <td>${item.presion !== undefined ? item.presion.toFixed(2) : '--'}</td>
                    <td class="bomba-status ${item.estado_bomba_1.toLowerCase()}">${item.estado_bomba_1 || '--'}</td>
                    <td class="bomba-status ${item.estado_bomba_2.toLowerCase()}">${item.estado_bomba_2 || '--'}</td>
                    <td class="eventos-cell">${eventosText || '-'}</td>
                </tr>
            `;
        });
        tableHTML += `</tbody></table>`;

        // Agregar estilos CSS para los eventos
        const style = document.createElement('style');
        style.textContent = `
            .event-row {
                background-color: #fff3cd !important;
                border-left: 4px solid #ffc107;
            }
            .bomba-status.encendida {
                color: #28a745;
                font-weight: bold;
            }
            .bomba-status.apagada {
                color: #dc3545;
                font-weight: bold;
            }
            .eventos-cell {
                font-size: 0.9em;
                color: #856404;
            }
        `;
        document.head.appendChild(style);

        historicalTableContainer.innerHTML = tableHTML;
    }

    searchButton.addEventListener('click', fetchHistoricalData);

    fetchGrdList();
});