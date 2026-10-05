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
    s = re.sub(r"['`’\"]", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")

def obtener_inventario():
    df = None
    if os.path.exists(ARCHIVO_LOCAL):
        try:
            # utf-8-sig remueve automáticamente los caracteres extraños Ã¯Â»Â¿
            df = pd.read_csv(ARCHIVO_LOCAL, encoding='utf-8-sig')
        except Exception:
            try:
                df = pd.read_csv(ARCHIVO_LOCAL, encoding='latin1')
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

    # Limpiar nombres de columnas
    df.columns = df.columns.astype(str).str.strip().str.lower()
    # Eliminar cualquier caracter raro al inicio de los nombres de columna
    df.columns = [re.sub(r'^[^a-z0-9]+', '', c) for c in df.columns]

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

    # Identificador limpio para buscar imágenes
    if 'codigo' in df.columns:
        df['foto_id'] = df['codigo'].apply(limpiar_codigo_para_foto)
    else:
        df['foto_id'] = ''

    # Normalizar texto de categorías tal como vienen en el archivo
    if 'categoria' in df.columns:
        df['categoria_final'] = df['categoria'].astype(str).str.strip().str.title()
    else:
        df['categoria_final'] = 'General'

    df = df.fillna('')
    return df

@app.route('/')
def catalogo():
    df = obtener_inventario()
    if isinstance(df, list) or df is None or (hasattr(df, 'empty') and df.empty):
        productos = []
        categorias = []
    else:
        categorias = sorted([c for c in df['categoria_final'].unique() if c and c.lower() not in ['nan', 'none', '']])
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

 
