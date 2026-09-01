// Capas del mapa.
//
// Se separan por origen antes que por estado: lo primero que hay que
// poder distinguir de un vistazo es qué lo dijo una máquina y qué lo
// puso una persona que estaba allí.

export const CAPAS = [
  "pendiente",
  "confirmada",
  "rechazada",
  "corregida",
  "reporte-local",
];

export const NOMBRES_CAPA = {
  pendiente: "IA · pendientes de revisar",
  confirmada: "IA · confirmadas",
  rechazada: "IA · rechazadas",
  corregida: "IA · corregidas",
  "reporte-local": "Reportes de personas",
};

/** Los reportes de personas van a su propia capa, no a la de su estado. */
export function capaDe(punto) {
  return punto.origen === "persona" ? "reporte-local" : punto.estado;
}

export function crearCapas(mapa) {
  const capas = {};
  CAPAS.forEach((clave) => {
    capas[clave] = L.layerGroup().addTo(mapa);
  });
  return capas;
}

export function limpiarCapas(capas) {
  Object.values(capas).forEach((capa) => capa.clearLayers());
}

export function iconoDe(punto) {
  const clave = capaDe(punto);

  // Los reportes locales usan un marcador distinto (cuadrado con borde
  // grueso) además de otro color: el color solo no basta para quien no
  // distingue bien los colores.
  if (clave === "reporte-local") {
    return L.divIcon({
      className: "",
      html: `<div class="marcador marcador--reporte marcador--${punto.categoria}"></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
  }

  return L.divIcon({
    className: "",
    html: `<div class="marcador marcador--${clave}"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export function controlDeCapas(mapa, capas) {
  const etiquetadas = {};
  CAPAS.forEach((clave) => {
    etiquetadas[NOMBRES_CAPA[clave]] = capas[clave];
  });
  return L.control.layers(null, etiquetadas, { collapsed: false }).addTo(mapa);
}
