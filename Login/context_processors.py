from .models import ItemCarrito

def cart_count(request):
    if request.user.is_authenticated:
        count = ItemCarrito.objects.filter(usuario=request.user).count()
    else:
        count = 0
    return {'cart_count': count}
