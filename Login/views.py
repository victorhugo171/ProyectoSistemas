import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Producto, Carrito, DetalleCarrito, Cliente, Venta, DetalleVenta, Pago, Factura

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo Electrónico")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "nombre_completo", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permite que la contraseña se mantenga si hay un error de validación
        if 'password1' in self.fields:
            self.fields['password1'].widget.render_value = True
        if 'password2' in self.fields:
            self.fields['password2'].widget.render_value = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and ' ' in username:
            raise forms.ValidationError("El nombre de usuario no puede contener espacios.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and ' ' in email:
            raise forms.ValidationError("El correo electrónico no puede contener espacios.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            if ' ' in password:
                raise forms.ValidationError("La contraseña no puede contener espacios.")
            if len(password) < 8:
                raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return password

# Formulario para uso administrativo (permite elegir rol)
class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "nombre_completo", "email", "rol")

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            if ' ' in password:
                raise forms.ValidationError("La contraseña no puede contener espacios.")
            if len(password) < 8:
                raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return password


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

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Formatear errores de forma más sencilla para el frontend
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list[0]
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'redirect_url': str(self.success_url),
                'message': '¡Registro exitoso! Redirigiendo...'
            })
        return response

class UsuarioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    fields = ['username', 'nombre_completo', 'rol', 'email']
    template_name = 'registration/registro.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'Administrador'

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
        
        # Si el usuario es rol 'Usuario', buscamos o creamos un cliente específico para guardarlo
        if not cliente_id and request.user.rol == 'Usuario':
            nit = request.POST.get('nit', '0')
            razon_social = request.POST.get('razon_social', 'CONSUMIDOR FINAL')
            
            # Buscamos por documento (NIT)
            cliente = Cliente.objects.filter(documento=nit).first()
            
            if not cliente:
                # Si no existe, lo creamos para que quede registrado en la base de datos
                cliente = Cliente.objects.create(
                    documento=nit,
                    nombre=razon_social,
                    telefono=nit, # Usamos el NIT como teléfono para cumplir con el campo único
                    estado='Activo'
                )
        elif not cliente_id:
            return redirect('ver_carrito')
        else:
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
            
        metodo_pago = request.POST.get('metodo_pago', 'Efectivo')
        nit = request.POST.get('nit') or cliente.documento or ''
        razon_social = request.POST.get('razon_social') or f"{cliente.nombre} {cliente.apellido or ''}".strip()
        
        factura = venta.finalizar_venta(
            metodo_pago=metodo_pago,
            nit=nit,
            razon_social=razon_social
        )
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
        queryset = Venta.objects.select_related('cliente', 'usuario', 'factura').prefetch_related('detalles__producto').all().order_by('-fecha')
        q = self.request.GET.get('sales_q')
        if q:
            queryset = queryset.filter(
                Q(factura__numero_factura__icontains=q) |
                Q(cliente__nombre__icontains=q) |
                Q(cliente__apellido__icontains=q) |
                Q(cliente__documento__icontains=q)
            )
        return queryset

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object_list = self.get_queryset()
            return render(request, 'celulares/_tabla_ventas.html', {'ventas': self.object_list})
        return super().get(request, *args, **kwargs)

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



@login_required
def buscar_cliente(request):
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

@login_required
def actualizar_cantidad_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            accion = data.get('accion')
            cantidad_directa = data.get('cantidad')

            producto = get_object_or_404(Producto, pk=producto_id)
            carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
            item = DetalleCarrito.objects.filter(carrito=carrito, producto=producto).first()

            nueva_cantidad = 0
            subtotal_item = 0
            removido = False

            if item:
                if cantidad_directa is not None:
                    # Ingreso manual de cantidad
                    nueva_val = int(cantidad_directa)
                    if nueva_val <= 0:
                        item.delete()
                        item = None
                        removido = True
                    else:
                        if nueva_val > producto.stock:
                            nueva_val = producto.stock
                        item.cantidad = nueva_val
                        item.save()
                elif accion == 'sumar':
                    if item.cantidad < producto.stock:
                        item.cantidad += 1
                        item.save()
                elif accion == 'restar':
                    if item.cantidad > 1:
                        item.cantidad -= 1
                        item.save()
                    else:
                        item.delete()
                        item = None
                        removido = True
                
                if item:
                    nueva_cantidad = item.cantidad
                    subtotal_item = float(item.subtotal())
            
            return JsonResponse({
                'success': True,
                'nueva_cantidad': nueva_cantidad,
                'subtotal_item': subtotal_item,
                'total_carrito': float(carrito.total()),
                'cart_count': carrito.detalles.count(),
                'removido': removido
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)