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

def normalizar_categoria(cat_orig, desc):
    cat = str(cat_orig).strip()
    if not cat or cat.lower() in ['nan', 'none', '']:
        desc_l = str(desc).lower()
        if 'flomil' in desc_l:
            return 'FLOMIL'
        elif 'bota' in desc_l or 'zapato' in desc_l:
            return 'Calzado'
        elif 'pantalon' in desc_l or 'pantalón' in desc_l:
            return 'Pantalones'
        return 'Otros'
   
    # Si ya tiene categoría escrita, respetamos su texto original capitalizado
    return cat.strip().capitalize()

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

    # ID limpio para buscar fotos
    if 'codigo' in df.columns:
        df['foto_id'] = df['codigo'].apply(limpiar_codigo_para_foto)
    else:
        df['foto_id'] = ''

    # Categorías fieles al inventario
    cat_col = df['categoria'] if 'categoria' in df.columns else ''
    desc_col = df['descripcion'] if 'descripcion' in df.columns else ''
    df['categoria_final'] = [normalizar_categoria(c, d) for c, d in zip(cat_col, desc_col)]

    df = df.fillna('')
    return df

@app.route('/')
def catalogo():
    df = obtener_inventario()
    if isinstance(df, list) or df is None or (hasattr(df, 'empty') and df.empty):
        productos = []
        categorias = []
    else:
        categorias = sorted([c for c in df['categoria_final'].unique() if c])
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

 
