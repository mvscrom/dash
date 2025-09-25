// Coordenadas exactas y nombres para los GRDs
const GRD_LOCATIONS = {
    720: { name: 'Cisterna LG', lat: -40.796944, lon: -65.075556, type: 'cisterna' }, 
    787: { name: 'Planta LG', lat: -40.801944, lon: -65.075833, type: 'planta' }     
};

const zoneSelect = document.getElementById('zone-select');
const grdSelect = document.getElementById('grd-select');
const infoPanel = document.getElementById('info-panel');
const closePanelBtn = document.getElementById('close-panel-btn');
const panelTitle = document.getElementById('panel-title');
const panelContent = document.getElementById('panel-content');

let allGrdData = [];
let map;
const markers = {};

// Definir las zonas y los GRDs que pertenecen a cada una
const zones = {
    'Las Grutas': [720, 787],
    // Puedes agregar más zonas aquí en el futuro
};

// --- INICIO DE CAMBIOS PARA ÍCONOS PERSONALIZADOS MÁS GRANDES Y DIFERENTES ---

// Función para obtener la URL del ícono según el tipo y el estado
function getIconUrl(grd_type, alerta_visual) {
    let baseIconUrl = '/static/img/';
    
    // Asignar el ícono base según el tipo de GRD
    if (grd_type === 'cisterna') {
        baseIconUrl += 'tanque.png'; 
    } else if (grd_type === 'planta') {
        baseIconUrl += 'tanque.png';
    } else {
        // En caso de que no se defina el tipo, usamos un marcador por defecto
        baseIconUrl = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png';
    }
    
    // (Opcional) Puedes agregar lógica para iconos de diferentes colores aquí
    // if (alerta_visual === 'alerta') {
    //     return baseIconUrl.replace('.png', '_alerta.png');
    // }
    
    return baseIconUrl;
}

// Función para crear un ícono personalizado de Leaflet
function getCustomMarkerIcon(grd_type, alerta_visual) {
    const iconUrl = getIconUrl(grd_type, alerta_visual);
    const iconSize = [48, 48]; // Tamaño del ícono, más grande como solicitaste
    const iconAnchor = [24, 48]; // El punto del ícono que corresponde a la ubicación del marcador
    
    return L.icon({
        iconUrl: iconUrl,
        iconSize: iconSize,
        iconAnchor: iconAnchor,
        popupAnchor: [0, -48], 
        tooltipAnchor: [15, -20]
    });
}
// --- FIN DE CAMBIOS PARA ÍCONOS PERSONALIZADOS MÁS GRANDES Y DIFERENTES ---


document.addEventListener('DOMContentLoaded', async () => {
    // 1. Inicializar el mapa
    map = L.map('map').setView([-40.799, -65.0757], 14); // Centrado en la zona de LG

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 2. Llenar los menús de filtrado
    populateZones();

    // 3. Obtener datos iniciales y crear/actualizar marcadores
    await updateMapData();

    // 4. Configurar eventos de filtrado
    zoneSelect.addEventListener('change', handleFilterChange);
    grdSelect.addEventListener('change', handleFilterChange);
    closePanelBtn.addEventListener('click', () => infoPanel.classList.add('hidden'));

    // 5. Refrescar los datos cada 30 segundos
    setInterval(updateMapData, 30000);
});

async function fetchData() {
    try {
        const response = await fetch('/api/grd_data');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        return [];
    }
}

function populateZones() {
    zoneSelect.innerHTML = '<option value="all">Todas</option>';
    Object.keys(zones).forEach(zone => {
        const option = document.createElement('option');
        option.value = zone;
        option.textContent = zone;
        zoneSelect.appendChild(option);
    });
}

function populateGrdSelect(grdIds) {
    grdSelect.innerHTML = '<option value="all">Todos</option>';
    grdIds.forEach(id => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = `${GRD_LOCATIONS[id].name}`;
        grdSelect.appendChild(option);
    });
    grdSelect.style.display = 'inline-block';
    document.querySelector('label[for="grd-select"]').style.display = 'inline-block';
}

async function updateMapData() {
    allGrdData = await fetchData();
    const activeGrdIds = new Set(allGrdData.map(grd => grd.grd_id));

    // Eliminar marcadores que ya no están activos
    Object.keys(markers).forEach(id => {
        if (!activeGrdIds.has(Number(id))) {
            map.removeLayer(markers[id]);
            delete markers[id];
        }
    });

    // Crear/Actualizar marcadores con los datos actuales
    allGrdData.forEach(grd => {
        if (GRD_LOCATIONS[grd.grd_id]) {
            const { name, lat, lon, type } = GRD_LOCATIONS[grd.grd_id]; // Obtener el tipo
            const markerLatLon = [lat, lon];
            
            // --- INICIO DE CAMBIOS: Usar íconos personalizados ---
            const customIcon = getCustomMarkerIcon(type, grd.nivel_agua?.alerta_visual);
            // --- FIN DE CAMBIOS ---
            
            if (markers[grd.grd_id]) {
                // Actualizar el ícono y el tooltip si ya existe
                markers[grd.grd_id].setIcon(customIcon);
                markers[grd.grd_id].bindTooltip(name, {permanent: true, direction: "top"}).openTooltip();
            } else {
                // Crear un nuevo marcador si no existe
                const marker = L.marker(markerLatLon, { icon: customIcon }).addTo(map);
                marker.grd_id = grd.grd_id; // Guardar el ID en el marcador
                marker.on('click', () => showInfoPanel(grd));
                marker.bindTooltip(name, {permanent: true, direction: "top"}).openTooltip();
                markers[grd.grd_id] = marker;
            }
        }
    });
    
    // Si el panel de información está abierto, actualizar sus datos
    if (!infoPanel.classList.contains('hidden')) {
        const currentGrdId = infoPanel.dataset.grdId;
        const currentGrdData = allGrdData.find(grd => String(grd.grd_id) === currentGrdId);
        if (currentGrdData) {
            showInfoPanel(currentGrdData);
        }
    }
    
    // Aplicar el filtro actual después de actualizar los datos
    handleFilterChange();
}

function showInfoPanel(grd) {
    const grdName = GRD_LOCATIONS[grd.grd_id]?.name || `GRD ID ${grd.grd_id}`;
    
    panelTitle.textContent = grdName;
    panelContent.innerHTML = `
        <p><strong>Nivel de Agua:</strong> ${grd.nivel_agua?.metros?.toFixed(2) || '--'} m</p>
        <p><strong>Porcentaje:</strong> ${grd.nivel_agua?.porcentaje?.toFixed(2) || '--'}%</p>
        <p><strong>Presión:</strong> ${grd.presion?.toFixed(2) || '--'} bar</p>
        <p><strong>Estado:</strong> <span class="status-${grd.nivel_agua.alerta_visual}">${grd.nivel_agua.estado}</span></p>
        <p><strong>Bomba 1:</strong> <span class="status-${grd.estado_bomba_1.toLowerCase()}">${grd.estado_bomba_1}</span></p>
        <p><strong>Bomba 2:</strong> <span class="status-${grd.estado_bomba_2.toLowerCase()}">${grd.estado_bomba_2}</span></p>
        <a href="/historial?grd_id=${grd.grd_id}" class="view-details-btn">Ver Historial</a>
    `;
    infoPanel.dataset.grdId = grd.grd_id;
    infoPanel.classList.remove('hidden');
}

function handleFilterChange() {
    const selectedZone = zoneSelect.value;
    const selectedGrdId = grdSelect.value;
    
    infoPanel.classList.add('hidden'); // Oculta el panel al cambiar el filtro
    
    // Ocultar todos los marcadores
    Object.values(markers).forEach(marker => map.removeLayer(marker));
    
    if (selectedZone === 'all') {
        // Mostrar todos los marcadores y ocultar el menú de GRD
        Object.values(markers).forEach(marker => marker.addTo(map));
        grdSelect.style.display = 'none';
        document.querySelector('label[for="grd-select"]').style.display = 'none';
        map.setView([-40.799, -65.0757], 14); // Volver a la vista general
        
    } else {
        // Mostrar el menú de GRD
        populateGrdSelect(zones[selectedZone]);

        if (selectedGrdId === 'all') {
            // Mostrar todos los marcadores de la zona seleccionada
            const grdIdsInZone = zones[selectedZone];
            grdIdsInZone.forEach(id => {
                if (markers[id]) {
                    markers[id].addTo(map);
                }
            });
            // Ajustar el mapa a la zona seleccionada
            const bounds = L.latLngBounds(grdIdsInZone.map(id => [GRD_LOCATIONS[id].lat, GRD_LOCATIONS[id].lon]));
            map.fitBounds(bounds, { padding: [50, 50] });
            
        } else {
            // Mostrar solo el marcador del GRD seleccionado
            const selectedGrd = markers[selectedGrdId];
            if (selectedGrd) {
                selectedGrd.addTo(map);
                map.setView(selectedGrd.getLatLng(), 16); // Centrar el mapa en el GRD
            }
        }
    }
}