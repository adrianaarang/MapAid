// Formulario para que una persona reporte algo que ha visto.
//
// Es la contraparte de la cola de validación: allí se revisa lo que
// propone la IA, aquí se aporta lo que la IA no puede ver — un daño que
// se le escapó, un pozo que funciona, un puente cortado.
//
// Flujo: se pulsa "Reportar", se hace clic en el mapa para marcar dónde,
// se rellenan los datos y se publica.

import { crearReporte } from "../api.js";

export class FormularioReporte {
  constructor(elementos, { onCreado, onPedirUbicacion } = {}) {
    this.form = elementos.form;
    this.boton = elementos.boton;
    this.selectorCategoria = elementos.categoria;
    this.grupoDano = elementos.grupoDano;
    this.selectorDano = elementos.dano;
    this.descripcion = elementos.descripcion;
    this.autor = elementos.autor;
    this.aviso = elementos.aviso;

    this.onCreado = onCreado;
    this.onPedirUbicacion = onPedirUbicacion;

    this.escena = null;
    this.ubicacion = null;

    this.conectar();
  }

  conectar() {
    // El nivel de daño solo tiene sentido al reportar un daño: para un
    // recurso o un acceso bloqueado se oculta, así el formulario no
    // deja enviar datos incoherentes que el backend rechazaría.
    this.selectorCategoria.addEventListener("change", () => {
      this.grupoDano.hidden = this.selectorCategoria.value !== "dano";
    });

    this.boton.addEventListener("click", () => {
      this.aviso.textContent = "Haz clic en el mapa para marcar el lugar…";
      this.onPedirUbicacion?.();
    });

    this.form.addEventListener("submit", (evento) => {
      evento.preventDefault();
      this.enviar();
    });

    this.form
      .querySelector(".btn-cancelar-reporte")
      .addEventListener("click", () => this.cerrar());
  }

  setEscena(escena) {
    this.escena = escena;
  }

  /** La llama el mapa cuando la persona hace clic para marcar el punto. */
  setUbicacion(lat, lng) {
    this.ubicacion = { lat, lng };
    this.aviso.textContent = `Lugar marcado (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
    this.form.hidden = false;
    this.descripcion.focus();
  }

  async enviar() {
    if (!this.ubicacion) {
      this.aviso.textContent = "Marca antes el lugar en el mapa.";
      return;
    }

    const categoria = this.selectorCategoria.value;
    const reporte = {
      escena: this.escena,
      categoria,
      latitud: this.ubicacion.lat,
      longitud: this.ubicacion.lng,
      descripcion: this.descripcion.value.trim(),
      reportado_por: this.autor.value.trim() || "vecino anónimo",
    };

    if (categoria === "dano") {
      reporte.dano = this.selectorDano.value;
    }

    const botonEnviar = this.form.querySelector('button[type="submit"]');
    botonEnviar.disabled = true;

    try {
      await crearReporte(reporte);
      this.cerrar();
      this.onCreado?.();
    } catch (error) {
      console.error("No se pudo crear el reporte:", error);
      this.aviso.textContent = `No se pudo guardar: ${error.message}`;
    } finally {
      botonEnviar.disabled = false;
    }
  }

  cerrar() {
    this.form.reset();
    this.form.hidden = true;
    this.grupoDano.hidden = false;
    this.ubicacion = null;
    this.aviso.textContent = "";
  }
}
