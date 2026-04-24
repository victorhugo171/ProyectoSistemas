from .models import Carrito, Pago

# --- FLUJO GLOBAL DE DATOS ---
# Este procesador permite que la variable 'cart_count' esté disponible en TODAS las páginas (base.html)
# para mostrar el número de items en la burbuja del carrito del menú.
def global_context(request):
    data = {
        'cart_count': 0,
        'pendientes_count': 0
    }
    
    if request.user.is_authenticated:
        # 1. Contador del carrito
        cart = Carrito.objects.filter(usuario=request.user, estado='Activo').first()
        data['cart_count'] = cart.detalles.count() if cart else 0
        
        # 2. Contador de pagos pendientes (Solo para Admins/Vendedores)
        if request.user.is_superuser or request.user.rol in ['Administrador', 'Vendedor']:
            data['pendientes_count'] = Pago.objects.filter(estado='Pendiente').count()
            
    return data
