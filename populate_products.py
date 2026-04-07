import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Login.models import Producto

def populate():
    products_to_add = [
        {
            'nombre': 'Galaxy A35 5G',
            'sku_codigo': 'SAM-A35-5G',
            'tipo': 'Celular',
            'precio': 1500.00,
            'stock': 10,
            'estado': 'Activo',
            'descripcion': 'Potente Samsung Galaxy A35 con tecnología 5G para una navegación ultrarrápida.',
            'imagen1': 'celulares/Galaxi A35 5g.png'
        },
        {
            'nombre': 'iPhone 16',
            'sku_codigo': 'APP-IP16',
            'tipo': 'Celular',
            'precio': 5500.00,
            'stock': 5,
            'estado': 'Activo',
            'descripcion': 'El nuevo iPhone 16 con cámara avanzada y chip A18 ultra potente.',
            'imagen1': 'celulares/IPhone16.jpg'
        },
        {
            'nombre': 'Motorola Moto G',
            'sku_codigo': 'MOT-G-2024',
            'tipo': 'Celular',
            'precio': 1200.00,
            'stock': 15,
            'estado': 'Activo',
            'descripcion': 'Excelente rendimiento y batería de larga duración con Motorola.',
            'imagen1': 'celulares/Motorola.jpg'
        },
        {
            'nombre': 'Redmi Note 13',
            'sku_codigo': 'XIA-RN13',
            'tipo': 'Celular',
            'precio': 950.00,
            'stock': 20,
            'estado': 'Activo',
            'descripcion': 'La mejor relación calidad-precio con el Redmi Note 13.',
            'imagen1': 'celulares/Redmi.jpg'
        },
        {
            'nombre': 'Huawei Nova',
            'sku_codigo': 'HUA-NOVA',
            'tipo': 'Celular',
            'precio': 1100.00,
            'stock': 8,
            'estado': 'Activo',
            'descripcion': 'Celular elegante con gran pantalla y diseño premium.',
            'imagen1': 'celulares/Telefono2.jpg'
        }
    ]

    for p_data in products_to_add:
        # Check if product exists by SKU
        producto, created = Producto.objects.get_or_create(
            sku_codigo=p_data['sku_codigo'],
            defaults={
                'nombre': p_data['nombre'],
                'tipo': p_data['tipo'],
                'precio': p_data['precio'],
                'stock': p_data['stock'],
                'estado': p_data['estado'],
                'descripcion': p_data['descripcion'],
                'imagen1': p_data['imagen1']
            }
        )
        if created:
            print(f"Producto creado: {producto.nombre}")
        else:
            print(f"Producto ya existe: {producto.nombre}. Actualizando campos principales.")
            producto.nombre = p_data['nombre']
            producto.imagen1 = p_data['imagen1']
            producto.save()

if __name__ == '__main__':
    print("Iniciando población de productos...")
    populate()
    print("Población completada.")
