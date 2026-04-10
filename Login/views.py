import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Producto, Carrito, DetalleCarrito, Cliente, Venta, DetalleVenta, Pago, Factura

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


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
                Q(categoria__nombre_categoria__icontains=query)
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
    cantidad = int(request.POST.get('cantidad', 1))
    
    if cantidad > producto.stock:
        cantidad = producto.stock
    
    if cantidad > 0:
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
        item, created = DetalleCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio}
        )
        if not created:
            nueva_cantidad = item.cantidad + cantidad
            if nueva_cantidad > producto.stock:
                nueva_cantidad = producto.stock
            item.cantidad = nueva_cantidad
            item.save()
            
    return redirect('ver_carrito')

@login_required
def ver_carrito(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
    items = carrito.detalles.all()
    total = carrito.total()
    return render(request, 'celulares/carrito.html', {
        'items': items, 
        'total': total
    })

@login_required
def procesar_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        if not cliente_id:
            return redirect('ver_carrito')
            
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
        items = carrito.detalles.all()
        
        if not items.exists():
            return redirect('inicio')
            
        total_venta = carrito.total()
        
        venta = Venta.objects.create(
            cliente=cliente,
            usuario=request.user,
            total=total_venta,
            estado='Iniciada'
        )
        
        for item in items:
            DetalleVenta.objects.create(
                venta=venta,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario, # Se usa el precio del carrito
                subtotal=item.subtotal()
            )
            item.producto.reducir_stock(item.cantidad, request.user, venta=venta)
            
        factura = venta.finalizar_venta(metodo_pago='Efectivo')
        # Marcar carrito como procesado
        carrito.estado = 'Procesado'
        carrito.save()
        
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
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
    item = DetalleCarrito.objects.filter(carrito=carrito, producto=producto).first()
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
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
    DetalleCarrito.objects.filter(carrito=carrito, producto=producto).delete()
    return redirect('ver_carrito')

class ReporteVentasView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Venta
    template_name = 'celulares/reporte_ventas.html'
    context_object_name = 'ventas'
    ordering = ['-fecha']

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return Venta.objects.select_related('cliente', 'usuario', 'factura').prefetch_related('detalles__producto').all().order_by('-fecha')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ahora = timezone.now()
        ventas_mes = Venta.objects.filter(fecha__year=ahora.year, fecha__month=ahora.month)
        context['total_mes'] = ventas_mes.aggregate(Sum('total'))['total__sum'] or 0
        context['total_general'] = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0
        return context

class InventarioListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Producto
    template_name = 'celulares/inventario.html'
    context_object_name = 'productos'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['valor_total'] = sum(p.stock * p.precio for p in Producto.objects.all())
        context['bajo_stock'] = Producto.objects.filter(stock__lt=5).count()
        return context

class ReporteDashView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'celulares/reportes.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ahora = timezone.now()
        
        # KPI Cards
        context['ventas_dia'] = Venta.objects.filter(fecha__date=ahora.date()).count()
        monto_total = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0
        num_ventas = Venta.objects.count()
        context['ticket_medio'] = round(monto_total / num_ventas, 2) if num_ventas > 0 else 0
        
        # Producto Estrella (más vendido en cantidad)
        estrella = DetalleVenta.objects.values('producto__nombre')\
            .annotate(total=Sum('cantidad'))\
            .order_by('-total').first()
        context['producto_estrella'] = estrella['producto__nombre'] if estrella else "N/A"

        # Datos para gráficos (JSON para Chart.js)
        # 1. Ventas últimos 7 días
        siete_dias_atras = ahora - timezone.timedelta(days=7)
        ventas_diarias = Venta.objects.filter(fecha__gte=siete_dias_atras)\
            .annotate(dia=TruncDate('fecha'))\
            .values('dia')\
            .annotate(total=Sum('total'))\
            .order_by('dia')
        
        context['labels_dias'] = json.dumps([v['dia'].strftime('%d/%m') for v in ventas_diarias])
        context['data_dias'] = json.dumps([float(v['total']) for v in ventas_diarias])

        # 2. Top 5 productos
        top_productos = DetalleVenta.objects.values('producto__nombre')\
            .annotate(total_vendido=Sum('cantidad'))\
            .order_by('-total_vendido')[:5]
        
        context['labels_prod'] = json.dumps([p['producto__nombre'] for p in top_productos])
        context['data_prod'] = json.dumps([int(p['total_vendido']) for p in top_productos])

        return context

@login_required
def buscar_cliente(request):
    from django.http import JsonResponse
    doc = request.GET.get('doc', '')
    if doc:
        cliente = Cliente.objects.filter(documento=doc, estado='Activo').first()
        if cliente:
            return JsonResponse({
                'success': True,
                'id': cliente.pk,
                'nombre': f"{cliente.nombre} {cliente.apellido if cliente.apellido else ''}",
                'documento': cliente.documento
            })
    return JsonResponse({'success': False})