import os
from flask import Flask, jsonify, render_template, request
import pandas as pd

app = Flask(__name__)

# Enlace de respaldo o Google Drive
URL_DRIVE = "https://drive.google.com/uc?export=download&id=1luWZ5008syvsjNfbqulGUCbxoaU3kZfv"
ARCHIVO_LOCAL = "inventario_base.csv"

def obtener_inventario():
    df = None
    try:
        df = pd.read_csv(URL_DRIVE)
    except Exception:
        if os.path.exists(ARCHIVO_LOCAL):
            df = pd.read_csv(ARCHIVO_LOCAL)
        elif os.path.exists("inventario.xlsx"):
            df = pd.read_excel("inventario.xlsx")
        else:
            return []

    # Normalizar nombres de columnas a minúsculas
    df.columns = df.columns.str.strip().str.lower()

    # Mapeo de columnas
    equivalencias = {
        'p_unit': 'precio_unit',
        'p_cuarto': 'precio_cuarto',
        'p_docena': 'precio_docena',
        'p_promo': 'precio_promo',
        'c_promo': 'cant_promo',
        'detalle': 'descripcion',
        'categoria': 'categoria'
    }
    df = df.rename(columns=equivalencias)

    # Conversión numérica de precios y stock
    cols_num = ['precio_unit', 'precio_cuarto', 'precio_docena', 'precio_promo', 'stock']
    for col in cols_num:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df = df.fillna('')
    return df

@app.route('/')
def catalogo():
    df = obtener_inventario()
    if isinstance(df, list):
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
    if isinstance(df, list):
        return jsonify([])
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

 