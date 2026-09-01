// Mapa de cambios detectados, sobre OpenStreetMap.
//
// Pinta dos cosas distintas y las mantiene distinguibles: lo que sugiere
// la IA (círculos, por estado de revisión) y lo que reporta una persona
// sobre el terreno (cuadrados, por categoría).

import { listarSugerencias } from "../api.js";
import {
  capaDe,
  controlDeCapas,
  crearCapas,
  iconoDe,
  limpiarCapas,
} from "./capasEstado.js";

const ETIQUETAS_DANO = {
  "minor-damage": "Daño menor",
  "major-damage": "Daño mayor",
  destroyed: "Destruido",
  "un-classified": "Sin clasificar",
  "no-damage": "Sin daño",
};

const ETIQUETAS_CATEGORIA = {
  dano: "Daño",
  recurso: "Recurso disponible",
  acceso: "Acceso bloqueado",
};

export class MapaCambios {
  constructor(idContenedor, { onClicUbicacion } = {}) {
    this.mapa = L.map(idContenedor).setView([0, 0], 2);

    // Teselas de OpenStreetMap. La atribución es obligatoria por la
    // licencia de OSM: no quitarla.
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.mapa);

    this.capas = crearCapas(this.mapa);
    controlDeCapas(this.mapa, this.capas);
    this.marcadores = new Map();

    // Modo "marcar ubicación": solo escucha clics cuando alguien está
    // creando un reporte, para no molestar durante el uso normal.
    this.esperandoUbicacion = false;
    this.marcadorProvisional = null;
    this.onClicUbicacion = onClicUbicacion;

    this.mapa.on("click", (evento) => this.alHacerClic(evento));
  }

  alHacerClic(evento) {
    if (!this.esperandoUbicacion) return;

    const { lat, lng } = evento.latlng;

    if (this.marcadorProvisional) {
      this.marcadorProvisional.setLatLng(evento.latlng);
    } else {
      this.marcadorProvisional = L.marker(evento.latlng, {
        icon: L.divIcon({
          className: "",
          html: '<div class="marcador-provisional"></div>',
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        }),
      }).addTo(this.mapa);
    }

    this.onClicUbicacion?.(lat, lng);
  }

  pedirUbicacion() {
    this.esperandoUbicacion = true;
    this.mapa.getContainer().style.cursor = "crosshair";
  }

  dejarDePedirUbicacion() {
    this.esperandoUbicacion = false;
    this.mapa.getContainer().style.cursor = "";
    if (this.marcadorProvisional) {
      this.mapa.removeLayer(this.marcadorProvisional);
      this.marcadorProvisional = null;
    }
  }

  async cargar(escena) {
    const puntos = await listarSugerencias({ escena });
    limpiarCapas(this.capas);
    this.marcadores.clear();

    if (!puntos.length) return;

    puntos.forEach((punto) => this.pintar(punto));

    const coordenadas = puntos.map((p) => [p.latitud, p.longitud]);
    this.mapa.fitBounds(L.latLngBounds(coordenadas), { padding: [40, 40] });
  }

  pintar(punto) {
    const marcador = L.marker([punto.latitud, punto.longitud], {
      icon: iconoDe(punto),
    });

    marcador.bindPopup(
      punto.origen === "persona"
        ? this.popupDeReporte(punto)
        : this.popupDeSugerencia(punto),
    );

    marcador.addTo(this.capas[capaDe(punto)]);
    this.marcadores.set(punto.id, marcador);
  }

  popupDeSugerencia(punto) {
    const porcentaje = Math.round(punto.confianza * 100);
    const aviso =
      punto.estado === "pendiente"
        ? '<br><em style="color:#BA7517">Sin confirmar por una persona</em>'
        : "";

    return `
      <strong>${punto.dano_etiqueta || ETIQUETAS_DANO[punto.dano] || punto.dano}</strong>
      <br><small>Detectado por la IA</small>
      <br>Confianza: ${porcentaje}%
      <br>Estado: ${punto.estado}${aviso}
    `;
  }

  popupDeReporte(punto) {
    const categoria = ETIQUETAS_CATEGORIA[punto.categoria] || punto.categoria;
    const nivel =
      punto.categoria === "dano"
        ? `<br>${punto.dano_etiqueta || ETIQUETAS_DANO[punto.dano] || ""}`
        : "";

    return `
      <strong>${categoria}</strong>
      <br><small>Reportado por una persona</small>${nivel}
      <br>${punto.descripcion || ""}
      <br><em>— ${punto.reportado_por || "anónimo"}</em>
    `;
  }

  /** Centra el mapa en un punto concreto (al pulsar su tarjeta). */
  centrarEn(punto) {
    const marcador = this.marcadores.get(punto.id);
    if (!marcador) return;
    this.mapa.setView([punto.latitud, punto.longitud], 18);
    marcador.openPopup();
  }
}
