// Cola de revisión: la lista de sugerencias pendientes.
//
// Orquesta las tarjetas y el resumen, y avisa al mapa cuando algo cambia
// para que los dos se mantengan sincronizados.

import { listarSugerencias, obtenerResumen, validarSugerencia } from "../api.js";
import { TarjetaValidacion } from "./tarjetaValidacion.js";

export class ColaValidacion {
  constructor(contenedor, contenedorResumen, { onCambio, onSeleccionar } = {}) {
    this.contenedor = contenedor;
    this.contenedorResumen = contenedorResumen;
    this.onCambio = onCambio;
    this.onSeleccionar = onSeleccionar;
    this.escena = null;
    this.tarjetas = new Map();
  }

  async cargar(escena) {
    this.escena = escena;
    this.contenedor.replaceChildren(TarjetaValidacion.cargando());

    try {
      const [sugerencias] = await Promise.all([
        listarSugerencias({ escena, estado: "pendiente" }),
        this.actualizarResumen(),
      ]);

      this.tarjetas.clear();
      this.contenedor.replaceChildren();

      if (!sugerencias.length) {
        this.contenedor.appendChild(TarjetaValidacion.vacio());
        return;
      }

      sugerencias.forEach((sugerencia) => {
        const tarjeta = new TarjetaValidacion(sugerencia, {
          onValidar: (id, decision, instancia) =>
            this.validar(id, decision, instancia),
          onSeleccionar: (datos) => {
            this.resaltar(datos.id);
            this.onSeleccionar?.(datos);
          },
        });
        this.tarjetas.set(sugerencia.id, tarjeta);
        this.contenedor.appendChild(tarjeta.getNodo());
      });
    } catch (error) {
      console.error("No se pudieron cargar las sugerencias:", error);
      this.contenedor.replaceChildren(
        TarjetaValidacion.error(
          "No se pudieron cargar las sugerencias. ¿Está arrancado el backend?",
        ),
      );
    }
  }

  async validar(id, decision, tarjeta) {
    try {
      await validarSugerencia(id, decision);

      // Al validarse deja de estar pendiente, así que sale de la cola.
      tarjeta.getNodo().remove();
      this.tarjetas.delete(id);

      if (!this.tarjetas.size) {
        this.contenedor.appendChild(TarjetaValidacion.vacio());
      }

      await this.actualizarResumen();
      this.onCambio?.();
    } catch (error) {
      console.error("No se pudo validar la sugerencia:", error);
      alert(`No se pudo guardar la decisión: ${error.message}`);
      tarjeta.bloquear(false);
    }
  }

  async actualizarResumen() {
    try {
      const resumen = await obtenerResumen(this.escena);
      this.contenedorResumen.innerHTML = Object.entries(resumen)
        .map(
          ([estado, total]) => `
            <div class="resumen__dato resumen__dato--${estado}">
              <span class="resumen__numero">${total}</span>
              <span class="resumen__etiqueta">${estado}</span>
            </div>`,
        )
        .join("");
    } catch (error) {
      console.error("No se pudo cargar el resumen:", error);
    }
  }

  resaltar(id) {
    this.tarjetas.forEach((tarjeta, clave) => tarjeta.seleccionar(clave === id));
  }
}
