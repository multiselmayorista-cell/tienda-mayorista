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

def clasificar_categoria_inteligente(descripcion, categoria_original):
    texto = f"{descripcion} {categoria_original}".lower()
   
    # Flomil y Carteras/Mochilas
    if any(k in texto for k in ['flomil', 'cartera', 'mochila', 'morral', 'billetera', 'neceser', 'monedero']):
        return '🌸 FLOMIL & Accesorios'
       
    # Calzado y Botas
    if any(k in texto for k in ['bota', 'calzado', 'zapato', 'zapatilla', 'sandalia', 'chutera', 'botin', 'venus']):
        return '👞 Calzado y Botas'

    # Ropa Hombre / Pantalones
    if any(k in texto for k in ['pantalon h', 'pantalón h', 'pantalon hombre', 'pantalón hombre', 'pantalon varon', 'pantalón varón', 'pantalon', 'pantalón', 'bermuda', 'boxer', 'camisa']):
        return '👖 Pantalones y Ropa Hombre'

    # Ropa Dama
    if any(k in texto for k in ['dama', 'mujer', 'blusa', 'vestido', 'falda', 'faja', 'top', 'leggin', 'brasier']):
        return '👗 Ropa Dama'
       
    # Deportes y Confección
    if any(k in texto for k in ['deporte', 'camiseta', 'futbol', 'voley', 'short deportivo', 'jugador', 'arquero', 'conjunto']):
        return '⚽ Deportes y Camisetas'

    # Librería y Útiles
    if any(k in texto for k in ['librer', 'cuaderno', 'lapicero', 'hoja', 'util', 'papel']):
        return '📚 Librería y Útiles'

    # Abarrotes y Hogar
    if any(k in texto for k in ['abarrote', 'limpieza', 'hogar', 'downy', 'shampoo', 'jabon']):
        return '🏠 Abarrotes y Hogar'

    # Si trae una categoría previa limpia, usarla
    cat_limpia = str(categoria_original).strip().capitalize()
    if cat_limpia and cat_limpia.lower() not in ['nan', 'none', '']:
        return cat_limpia

    return '🏷️ Otros Productos'

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

    # Creación de campos clave para búsqueda y fotos
    if 'codigo' in df.columns:
        df['foto_id'] = df['codigo'].apply(limpiar_codigo_para_foto)
    else:
        df['foto_id'] = ''

    # Agrupación y clasificación inteligente
    desc_col = df['descripcion'] if 'descripcion' in df.columns else ''
    cat_col = df['categoria'] if 'categoria' in df.columns else ''
   
    df['categoria_agrupada'] = [
        clasificar_categoria_inteligente(d, c)
        for d, c in zip(desc_col, cat_col)
    ]

    df = df.fillna('')
    return df

@app.route('/')
def catalogo():
    df = obtener_inventario()
    if isinstance(df, list) or df is None or (hasattr(df, 'empty') and df.empty):
        productos = []
        categorias = []
    else:
        categorias = sorted([c for c in df['categoria_agrupada'].unique() if c])
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

 
