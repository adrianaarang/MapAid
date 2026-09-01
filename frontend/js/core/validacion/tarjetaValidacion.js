// Tarjeta de validación de una sugerencia.
//
// Muestra el antes/después recortado, qué cree la IA y con cuánta
// confianza, y los tres botones de decisión.
//
// Decisión de diseño: la palabra "SUGERENCIA SIN CONFIRMAR" está siempre
// visible. Quien revisa no debe poder olvidarse de que esto lo dijo una
// máquina y aún no lo ha mirado nadie.

import { urlImagen } from "../api.js";

const ETIQUETAS_DANO = {
  "no-damage": "Sin daño",
  "minor-damage": "Daño menor",
  "major-damage": "Daño mayor",
  destroyed: "Destruido",
  "un-classified": "Sin clasificar",
};

export class TarjetaValidacion {
  /**
   * @param {object} sugerencia - tal como la devuelve el backend
   * @param {{onValidar: Function, onSeleccionar: Function}} acciones
   */
  constructor(sugerencia, acciones = {}) {
    this.datos = sugerencia;
    this.acciones = acciones;
    this.elemento = this.construir();
  }

  construir() {
    const { escena, dano, dano_etiqueta, confianza, capturada_en } = this.datos;

    const tarjeta = document.createElement("article");
    tarjeta.className = "tarjeta";
    tarjeta.dataset.id = this.datos.id;

    const porcentaje = Math.round(confianza * 100);

    tarjeta.innerHTML = `
      <p class="tarjeta__sugerencia">⚠ Sugerencia sin confirmar</p>
      <div class="tarjeta__cabecera">
        <span class="tarjeta__dano tarjeta__dano--${dano}">
          ${dano_etiqueta || ETIQUETAS_DANO[dano] || dano}
        </span>
        <span class="tarjeta__confianza">Confianza ${porcentaje}%</span>
      </div>
      <div class="tarjeta__imagenes">
        <figure class="tarjeta__imagen">
          <img src="${urlImagen(escena, "pre")}" alt="Imagen antes del desastre" loading="lazy" />
          <figcaption>Antes</figcaption>
        </figure>
        <figure class="tarjeta__imagen">
          <img src="${urlImagen(escena, "post")}" alt="Imagen después del desastre" loading="lazy" />
          <figcaption>Después</figcaption>
        </figure>
      </div>
      <p class="tarjeta__meta">${escena}${capturada_en ? ` · ${capturada_en}` : ""}</p>
      <div class="tarjeta__acciones">
        <button type="button" class="btn-aceptar">Aceptar</button>
        <button type="button" class="btn-rechazar">Rechazar</button>
        <button type="button" class="btn-editar">Editar</button>
      </div>
    `;

    tarjeta.addEventListener("click", () => {
      this.acciones.onSeleccionar?.(this.datos);
    });

    tarjeta
      .querySelector(".btn-aceptar")
      .addEventListener("click", (evento) => this.decidir(evento, "confirmar"));
    tarjeta
      .querySelector(".btn-rechazar")
      .addEventListener("click", (evento) => this.decidir(evento, "rechazar"));
    tarjeta
      .querySelector(".btn-editar")
      .addEventListener("click", (evento) => this.decidir(evento, "corregir"));

    return tarjeta;
  }

  /**
   * Recoge la decisión y se la pasa al controlador de la cola.
   *
   * Rechazar y corregir piden motivo por diseño: es lo que después
   * permite estudiar en qué se equivoca la IA. Si la persona cancela el
   * diálogo, no se envía nada.
   */
  decidir(evento, accion) {
    evento.stopPropagation();

    const decision = { accion, revisada_por: "demo" };

    if (accion === "rechazar" || accion === "corregir") {
      const motivo = window.prompt(
        accion === "rechazar"
          ? "¿Por qué no es correcta esta detección?"
          : "¿Qué habría que corregir?",
      );
      if (motivo === null || !motivo.trim()) return;
      decision.motivo = motivo.trim();
    }

    if (accion === "corregir") {
      const nivel = window.prompt(
        "Nivel de daño correcto:\nno-damage / minor-damage / major-damage / destroyed",
        "minor-damage",
      );
      if (nivel === null || !ETIQUETAS_DANO[nivel.trim()]) return;
      decision.dano_corregido = nivel.trim();
    }

    this.bloquear(true);
    this.acciones.onValidar?.(this.datos.id, decision, this);
  }

  bloquear(bloqueada) {
    this.elemento
      .querySelectorAll("button")
      .forEach((boton) => (boton.disabled = bloqueada));
  }

  seleccionar(activa) {
    this.elemento.classList.toggle("is-seleccionada", activa);
  }

  getNodo() {
    return this.elemento;
  }

  // ---- Estados de la lista ----
  static cargando() {
    const el = document.createElement("p");
    el.className = "estado-lista";
    el.textContent = "Cargando sugerencias…";
    return el;
  }

  static vacio() {
    const el = document.createElement("p");
    el.className = "estado-lista";
    el.textContent = "No hay sugerencias pendientes de revisar.";
    return el;
  }

  static error(mensaje) {
    const el = document.createElement("p");
    el.className = "estado-lista estado-lista--error";
    el.textContent = `⚠ ${mensaje}`;
    return el;
  }
}
