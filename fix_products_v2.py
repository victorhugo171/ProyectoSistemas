import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Login.models import Producto

def fix_and_cleanup():
    # 1. Mapeo de SKUs originales a sus fotos correspondientes
    mapping = {
        'IP16': 'celulares/IPhone16.jpg',
        'SAM-S24': 'celulares/Telefono2.jpg',
        'RED-13': 'celulares/Redmi.jpg',
        'SAM-A35-5G': 'celulares/Galaxi A35 5g.png',
        'MOT-G-2024': 'celulares/Motorola.jpg',
    }

    print("Actualizando productos originales...")
    for sku, img_path in mapping.items():
        try:
            p = Producto.objects.get(sku_codigo=sku)
            p.imagen1 = img_path
            p.save()
            print(f"Actualizado: {p.nombre} (SKU: {sku}) -> {img_path}")
        except Producto.DoesNotExist:
            print(f"Advertencia: SKU {sku} no encontrado.")

    # 2. Eliminar duplicados innecesarios (los creados con prefijos en la ejecución anterior)
    redundant_skus = ['APP-IP16', 'XIA-RN13', 'HUA-NOVA']
    print("\nLimpiando productos duplicados...")
    for sku in redundant_skus:
        deleted_count, _ = Producto.objects.filter(sku_codigo=sku).delete()
        if deleted_count > 0:
            print(f"Eliminado producto redundante: {sku}")

if __name__ == '__main__':
    fix_and_cleanup()
    print("\nProceso de limpieza y actualización de fotos finalizado.")
