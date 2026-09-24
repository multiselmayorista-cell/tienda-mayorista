from datetime import datetime
from flask import Flask, jsonify, render_template, request
import pandas as pd

try:
  import win32print

  IMPRESION_DISPONIBLE = True
except ImportError:
  IMPRESION_DISPONIBLE = False

app = Flask(__name__)

URL_DRIVE = (
    "https://drive.google.com/uc?export=download&id=1luWZ5008syvsjNfbqulGUCbxoaU3kZfv"
)


def obtener_inventario():
  try:
    df = pd.read_csv(URL_DRIVE)
  except Exception:
    df = pd.read_csv("inventario_base.csv")

  df.columns = df.columns.str.strip().str.lower()

  equivalencias = {
      "p_unit": "precio_unit",
      "p_cuarto": "precio_cuarto",
      "p_docena": "precio_docena",
      "p_promo": "precio_promo",
      "c_promo": "cant_promo",
      "detalle": "descripcion",
      "categoria": "categoria",
  }
  df = df.rename(columns=equivalencias)

  cols_num = [
      "precio_unit",
      "precio_cuarto",
      "precio_docena",
      "precio_promo",
      "stock",
  ]
  for col in cols_num:
    if col in df.columns:
      df[col] = df[col].astype(str).str.replace(",", ".")
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  df = df.fillna("")
  return df


def mandar_a_impresora(texto_ticket):
  if not IMPRESION_DISPONIBLE:
    print(
        "[AVISO] pywin32 no está instalado o no se puede acceder a la"
        " impresora."
    )
    return False

  try:
    nombre_impresora = win32print.GetDefaultPrinter()
    hprinter = win32print.OpenPrinter(nombre_impresora)
    try:
      hjob = win32print.StartDocPrinter(
          hprinter, 1, ("Comanda Web - El Mayorista", None, "RAW")
      )
      win32print.StartPagePrinter(hprinter)

      # Comandos ESC/POS estándar para inicializar, texto y corte de papel
      init_cmd = b"\x1b\x40"
      cut_cmd = b"\x1d\x56\x00"  # Corte de papel térmico

      cuerpo = texto_ticket.encode("latin-1", errors="replace")

      datos = init_cmd + cuerpo + b"\n\n\n" + cut_cmd
      win32print.WritePrinter(hprinter, datos)

      win32print.EndPagePrinter(hprinter)
      win32print.EndDocPrinter(hprinter)
      return True
    finally:
      win32print.ClosePrinter(hprinter)
  except Exception as e:
    print(f"[ERROR IMPRESORA] {e}")
    return False


@app.route("/")
def catalogo():
  df = obtener_inventario()
  if "categoria" in df.columns:
    categorias = sorted(
        [c for c in df["categoria"].astype(str).str.strip().unique() if c]
    )
  else:
    categorias = []
  productos = df.to_dict(orient="records")
  return render_template(
      "index.html", productos=productos, categorias=categorias
  )


@app.route("/api/inventario")
def api():
  df = obtener_inventario()
  return jsonify(df.to_dict(orient="records"))


@app.route("/api/imprimir_comanda", methods=["POST"])
def imprimir_comanda():
  datos = request.get_json() or {}
  items = datos.get("items", [])
  cliente = datos.get("cliente", "Cliente Mostrador")
  comprobante = datos.get("comprobante", "Nota de Venta")
  ruta = datos.get("ruta", "Recojo en Tienda")
  total = datos.get("total", "0.00")
  fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

  lineas = [
      "========================================",
      "     MULTISERVICIOS EL MAYORISTA       ",
      "          RUC: 10701759015             ",
      "      San Juan La Orilla - Almacen      ",
      "----------------------------------------",
      "          ORDEN DE DESPACHO WEB         ",
      f"Fecha: {fecha_hora}",
      f"Cliente: {cliente}",
      f"Comprobante: {comprobante}",
      f"Ruta: {ruta}",
      "----------------------------------------",
      "CANT  DESCRIPCION             SUBTOTAL  ",
      "----------------------------------------",
  ]

  for it in items:
    nom = it.get("nombre", "")[:20]
    cant = str(it.get("cantidad", 1))
    sub = f"S/{float(it.get('subtotal', 0)):.2f}"
    lineas.append(f"{cant:<4}  {nom:<22} {sub:>8}")

    meta = f"      Talla: {it.get('talla','-')} | Color: {it.get('color','-')}"
    lineas.append(meta)

  lineas.extend([
      "----------------------------------------",
      f"TOTAL A PAGAR:                S/{total}",
      "========================================",
      "  * Flete cancelable en destino *       ",
      "  * Cancelacion total previa al envio * ",
      "\n",
  ])

  texto_final = "\n".join(lineas)

  # Intenta imprimir directamente
  exito = mandar_a_impresora(texto_final)
  return jsonify({
      "status": "ok" if exito else "error_impresora",
      "mensaje": "Impreso" if exito else "No se pudo conectar a la impresora",
  })


if __name__ == "__main__":
  app.run(debug=True, port=5000)

 
