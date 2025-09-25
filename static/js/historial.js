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
            
            renderHistoricalChart(data);
            renderHistoricalTable(data);
            
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
                    </tr>
                </thead>
                <tbody>
        `;
        data.forEach(item => {
            tableHTML += `
                <tr>
                    <td>${item.timestamp}</td>
                    <td>${item.nivel_agua.metros !== undefined ? item.nivel_agua.metros.toFixed(2) : '--'}</td>
                    <td>${item.nivel_agua.porcentaje !== undefined ? item.nivel_agua.porcentaje.toFixed(2) : '--'}</td>
                    <td>${item.presion !== undefined ? item.presion.toFixed(2) : '--'}</td>
                    <td>${item.estado_bomba_1 || '--'}</td>
                    <td>${item.estado_bomba_2 || '--'}</td>
                </tr>
            `;
        });
        tableHTML += `</tbody></table>`;
        historicalTableContainer.innerHTML = tableHTML;
    }

    searchButton.addEventListener('click', fetchHistoricalData);

    fetchGrdList();
});