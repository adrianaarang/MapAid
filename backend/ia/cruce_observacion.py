"""Pieza 2 de la IA: cruce entre observación textual y satélite.

Recibe la descripción libre de una persona ("la casa de la esquina se
ha caído") y la imagen de Copernicus de esa zona, y responde:
  - coherente: lo que describe se ve en la imagen
  - posible: podría ser, pero la imagen no lo confirma con claridad
  - no_detectable: la imagen no permite saberlo (daño interno, nubes...)

Esto nunca publica nada por su cuenta: genera una sugerencia pendiente
igual que la pieza 1, que necesita confirmación humana.

TODO (Adriana): extraer zona de la descripción, recortar imagen,
comparar y clasificar coherencia.
"""
