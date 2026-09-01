// Arranque de la aplicación: conecta el mapa, la cola de validación y el
// formulario de reportes locales.

import { analizarEscena, contarPorOrigen, listarEscenas } from "./api.js";
import { MapaCambios } from "./mapa/mapaCambios.js";
import { FormularioReporte } from "./reportes/formularioReporte.js";
import { ColaValidacion } from "./validacion/colaValidacion.js";

const selector = document.getElementById("selector-escena");
const botonAnalizar = document.getElementById("btn-analizar");
const listaTarjetas = document.getElementById("lista-tarjetas");
const resumen = document.getElementById("resumen");
const origen = document.getElementById("origen");

const mapa = new MapaCambios("map", {
  onClicUbicacion: (lat, lng) => formulario.setUbicacion(lat, lng),
});

const cola = new ColaValidacion(listaTarjetas, resumen, {
  // Al validar algo, el punto cambia de capa en el mapa.
  onCambio: () => refrescar(),
  onSeleccionar: (punto) => mapa.centrarEn(punto),
});

const formulario = new FormularioReporte(
  {
    form: document.getElementById("form-reporte"),
    boton: document.getElementById("btn-reportar"),
    categoria: document.getElementById("reporte-categoria"),
    grupoDano: document.getElementById("grupo-dano"),
    dano: document.getElementById("reporte-dano"),
    descripcion: document.getElementById("reporte-descripcion"),
    autor: document.getElementById("reporte-autor"),
    aviso: document.getElementById("reporte-aviso"),
  },
  {
    onPedirUbicacion: () => mapa.pedirUbicacion(),
    onCreado: async () => {
      mapa.dejarDePedirUbicacion();
      await refrescar();
    },
  },
);

async function actualizarOrigen(escena) {
  try {
    const datos = await contarPorOrigen(escena);
    origen.innerHTML = `
      <span><b>${datos.ia}</b> detectados por la IA</span>
      <span><b>${datos.persona}</b> reportados por personas</span>
    `;
  } catch (error) {
    console.error("No se pudo cargar el recuento por origen:", error);
  }
}

async function refrescar() {
  const escena = selector.value;
  if (!escena) return;
  formulario.setEscena(escena);
  await Promise.all([
    mapa.cargar(escena),
    cola.cargar(escena),
    actualizarOrigen(escena),
  ]);
}

async function inicializar() {
  try {
    const escenas = await listarEscenas();

    if (!escenas.length) {
      listaTarjetas.innerHTML =
        '<p class="estado-lista estado-lista--error">No hay escenas en data/raw/xbd. Ver docs/datos.md.</p>';
      return;
    }

    selector.innerHTML = escenas
      .map(
        (e) =>
          `<option value="${e.escena}">${e.escena} · ${e.tipo_desastre} · ${e.edificios} edificios</option>`,
      )
      .join("");

    await refrescar();
  } catch (error) {
    console.error("No se pudo arrancar:", error);
    listaTarjetas.innerHTML =
      '<p class="estado-lista estado-lista--error">No se pudo conectar con el backend. ¿Está arrancado en el puerto 8000?</p>';
  }
}

selector.addEventListener("change", refrescar);

botonAnalizar.addEventListener("click", async () => {
  botonAnalizar.disabled = true;
  botonAnalizar.textContent = "Analizando…";
  try {
    const resultado = await analizarEscena(selector.value);
    await refrescar();
    alert(
      `Análisis terminado: ${resultado.detectadas} cambios detectados.\n\n` +
        "Son sugerencias sin confirmar: hay que revisarlas una a una.",
    );
  } catch (error) {
    console.error("Error analizando:", error);
    alert(`No se pudo analizar: ${error.message}`);
  } finally {
    botonAnalizar.disabled = false;
    botonAnalizar.textContent = "Analizar escena";
  }
});

inicializar();
