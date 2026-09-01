// Capa de conexión con el backend de MapAid.
// Todas las llamadas fetch centralizadas aquí, con soporte de token JWT.

const BASE_URL = "http://localhost:8000/api";

export class MapAidApiError extends Error {
  constructor(mensaje, status, detalle) {
    super(mensaje);
    this.name = "MapAidApiError";
    this.status = status;
    this.detalle = detalle;
  }
}

function cabeceras(token) {
  const h = { "Content-Type": "application/json", Accept: "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function parsear(respuesta) {
  let cuerpo = null;
  try { cuerpo = await respuesta.json(); } catch {}
  if (!respuesta.ok) {
    const msg = cuerpo?.detail || cuerpo?.error || `Error ${respuesta.status}`;
    throw new MapAidApiError(msg, respuesta.status, cuerpo?.detalle || "");
  }
  return cuerpo;
}

export async function login(email, contrasena) {
  return parsear(await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: cabeceras(null),
    body: JSON.stringify({ email, contrasena }),
  }));
}

export async function listarEscenas(token) {
  return parsear(await fetch(`${BASE_URL}/deteccion/escenas`,
    { headers: cabeceras(token) }));
}

export async function analizarEscena(escena, token) {
  return parsear(await fetch(`${BASE_URL}/deteccion/analizar`, {
    method: "POST",
    headers: cabeceras(token),
    body: JSON.stringify({ escena }),
  }));
}

export async function listarSugerencias({ escena, estado } = {}, token) {
  const p = new URLSearchParams();
  if (escena) p.set("escena", escena);
  if (estado) p.set("estado", estado);
  return parsear(await fetch(`${BASE_URL}/deteccion/sugerencias?${p}`,
    { headers: cabeceras(token) }));
}

export async function obtenerResumen(escena, token) {
  const p = new URLSearchParams();
  if (escena) p.set("escena", escena);
  return parsear(await fetch(`${BASE_URL}/deteccion/resumen?${p}`,
    { headers: cabeceras(token) }));
}

export async function validarSugerencia(id, decision, token) {
  return parsear(await fetch(`${BASE_URL}/validacion/${id}`, {
    method: "PATCH",
    headers: cabeceras(token),
    body: JSON.stringify(decision),
  }));
}

export async function crearReporte(reporte, token) {
  return parsear(await fetch(`${BASE_URL}/reportes`, {
    method: "POST",
    headers: cabeceras(token),
    body: JSON.stringify(reporte),
  }));
}

export async function contarPorOrigen(escena, token) {
  const p = new URLSearchParams();
  if (escena) p.set("escena", escena);
  return parsear(await fetch(`${BASE_URL}/reportes/origen?${p}`,
    { headers: cabeceras(token) }));
}

export async function usarActivacion(payload, token) {
  return parsear(await fetch(`${BASE_URL}/copernicus/usar-activacion`, {
    method: "POST",
    headers: cabeceras(token),
    body: JSON.stringify(payload),
  }));
}

export async function listarActivaciones(token, max = 10) {
  return parsear(await fetch(`${BASE_URL}/copernicus/activaciones?max_resultados=${max}`,
    { headers: cabeceras(token) }));
}

export function urlImagen(escena, momento) {
  return `../../data/raw/xbd/images/${escena}_${momento}_disaster.png`;
}
