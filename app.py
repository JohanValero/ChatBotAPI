import logging
import json
import datetime
import os

# Configure logging
logging_dir = "logs"
if not os.path.exists(logging_dir):
    os.makedirs(logging_dir)

# Setup basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"{logging_dir}/whatsapp_bot_{datetime.datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dummuy_api")

from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId
import datetime
import os

app = Flask(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", 'mongodb://localhost:27017/')

# Conexión a MongoDB
client = MongoClient(MONGODB_URI, ssl=True, tls=True, tlsAllowInvalidCertificates=False)
print("MONGODB_URI:", MONGODB_URI)

db = client['jv_chatbot_mvp']

# Convertir ObjectId y datetime a string para serialización JSON
def parse_json(data):
    return json.loads(dumps(data))

# Rutas para simular ERP/CRM

# Endpoint para validar usuario por cédula
@app.route('/api/usuarios/validar', methods=['POST'])
def validar_usuario():
    try:
        data = request.json
        logger.info(f"Validating data: {data}")

        cedula = data.get('cedula')
        logger.info(f"Validating cedula: {cedula}")
        
        if not cedula:
            return jsonify({"error": "Se requiere cédula"}), 400
        
        usuario = db.users.find_one({"cedula": cedula})
        
        if usuario:
            # Filtrar datos sensibles
            usuario_data = {
                "cedula": usuario["cedula"],
                "nombre": usuario["nombre"],
                "correo": usuario["correo"],
                "telefono": usuario["telefono"],
                "estado": usuario["estado"],
                "segmento": usuario["segmento"]
            }
            return jsonify({"success": True, "usuario": parse_json(usuario_data)})
        else:
            return jsonify({"success": False, "mensaje": "Usuario no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error en la validación de usuario: {str(e)}")
        return jsonify({"error": "Error al validar usuario"}), 500

# Endpoint para obtener datos de un usuario
@app.route('/api/usuarios/<cedula>', methods=['GET'])
def obtener_usuario(cedula):
    try:
        logger.info(f"Fetching user data for cedula: {cedula}")
        usuario = db.users.find_one({"cedula": cedula})
    
        if usuario:
            return jsonify({"success": True, "usuario": parse_json(usuario)})
        else:
            return jsonify({"success": False, "mensaje": "Usuario no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error al obtener datos de usuario: {str(e)}")
        return jsonify({"error": "Error al obtener datos de usuario"}), 500

# Endpoint para obtener todos los pedidos de un usuario
@app.route('/api/pedidos/usuario/<cedula>', methods=['GET'])
def obtener_pedidos_usuario(cedula):
    pedidos = list(db.orders.find({"cedula_cliente": cedula}))
    
    if pedidos:
        return jsonify({"success": True, "pedidos": parse_json(pedidos)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron pedidos para este usuario"}), 404

# Endpoint para obtener un pedido específico
@app.route('/api/pedidos/<numero_pedido>', methods=['GET'])
def obtener_pedido(numero_pedido):
    pedido = db.orders.find_one({"numero_pedido": numero_pedido})
    
    if pedido:
        return jsonify({"success": True, "pedido": parse_json(pedido)})
    else:
        return jsonify({"success": False, "mensaje": "Pedido no encontrado"}), 404

# Endpoint para buscar productos por categoría
@app.route('/api/productos/categoria/<categoria>', methods=['GET'])
def productos_por_categoria(categoria):
    productos = list(db.products.find({"categoria": categoria}))
    
    if productos:
        return jsonify({"success": True, "productos": parse_json(productos)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron productos en esta categoría"}), 404

# Endpoint para buscar un producto por código
@app.route('/api/productos/<codigo>', methods=['GET'])
def obtener_producto(codigo):
    producto = db.products.find_one({"codigo": codigo})
    
    if producto:
        return jsonify({"success": True, "producto": parse_json(producto)})
    else:
        return jsonify({"success": False, "mensaje": "Producto no encontrado"}), 404

# Endpoint para buscar productos por nombre (búsqueda parcial)
@app.route('/api/productos/buscar', methods=['GET'])
def buscar_productos():
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({"error": "Se requiere un término de búsqueda"}), 400
    
    # Búsqueda por coincidencia parcial en el nombre
    productos = list(db.products.find({"nombre": {"$regex": query, "$options": "i"}}))
    
    if productos:
        return jsonify({"success": True, "productos": parse_json(productos)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron productos que coincidan con la búsqueda"}), 404

# Endpoint para obtener productos disponibles
@app.route('/api/productos/disponibles', methods=['GET'])
def productos_disponibles():
    productos = list(db.products.find({"estado": "disponible", "stock": {"$gt": 0}}))
    
    if productos:
        return jsonify({"success": True, "productos": parse_json(productos)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron productos disponibles"}), 404

# Endpoint para verificar stock de un producto
@app.route('/api/productos/stock/<codigo>', methods=['GET'])
def verificar_stock(codigo):
    producto = db.products.find_one({"codigo": codigo}, {"_id": 0, "codigo": 1, "nombre": 1, "stock": 1})
    
    if producto:
        return jsonify({"success": True, "stock": parse_json(producto)})
    else:
        return jsonify({"success": False, "mensaje": "Producto no encontrado"}), 404

# Endpoint para obtener preguntas frecuentes
@app.route('/api/faqs', methods=['GET'])
def obtener_faqs():
    categoria = request.args.get('categoria')
    
    if categoria:
        faqs = list(db.faqs.find({"categoria": categoria}))
    else:
        faqs = list(db.faqs.find())
    
    if faqs:
        return jsonify({"success": True, "faqs": parse_json(faqs)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron preguntas frecuentes"}), 404

# Endpoint para crear un nuevo pedido (simulación)
@app.route('/api/pedidos/crear', methods=['POST'])
def crear_pedido():
    data = request.json
    
    # Verificar datos mínimos requeridos
    if not data.get('cedula_cliente') or not data.get('items'):
        return jsonify({"error": "Se requiere cédula del cliente e items del pedido"}), 400
    
    # Generar número de pedido
    import random
    numero_pedido = f"PED-{str(random.randint(10000, 99999))}"
    
    # Calcular total del pedido
    total_pedido = 0
    items_procesados = []
    
    for item in data.get('items', []):
        codigo_producto = item.get('codigo_producto')
        cantidad = item.get('cantidad', 1)
        
        # Buscar producto en la base de datos
        producto = db.products.find_one({"codigo": codigo_producto})
        
        if producto:
            precio_unitario = producto.get('precio', 0)
            subtotal = precio_unitario * cantidad
            
            item_procesado = {
                "codigo_producto": codigo_producto,
                "nombre_producto": producto.get('nombre', ''),
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal
            }
            
            items_procesados.append(item_procesado)
            total_pedido += subtotal
    
    # Crear pedido
    nuevo_pedido = {
        "numero_pedido": numero_pedido,
        "cedula_cliente": data.get('cedula_cliente'),
        "fecha_pedido": datetime.datetime.now(),
        "estado": "pendiente",
        "items": items_procesados,
        "total": total_pedido,
        "metodo_pago": data.get('metodo_pago', 'pendiente'),
        "direccion_entrega": data.get('direccion_entrega', ''),
        "notas": data.get('notas', '')
    }
    
    # Insertar en la base de datos
    db.orders.insert_one(nuevo_pedido)
    
    return jsonify({
        "success": True, 
        "mensaje": "Pedido creado exitosamente", 
        "pedido": parse_json(nuevo_pedido)
    })

# Endpoint para actualizar estado de un pedido
@app.route('/api/pedidos/actualizar/<numero_pedido>', methods=['PUT'])
def actualizar_pedido(numero_pedido):
    data = request.json
    nuevo_estado = data.get('estado')
    
    if not nuevo_estado:
        return jsonify({"error": "Se requiere el nuevo estado"}), 400
    
    # Validar estado
    estados_validos = ["pendiente", "confirmado", "en preparación", "en tránsito", "entregado", "cancelado"]
    if nuevo_estado not in estados_validos:
        return jsonify({"error": f"Estado no válido. Debe ser uno de: {', '.join(estados_validos)}"}), 400
    
    # Actualizar estado y fecha correspondiente
    actualizacion = {"estado": nuevo_estado}
    
    if nuevo_estado == "confirmado":
        actualizacion["fecha_confirmacion"] = datetime.datetime.now()
    elif nuevo_estado == "en preparación":
        actualizacion["fecha_preparacion"] = datetime.datetime.now()
    elif nuevo_estado == "en tránsito":
        actualizacion["fecha_envio"] = datetime.datetime.now()
        actualizacion["numero_guia"] = f"GUIA-{str(ObjectId())[-8:].upper()}"
    elif nuevo_estado == "entregado":
        actualizacion["fecha_entrega"] = datetime.datetime.now()
    
    resultado = db.orders.update_one(
        {"numero_pedido": numero_pedido},
        {"$set": actualizacion}
    )
    
    if resultado.modified_count > 0:
        pedido_actualizado = db.orders.find_one({"numero_pedido": numero_pedido})
        return jsonify({
            "success": True, 
            "mensaje": "Pedido actualizado exitosamente", 
            "pedido": parse_json(pedido_actualizado)
        })
    else:
        return jsonify({"success": False, "mensaje": "No se pudo actualizar el pedido o no existe"}), 404

# Endpoint para guardar una conversación
@app.route('/api/conversaciones/guardar', methods=['POST'])
def guardar_conversacion():
    data = request.json
    
    # Verificar datos mínimos
    if not data.get('phone_number') or not data.get('mensaje'):
        return jsonify({"error": "Se requiere número de teléfono y mensaje"}), 400
    
    # Crear documento de conversación
    conversacion = {
        "phone_number": data.get('phone_number'),
        "cedula": data.get('cedula', ''),
        "mensaje": data.get('mensaje'),
        "respuesta": data.get('respuesta', ''),
        "timestamp": datetime.datetime.now(),
        "intent": data.get('intent', ''),
        "sentimiento": data.get('sentimiento', 'neutral')
    }
    
    # Insertar en la base de datos
    db.conversations.insert_one(conversacion)
    
    return jsonify({
        "success": True, 
        "mensaje": "Conversación guardada exitosamente", 
        "conversacion": parse_json(conversacion)
    })

# Endpoint para obtener conversaciones de un usuario
@app.route('/api/conversaciones/<phone_number>', methods=['GET'])
def obtener_conversaciones(phone_number):
    # Obtener el número de conversaciones a retornar (opcional)
    limit = request.args.get('limit', 10, type=int)
    
    # Buscar conversaciones ordenadas por fecha (más recientes primero)
    conversaciones = list(db.conversations.find(
        {"phone_number": phone_number}
    ).sort("timestamp", -1).limit(limit))
    
    if conversaciones:
        return jsonify({"success": True, "conversaciones": parse_json(conversaciones)})
    else:
        return jsonify({"success": False, "mensaje": "No se encontraron conversaciones para este usuario"}), 404

# Endpoint para obtener información de la empresa (para preguntas frecuentes)
@app.route('/api/empresa/info', methods=['GET'])
def obtener_info_empresa():
    info_empresa = {
        "nombre": "JV Energy Solutions",
        "horario_atencion": {
            "lunes_viernes": "8:00 AM - 6:00 PM",
            "sabados": "9:00 AM - 1:00 PM",
            "domingos_festivos": "Cerrado"
        },
        "direccion_principal": "Carrera 62 No. 14-65, Zona Industrial Puente Aranda, Bogotá",
        "telefonos": {
            "ventas": "+57 1 5709000",
            "soporte": "+57 1 5709001",
            "whatsapp": "+57 3001234567"
        },
        "correo": "servicioalcliente@jv.co",
        "web": "www.jv.co",
        "redes_sociales": {
            "facebook": "JVEnergy",
            "instagram": "@jvenergy",
            "linkedin": "jv-energy-solutions"
        },
        "metodos_pago": [
            "Tarjetas de crédito (Visa, Mastercard, American Express)",
            "PSE (Pago Seguro Electrónico)",
            "Transferencia bancaria",
            "Efectivo contra entrega (en compras seleccionadas)"
        ],
        "politica_garantia": "Los productos JV cuentan con garantía desde 1 año hasta 5 años dependiendo del modelo y tipo de producto.",
        "plazo_entrega": "Ciudades principales: 1-3 días hábiles. Zonas remotas: 4-7 días hábiles."
    }
    
    return jsonify({"success": True, "info": info_empresa})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)