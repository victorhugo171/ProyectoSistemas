from .models import Carrito

def cart_count(request):
    if request.user.is_authenticated:
        cart = Carrito.objects.filter(usuario=request.user, estado='Activo').first()
        count = cart.detalles.count() if cart else 0
    else:
        count = 0
    return {'cart_count': count}
