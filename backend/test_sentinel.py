import sys
sys.path.insert(0, ".")
from modules.reportes.cruce_satelital import _descargar_recorte, _get_token
from datetime import date, timedelta

lat, lon = 40.4168, -3.7038
hoy = date.today()
pre_fin = (hoy - timedelta(days=35)).strftime("%Y-%m-%d")
pre_ini = (hoy - timedelta(days=90)).strftime("%Y-%m-%d")
post_ini = (hoy - timedelta(days=30)).strftime("%Y-%m-%d")
post_fin = (hoy - timedelta(days=5)).strftime("%Y-%m-%d")
print("pre:", pre_ini, "a", pre_fin)
print("post:", post_ini, "a", post_fin)
try:
    token = _get_token()
    print("Token OK:", token[:20])
except Exception as e:
    print("Error token:", e)
    sys.exit(1)
img_pre = _descargar_recorte(lat, lon, pre_ini, pre_fin)
print("pre:", "OK" if img_pre else "None")
img_post = _descargar_recorte(lat, lon, post_ini, post_fin)
print("post:", "OK" if img_post else "None")
