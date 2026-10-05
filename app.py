import os
import re
from flask import Flask, jsonify, render_template, request
import pandas as pd

app = Flask(__name__)

ARCHIVO_LOCAL = "inventario_base.csv"
URL_DRIVE = "https://drive.google.com/uc?export=download&id=1luWZ5008syvsjNfbqulGUCbxoaU3kZfv"

def limpiar_codigo_para_foto(val):
    if not val:
        return ""
    s = str(val).strip()
    # Reemplaza comillas simples, dobles o apóstrofes por guion
    s = re.sub(r"['`’\"]", "-", s)
    # Limpia guiones repetidos si hubiera
    s = re.sub(r"-+", "-", s)
    return s.strip("-")

def obtener_inventario():
    df = None
    if os.path.exists(ARCHIVO_LOCAL):
        try:
            df = pd.read_csv(ARCHIVO_LOCAL)
        except Exception:
            pass
           
    if df is None and os.path.exists("inventario.xlsx"):
        try:
            df = pd.read_excel("inventario.xlsx")
        except Exception:
            pass

    if df is None:
        try:
            df = pd.read_csv(URL_DRIVE)
        except Exception:
            return []

    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()

    # Mapeo de columnas
    equivalencias = {
        'p_unit': 'precio_unit',
        'p_cuarto': 'precio_cuarto',
        'p_docena': 'precio_docena',
        'p_promo': 'precio_promo',
        'c_promo': 'cant_promo',
        'detalle': 'descripcion',
        'categoria': 'categoria',
        'codigo': 'codigo'
    }
    df = df.rename(columns=equivalencias)

    # Conversión numérica de precios y stock
    cols_num = ['precio_unit', 'precio_cuarto', 'precio_docena', 'precio_promo', 'stock']
    for col in cols_num:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Crear identificador limpio para buscar la imagen (ej: M'23 -> M-23)
    if 'codigo' in df.columns:
        df['foto_id'] = df['codigo'].apply(limpiar_codigo_para_foto)
    else:
        df['foto_id'] = ''

    df = df.fillna('')
    return df

@app.route('/')
def catalogo():
    df = obtener_inventario()
    if isinstance(df, list) or df is None or (hasattr(df, 'empty') and df.empty):
        productos = []
        categorias = []
    else:
        if 'categoria' in df.columns:
            categorias = sorted([c for c in df['categoria'].astype(str).str.strip().unique() if c])
        else:
            categorias = []
        productos = df.to_dict(orient='records')

    return render_template('index.html', productos=productos, categorias=categorias)

@app.route('/api/inventario')
def api():
    df = obtener_inventario()
    if isinstance(df, list) or df is None:
        return jsonify([])
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

 
