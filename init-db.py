import pymongo
from pymongo import MongoClient
import datetime
import random
import uuid
from faker import Faker
import os

# Inicializar Faker para generar datos de prueba
fake = Faker('es_CO')  # Usar localización colombiana

# Conectar a MongoDB
def connect_to_mongodb():
    try:
        client = MongoClient(os.getenv("MONGODB_URI", 'mongodb://localhost:27017/'))
        print("Conexión a MongoDB establecida con éxito")
        return client
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        return None

# Crear la base de datos y colecciones para el MVP
def create_database(client):
    # Crear o acceder a la base de datos
    db = client['jv_chatbot_mvp']
    
    # Eliminar colecciones existentes si existen (para reiniciar)
    for collection_name in db.list_collection_names():
        db[collection_name].drop()
    
    print("Base de datos 'jv_chatbot_mvp' creada correctamente")
    return db

# Crear colección de usuarios
def create_users_collection(db):
    users = db['users']
    
    # Crear índice único en la cédula
    users.create_index([("cedula", pymongo.ASCENDING)], unique=True)
    
    # Datos de prueba: 50 usuarios
    user_data = []
    for _ in range(50):
        cedula = fake.unique.random_number(digits=10)
        user = {
            "cedula": str(cedula),
            "nombre": fake.name(),
            "correo": fake.email(),
            "telefono": fake.phone_number(),
            "direccion": fake.address(),
            "fecha_registro": fake.date_time_between(start_date="-2y", end_date="now"),
            "ultima_compra": fake.date_time_between(start_date="-6M", end_date="now"),
            "estado": random.choice(["activo", "inactivo"]),
            "segmento": random.choice(["nuevo", "recurrente", "premium"]),
        }
        user_data.append(user)
    
    users.insert_many(user_data)
    print(f"Colección 'users' creada con {users.count_documents({})} documentos")
    return user_data

# Crear colección de productos
def create_products_collection(db):
    products = db['products']
    
    # Crear índice único en el código de producto
    products.create_index([("codigo", pymongo.ASCENDING)], unique=True)
    
    # Categorías de productos para JV
    categories = ["UPS", "Baterías", "Inversores", "Reguladores", "Paneles solares", 
                  "Cargadores", "Accesorios", "Convertidores", "Sistemas de energía"]
    
    # Datos de prueba: 100 productos
    product_data = []
    for i in range(100):
        codigo = f"PROD-{str(i+1).zfill(3)}"
        categoria = random.choice(categories)
        
        # Generar nombre apropiado según la categoría
        if categoria == "UPS":
            nombre = f"UPS {random.choice(['Online', 'Interactiva', 'Standby'])} {random.randint(500, 3000)}VA"
        elif categoria == "Baterías":
            nombre = f"Batería {random.choice(['Sellada', 'Gel', 'AGM', 'Litio'])} {random.randint(6, 48)}V {random.randint(5, 200)}Ah"
        elif categoria == "Inversores":
            nombre = f"Inversor {random.choice(['Onda pura', 'Onda modificada'])} {random.randint(300, 5000)}W"
        else:
            nombre = f"{categoria} {random.choice(['Serie A', 'Serie X', 'Premium', 'Estándar', 'Industrial'])}"
        
        product = {
            "codigo": codigo,
            "nombre": nombre,
            "categoria": categoria,
            "descripcion": fake.paragraph(nb_sentences=3),
            "precio": round(random.uniform(100000, 5000000), -3),  # Precios redondeados a miles
            "stock": random.randint(0, 100),
            "fecha_creacion": fake.date_time_between(start_date="-1y", end_date="now"),
            "especificaciones": {
                "potencia": f"{random.randint(300, 5000)}W" if categoria in ["UPS", "Inversores"] else None,
                "voltaje": f"{random.choice([12, 24, 36, 48])}V" if categoria in ["Baterías", "Inversores"] else None,
                "capacidad": f"{random.randint(5, 200)}Ah" if categoria == "Baterías" else None,
                "dimensiones": f"{random.randint(10, 100)}x{random.randint(10, 100)}x{random.randint(5, 50)}cm",
                "peso": f"{random.randint(1, 100)}kg",
            },
            "garantia": f"{random.randint(1, 5)} años",
            "estado": random.choice(["disponible", "agotado", "descontinuado"]),
        }
        product_data.append(product)
    
    products.insert_many(product_data)
    print(f"Colección 'products' creada con {products.count_documents({})} documentos")
    return product_data

# Crear colección de pedidos
def create_orders_collection(db, users, products):
    orders = db['orders']
    
    # Crear índice en el número de pedido y cédula para búsquedas rápidas
    orders.create_index([("numero_pedido", pymongo.ASCENDING)], unique=True)
    orders.create_index([("cedula_cliente", pymongo.ASCENDING)])
    
    # Estados posibles de un pedido
    estados_pedido = ["pendiente", "confirmado", "en preparación", "en tránsito", "entregado", "cancelado"]
    
    # Métodos de pago
    metodos_pago = ["tarjeta de crédito", "PSE", "transferencia bancaria", "efectivo contra entrega"]
    
    # Datos de prueba: 100 pedidos
    order_data = []
    for i in range(100):
        # Seleccionar un usuario aleatorio
        user = random.choice(users)
        cedula_cliente = user["cedula"]
        
        # Fecha del pedido (entre 6 meses atrás y ahora)
        fecha_pedido = fake.date_time_between(start_date="-6M", end_date="now")
        
        # Estado del pedido
        estado = random.choice(estados_pedido)
        
        # Determinar fechas según el estado
        fecha_confirmacion = None
        fecha_preparacion = None
        fecha_envio = None
        fecha_entrega = None
        
        if estado != "pendiente":
            fecha_confirmacion = fecha_pedido + datetime.timedelta(hours=random.randint(1, 24))
            
            if estado not in ["pendiente", "confirmado"]:
                fecha_preparacion = fecha_confirmacion + datetime.timedelta(hours=random.randint(12, 48))
                
                if estado not in ["pendiente", "confirmado", "en preparación"]:
                    fecha_envio = fecha_preparacion + datetime.timedelta(hours=random.randint(12, 24))
                    
                    if estado == "entregado":
                        fecha_entrega = fecha_envio + datetime.timedelta(days=random.randint(1, 5))
        
        # Crear ítems del pedido (entre 1 y 5 productos)
        items = []
        total_pedido = 0
        
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, num_items)
        
        for product in selected_products:
            cantidad = random.randint(1, 3)
            precio_unitario = product["precio"]
            subtotal = cantidad * precio_unitario
            
            item = {
                "codigo_producto": product["codigo"],
                "nombre_producto": product["nombre"],
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal
            }
            
            items.append(item)
            total_pedido += subtotal
        
        # Determinar si tiene un número de guía (solo para pedidos en tránsito o entregados)
        numero_guia = None
        if estado in ["en tránsito", "entregado"]:
            numero_guia = str(uuid.uuid4())[:8].upper()
        
        # Crear pedido
        order = {
            "numero_pedido": f"PED-{str(i+1).zfill(5)}",
            "cedula_cliente": cedula_cliente,
            "fecha_pedido": fecha_pedido,
            "estado": estado,
            "items": items,
            "total": total_pedido,
            "metodo_pago": random.choice(metodos_pago),
            "direccion_entrega": user["direccion"],
            "numero_guia": numero_guia,
            "fecha_confirmacion": fecha_confirmacion,
            "fecha_preparacion": fecha_preparacion,
            "fecha_envio": fecha_envio,
            "fecha_entrega": fecha_entrega,
            "notas": fake.text(max_nb_chars=100) if random.random() < 0.3 else None
        }
        
        order_data.append(order)
    
    orders.insert_many(order_data)
    print(f"Colección 'orders' creada con {orders.count_documents({})} documentos")

# Crear colección de consultas frecuentes
def create_faqs_collection(db):
    faqs = db['faqs']
    
    # Datos de preguntas frecuentes relacionadas con energía y UPS
    faq_data = [
        {
            "categoria": "productos",
            "pregunta": "¿Qué tipo de UPS necesito para mi computadora?",
            "respuesta": "Para una computadora personal, generalmente recomendamos una UPS interactiva con capacidad de al menos 600VA. Si tiene periféricos adicionales como monitor externo o impresora, considere una UPS de 800VA o superior. Para estaciones de trabajo o servidores pequeños, recomendamos UPS online de 1000VA o superior."
        },
        {
            "categoria": "productos",
            "pregunta": "¿Cuál es la diferencia entre una UPS interactiva y una UPS online?",
            "respuesta": "Una UPS interactiva (línea interactiva) cambia a batería cuando detecta problemas en el suministro eléctrico, ofreciendo protección básica ideal para equipos personales. Una UPS online proporciona energía constante desde la batería, aislando completamente los equipos de la red eléctrica, lo que brinda máxima protección para equipos críticos o sensibles."
        },
        {
            "categoria": "productos",
            "pregunta": "¿Cuánto tiempo puedo usar mis equipos con una UPS durante un corte de energía?",
            "respuesta": "El tiempo de respaldo depende de la capacidad de la UPS y el consumo de los equipos conectados. En general, una UPS típica puede proporcionar entre 5 y 15 minutos de respaldo para un computador personal, lo suficiente para guardar su trabajo y apagar correctamente. Para mayor tiempo de respaldo, recomendamos modelos con capacidad de batería extendida."
        },
        {
            "categoria": "soporte",
            "pregunta": "¿Cómo sé si mi UPS necesita cambio de baterías?",
            "respuesta": "Los indicadores de que su UPS necesita cambio de baterías incluyen: reducción significativa en el tiempo de respaldo, alarmas o luces de advertencia en el panel, la UPS no enciende correctamente, o han pasado más de 3-5 años desde su compra o último cambio de baterías. Recomendamos realizar pruebas periódicas de autonomía."
        },
        {
            "categoria": "soporte",
            "pregunta": "Mi UPS emite un pitido constante, ¿qué significa?",
            "respuesta": "Un pitido constante generalmente indica que la UPS está funcionando con batería debido a problemas en el suministro eléctrico, o que la batería está baja. Si el pitido continúa cuando hay electricidad normal, podría indicar sobrecarga o un problema interno que requiere revisión técnica. Consulte el manual de su modelo para interpretar los patrones de alarma específicos."
        },
        {
            "categoria": "soporte",
            "pregunta": "¿Qué dispositivos no debo conectar a una UPS?",
            "respuesta": "Evite conectar equipos con alto consumo energético como impresoras láser, calentadores, secadores de pelo, aspiradoras, o equipos médicos críticos. Tampoco conecte protectores de sobretensión adicionales o regletas múltiples. Los equipos con motores grandes o elementos calefactores pueden dañar la UPS o agotar rápidamente la batería."
        },
        {
            "categoria": "instalación",
            "pregunta": "¿Cómo instalo correctamente mi UPS?",
            "respuesta": "Para instalar correctamente una UPS: 1) Ubíquela en un lugar ventilado lejos de polvo y humedad, 2) Conecte la UPS directamente a un tomacorriente de pared (no a regletas), 3) Cargue la batería por 8-12 horas antes del primer uso, 4) Conecte los equipos críticos a las salidas con respaldo de batería, 5) Encienda primero la UPS y luego los equipos conectados, 6) Instale el software de gestión si está disponible."
        },
        {
            "categoria": "garantía",
            "pregunta": "¿Cuál es la garantía de los productos JV?",
            "respuesta": "Los productos JV cuentan con garantía desde 1 año hasta 5 años dependiendo del modelo y tipo de producto. Las UPS generalmente tienen 2 años de garantía en el equipo y 1 año en baterías. Los inversores y sistemas más grandes tienen hasta 5 años. La garantía cubre defectos de fabricación y no cubre daños por mal uso, instalación incorrecta o eventos de fuerza mayor."
        },
        {
            "categoria": "compras",
            "pregunta": "¿Cuáles son los métodos de pago aceptados?",
            "respuesta": "Aceptamos diversos métodos de pago: tarjetas de crédito (Visa, Mastercard, American Express), PSE (Pago Seguro Electrónico), transferencias bancarias, y para ciertos productos, pago contra entrega. Para proyectos grandes ofrecemos opciones de financiamiento con entidades bancarias aliadas. Los pagos en línea son procesados a través de plataformas seguras con encriptación SSL."
        },
        {
            "categoria": "compras",
            "pregunta": "¿Hacen envíos a nivel nacional?",
            "respuesta": "Sí, realizamos envíos a todo el territorio nacional. Para ciudades principales, el tiempo de entrega es de 1-3 días hábiles. Para zonas remotas o de difícil acceso, el tiempo puede extenderse a 4-7 días hábiles. Los costos de envío varían según el destino y el volumen/peso del producto. Algunos productos tienen envío gratuito según promociones vigentes."
        },
        {
            "categoria": "empresa",
            "pregunta": "¿Cuáles son los horarios de atención?",
            "respuesta": "Nuestros horarios de atención son: Lunes a viernes de 8:00 AM a 6:00 PM, y sábados de 9:00 AM a 1:00 PM. Estamos cerrados los domingos y días festivos. La atención técnica de emergencia está disponible 24/7 para clientes con contratos de soporte premium. Nuestro chatbot está disponible en todo momento para consultas básicas y programación de citas."
        },
        {
            "categoria": "empresa",
            "pregunta": "¿Dónde están ubicadas sus oficinas?",
            "respuesta": "Nuestra sede principal está ubicada en Bogotá en la Carrera 62 No. 14-65, Zona Industrial Puente Aranda. Contamos con oficinas regionales en Medellín, Cali, Barranquilla y Bucaramanga. Para visitar nuestras instalaciones, recomendamos agendar una cita previa con nuestro equipo comercial para garantizar una atención personalizada."
        }
    ]
    
    # Insertar datos
    faqs.insert_many(faq_data)
    print(f"Colección 'faqs' creada con {faqs.count_documents({})} documentos")

# Crear colección para historial de conversaciones
def create_conversations_collection(db):
    conversations = db['conversations']
    
    # Crear índices para búsquedas rápidas
    conversations.create_index([("phone_number", pymongo.ASCENDING)])
    conversations.create_index([("timestamp", pymongo.DESCENDING)])
    
    # No insertamos datos de prueba aquí, ya que se poblará con el uso del chatbot
    print("Colección 'conversations' creada correctamente")

# Función principal
def main():
    client = connect_to_mongodb()
    if not client:
        return
    
    try:
        # Crear la base de datos y colecciones
        db = create_database(client)
        
        # Crear colecciones con datos de prueba
        users = create_users_collection(db)
        products = create_products_collection(db)
        create_orders_collection(db, users, products)
        create_faqs_collection(db)
        create_conversations_collection(db)
        
        print("\nBase de datos para el MVP del ChatBot de JV creada exitosamente!")
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()