document.addEventListener('DOMContentLoaded', async () => {
    const urlParts = window.location.pathname.split('/');
    const currentGrdId = parseInt(urlParts[urlParts.length - 1], 10);
    let allGrdIds = [];

    const tankNameElement = document.getElementById('tank-name');
    const nivelMetrosElement = document.getElementById('nivel-metros-big');
    const nivelPorcentajeElement = document.getElementById('nivel-porcentaje-big');
    const presionElement = document.getElementById('presion-big');
    const bomba1Element = document.getElementById('bomba-1-big');
    const bomba2Element = document.getElementById('bomba-2-big');
    const waterLevelDiv = document.getElementById('water-level-big');
    const waterLabelDiv = document.getElementById('water-label-big');

    const prevButton = document.getElementById('prev-grd');
    const nextButton = document.getElementById('next-grd');

    // Mapeo de IDs de GRD a nombres
    const GRD_NAMES = {
        720: 'Cisterna LG',
        787: 'Planta LG'
    };

    // 1. Obtener la lista de todos los GRDs para la navegación
    try {
        const response = await fetch('/api/grd_data');
        if (!response.ok) {
            throw new Error('Failed to fetch GRD list.');
        }
        const data = await response.json();
        allGrdIds = data.map(grd => grd.grd_id).sort((a, b) => a - b);
        updateNavigationButtons(currentGrdId);
    } catch (error) {
        console.error('Error fetching GRD list:', error);
    }

    // 2. Función para obtener y mostrar los datos del GRD actual
    async function fetchGrdData(grdId) {
        try {
            const response = await fetch(`/api/tank_data/${grdId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch tank data.');
            }
            const data = await response.json();
            updateUI(data);
            document.title = GRD_NAMES[grdId] || `GRD ${grdId}`;
        } catch (error) {
            console.error('Error fetching tank data:', error);
            tankNameElement.textContent = `GRD ${grdId} no encontrado`;
            resetUI();
        }
    }

    // 3. Función para actualizar la interfaz con los datos
    function updateUI(grd) {
        const grdName = GRD_NAMES[grd.grd_id] || `GRD ${grd.grd_id}`;
        tankNameElement.textContent = grdName;

        const nivelMetros = grd.nivel_agua ? grd.nivel_agua.metros.toFixed(2) : '--';
        const nivelPorcentaje = grd.nivel_agua ? grd.nivel_agua.porcentaje.toFixed(2) : '--';
        const presionBar = grd.presion ? grd.presion.toFixed(2) : '--';

        nivelMetrosElement.textContent = `${nivelMetros} m`;
        nivelPorcentajeElement.textContent = `${nivelPorcentaje}%`;
        presionElement.textContent = `${presionBar} bar`;
        bomba1Element.textContent = grd.estado_bomba_1;
        bomba2Element.textContent = grd.estado_bomba_2;

        waterLevelDiv.style.height = `${nivelPorcentaje}%`;
        waterLabelDiv.textContent = `${nivelPorcentaje}%`;

        // Actualizar clases para colores
        waterLevelDiv.className = 'water-level-big';
        if (grd.nivel_agua.alerta_visual === 'alerta') {
            waterLevelDiv.classList.add('alerta');
        } else if (grd.nivel_agua.alerta_visual === 'lleno') {
            waterLevelDiv.classList.add('lleno');
        }

        bomba1Element.className = `status-${grd.estado_bomba_1.toLowerCase()}`;
        bomba2Element.className = `status-${grd.estado_bomba_2.toLowerCase()}`;
    }

    function resetUI() {
        nivelMetrosElement.textContent = '-- m';
        nivelPorcentajeElement.textContent = '--%';
        presionElement.textContent = '-- bar';
        bomba1Element.textContent = '--';
        bomba2Element.textContent = '--';
        waterLevelDiv.style.height = '0%';
        waterLabelDiv.textContent = '--%';
        waterLevelDiv.className = 'water-level-big';
    }

    // 4. Lógica de navegación
    function updateNavigationButtons(currentId) {
        const currentIndex = allGrdIds.indexOf(currentId);
        prevButton.disabled = currentIndex <= 0;
        nextButton.disabled = currentIndex >= allGrdIds.length - 1;

        if (currentIndex > 0) {
            prevButton.onclick = () => window.location.href = `/tank/${allGrdIds[currentIndex - 1]}`;
        }
        if (currentIndex < allGrdIds.length - 1) {
            nextButton.onclick = () => window.location.href = `/tank/${allGrdIds[currentIndex + 1]}`;
        }
    }

    // Inicializar la página con los datos del GRD
    if (currentGrdId) {
        fetchGrdData(currentGrdId);
    }

    // Actualizar los datos cada 30 segundos
    setInterval(() => {
        if (currentGrdId) {
            fetchGrdData(currentGrdId);
        }
    }, 30000);
});