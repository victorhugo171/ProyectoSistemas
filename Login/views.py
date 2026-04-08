from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


from django.db.models import Q 
from django.contrib.auth.decorators import login_required
from .models import Producto, ItemCarrito, Cliente, Venta, DetalleVenta, Pago, Factura


class UsuarioABMView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'registration/home.html'
    context_object_name = 'usuarios'

    def test_func(self):
        return self.request.user.is_superuser

class RegistroUsuario(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'registration/registro.html'
    success_url = reverse_lazy('inicio')

class UsuarioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    fields = ['username', 'email', 'first_name', 'last_name']
    template_name = 'registration/registro.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_superuser

class UsuarioDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name = 'registration/confirmar_borrado.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_superuser



class CelularListView(ListView): # Mantenemos el nombre de la vista por ahora para no romper URLs, pero usa Producto
    model = Producto
    template_name = 'celulares/lista_celulares.html'
    context_object_name = 'celulares'

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')  
        
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) | 
                Q(sku_codigo__icontains=query) |
                Q(tipo__icontains=query)
            )
        return queryset

class CelularDetailView(DetailView):
    model = Producto
    template_name = 'celulares/detalle_celular.html'
    context_object_name = 'celular'

class CelularCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Producto
    fields = '__all__'
    template_name = 'celulares/formulario_celular.html'
    success_url = reverse_lazy('lista_celulares')

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        return super().form_valid(form)

class CelularUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Producto
    fields = '__all__'
    template_name = 'celulares/formulario_celular.html'
    success_url = reverse_lazy('lista_celulares')

    def test_func(self):
        return self.request.user.is_superuser

class CelularDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Producto
    template_name = 'celulares/confirmar_borrado_celular.html'
    success_url = reverse_lazy('lista_celulares')

    def test_func(self):
        return self.request.user.is_superuser

@login_required
def agregar_al_carrito(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    # Obtener cantidad desde el formulario (POST) o por defecto 1
    cantidad = int(request.POST.get('cantidad', 1))
    
    # Validar que la cantidad no sea mayor al stock disponible
    if cantidad > producto.stock:
        cantidad = producto.stock # Opcional: podrías mostrar un error
    
    if cantidad > 0:
        item, created = ItemCarrito.objects.get_or_create(
            usuario=request.user,
            producto=producto,
            defaults={'cantidad': cantidad}
        )
        if not created:
            # Si ya existe, sumar la nueva cantidad sin exceder el stock
            nueva_cantidad = item.cantidad + cantidad
            if nueva_cantidad > producto.stock:
                nueva_cantidad = producto.stock
            item.cantidad = nueva_cantidad
            item.save()
            
    return redirect('ver_carrito')

@login_required
def ver_carrito(request):
    items = ItemCarrito.objects.filter(usuario=request.user)
    total = sum(item.subtotal() for item in items)
    clientes = Cliente.objects.filter(estado='Activo')
    return render(request, 'celulares/carrito.html', {
        'items': items, 
        'total': total,
        'clientes': clientes
    })

@login_required
def procesar_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        if not cliente_id:
            return redirect('ver_carrito')
            
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        items = ItemCarrito.objects.filter(usuario=request.user)
        
        if not items.exists():
            return redirect('inicio')
            
        total_venta = sum(item.subtotal() for item in items)
        
        # Crear la Venta
        venta = Venta.objects.create(
            cliente=cliente,
            usuario=request.user,
            total=total_venta,
            estado='Iniciada'
        )
        
        # Crear DetalleVenta y reducir stock
        for item in items:
            DetalleVenta.objects.create(
                venta=venta,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
                subtotal=item.subtotal()
            )
            # Reducir stock
            item.producto.reducir_stock(item.cantidad, request.user)
            
        # Finalizar venta (Pago en efectivo y Factura)
        factura = venta.finalizar_venta(metodo_pago='Efectivo')
        
        # Vaciar carrito
        items.delete()
        
        return redirect('detalle_factura', pk=factura.pk)
    
    return redirect('ver_carrito')

@login_required
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render(request, 'celulares/factura_detalle.html', {'factura': factura})

class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    fields = ['nombre', 'telefono', 'documento', 'email']
    template_name = 'celulares/formulario_cliente.html'
    success_url = reverse_lazy('ver_carrito')

@login_required
def restar_del_carrito(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    item = ItemCarrito.objects.filter(usuario=request.user, producto=producto).first()
    
    if item:
        if item.cantidad > 1:
            item.cantidad -= 1
            item.save()
        else:
            item.delete()
            
    return redirect('ver_carrito')

@login_required
def eliminar_item_carrito(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    ItemCarrito.objects.filter(usuario=request.user, producto=producto).delete()
    return redirect('ver_carrito')