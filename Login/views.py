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
from django.contrib import messages
from .models import (
    Producto, Carrito, DetalleCarrito, Cliente, Venta, DetalleVenta, 
    Pago, Factura, Proveedor, Compra, DetalleCompra, ReclamoProveedor,
    MovimientoInventario, CategoriaProducto
)
from .forms import ProveedorForm, CompraForm, ReclamoProveedorForm, ProductoQuickForm

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
    success_url = reverse_lazy('login')

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


# --- FLUJO DE CATÁLOGO ---

# Vista principal que muestra todos los productos.
# URL: '/' o '/celulares/'
# Renderiza: 'celulares/lista_celulares.html'
class CelularListView(ListView): 
    model = Producto
    template_name = 'celulares/lista_celulares.html'
    context_object_name = 'celulares'

    def get_queryset(self):
        # Permite filtrar productos por nombre o SKU desde la barra de búsqueda del header.
        queryset = super().get_queryset()
        query = self.request.GET.get('q')  
        
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) | 
                Q(sku_codigo__icontains=query) |
                Q(categoria__nombre_categoria__icontains=query)
            )
        return queryset

# Muestra la ficha técnica completa de un producto específico.
# URL: '/celulares/detalle/<pk>/'
# Renderiza: 'celulares/detalle_celular.html'
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

# --- FLUJO DEL CARRITO ---

# Se dispara al hacer clic en "Comprar Ahora".
# Añade el producto al carrito del usuario actual.
# Redirige a: 'ver_carrito'
@login_required
def agregar_al_carrito(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    cantidad = int(request.POST.get('cantidad', 1))
    
    if cantidad > producto.stock:
        cantidad = producto.stock
    
    if cantidad > 0:
        # Busca un carrito 'Activo' para el usuario, si no existe lo crea.
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
        # Añade el detalle del producto al carrito.
        item, created = DetalleCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio}
        )
        if not created:
            # Si el producto ya estaba en el carrito, suma la cantidad (respetando el stock).
            nueva_cantidad = item.cantidad + cantidad
            if nueva_cantidad > producto.stock:
                nueva_cantidad = producto.stock
            item.cantidad = nueva_cantidad
            item.save()
            
    return redirect('ver_carrito')

# Muestra el contenido actual del carrito.
# URL: '/carrito/'
# Renderiza: 'celulares/carrito.html'
@login_required
def ver_carrito(request):
    carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
    items = carrito.detalles.all()
    total = carrito.total()
    return render(request, 'celulares/carrito.html', {
        'items': items, 
        'total': total
    })

# --- FLUJO DE FINALIZACIÓN DE VENTA (CHECKOUT) ---

# Esta es la vista crítica que transforma el carrito en dinero y stock real.
# Procesa el formulario de checkout en 'carrito.html'.
@login_required
def procesar_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        
        # 1. Identificar o crear al cliente que está comprando.
        if not cliente_id and request.user.rol == 'Usuario':
            nit = request.POST.get('nit', '0').strip() or '0'
            razon_social = request.POST.get('razon_social', 'CONSUMIDOR FINAL').strip() or 'CONSUMIDOR FINAL'
            
            cliente = Cliente.objects.filter(Q(documento=nit) | Q(telefono=nit)).first()
            if not cliente:
                try:
                    cliente = Cliente.objects.create(
                        documento=nit, nombre=razon_social, telefono=nit, estado='Activo'
                    )
                except Exception:
                    cliente = Cliente.objects.get_or_create(documento='0', defaults={'nombre': 'CONSUMIDOR FINAL'})[0]
        elif not cliente_id:
            return redirect('ver_carrito')
        else:
            cliente = get_object_or_404(Cliente, pk=cliente_id)

        # 2. Iniciar el objeto Venta.
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user, estado='Activo')
        items = carrito.detalles.all()

        if not items.exists():
            return redirect('inicio')
            
        total_venta = carrito.total()
        venta = Venta.objects.create(
            cliente=cliente, usuario=request.user, total=total_venta, estado='Iniciada'
        )
        
        # 3. Transferir productos del Carrito al Detalle de Venta y Reducir Stock.
        for item in items:
            DetalleVenta.objects.create(
                venta=venta, producto=item.producto, cantidad=item.cantidad,
                precio_unitario=item.precio_unitario, subtotal=item.subtotal()
            )
            item.producto.reducir_stock(item.cantidad, request.user, venta=venta)
            
        # 4. Finalizar Pago y Generar Factura.
        metodo_pago = request.POST.get('metodo_pago', 'Efectivo')
        nit = request.POST.get('nit') or cliente.documento or ''
        razon_social = request.POST.get('razon_social') or f"{cliente.nombre}".strip()
        
        try:
            # Llama al método del modelo Venta que se encarga de la lógica de negocio.
            factura_o_none = venta.finalizar_venta(
                metodo_pago=metodo_pago, nit=nit, razon_social=razon_social
            )
            
            # El carrito se "limpia" (se marca como procesado).
            carrito.estado = 'Procesado'
            carrito.save()
            
            if factura_o_none:
                # Si hay factura (Efectivo), vamos directo al detalle
                return redirect('detalle_factura', pk=factura_o_none.pk)
            else:
                # Si es transferencia, vamos a la pantalla de espera
                return redirect('esperando_pago', pk=venta.pk)
                
        except Exception as e:
            # Si algo falla, la venta se borra para no quedar huérfana y el reporte de error vuelve al carrito.
            venta.delete()
            return redirect('ver_carrito')
    
    return redirect('ver_carrito')

# Página de éxito: Muestra la factura generada.
# URL: '/factura/<pk>/'
# Renderiza: 'celulares/factura_detalle.html'
@login_required
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render(request, 'celulares/factura_detalle.html', {'factura': factura})

class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    fields = ['nombre', 'telefono', 'documento', 'email']
    template_name = 'celulares/formulario_cliente.html'
    success_url = reverse_lazy('ver_carrito')

    def get_initial(self):
        initial = super().get_initial()
        doc = self.request.GET.get('doc')
        if doc:
            initial['documento'] = doc
        return initial

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


# --- GESTIÓN DE PAGOS (ADMIN) ---

class PagosPendientesListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Pago
    template_name = 'celulares/pagos_pendientes.html'
    context_object_name = 'pagos'

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

    def get_queryset(self):
        return Pago.objects.filter(estado='Pendiente').select_related('venta__cliente', 'venta__usuario')

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object_list = self.get_queryset()
            return render(request, 'celulares/_tabla_pagos.html', {'pagos': self.object_list})
        return super().get(request, *args, **kwargs)

@login_required
def confirmar_pago(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['Administrador', 'Vendedor']):
        return redirect('inicio')
    
    pago = get_object_or_404(Pago, pk=pk)
    venta = pago.venta
    
    pago.estado = 'Completado'
    pago.save()
    
    venta.estado = 'Pagada'
    venta.save()
    
    # GENERAR FACTURA AL MOMENTO DE CONFIRMAR
    factura = venta.generar_factura()
    
    messages.success(request, f"Pago confirmado. Se ha generado la factura {factura.numero_factura}.")
    return redirect('pagos_pendientes')

@login_required
def rechazar_pago(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['Administrador', 'Vendedor']):
        return redirect('inicio')
    
    pago = get_object_or_404(Pago, pk=pk)
    venta = pago.venta
    
    if venta.cancelar_y_devolver_stock(request.user):
        messages.warning(request, f"Venta {venta.pk} rechazada. El stock ha sido devuelto.")
    else:
        messages.error(request, "Hubo un error al intentar rechazar el pago.")
        
    return redirect('pagos_pendientes')

# --- APIS PARA POLLING (TIEMPO REAL) ---

@login_required
def api_get_venta_status(request, pk):
    """Consulta el estado de una venta para el cliente."""
    venta = get_object_or_404(Venta, pk=pk, usuario=request.user)
    data = {
        'status': venta.estado, # 'Iniciada', 'Pagada', 'Cancelada'
        'pago_estado': venta.pago.estado if hasattr(venta, 'pago') else 'Desconocido',
        'factura_pk': venta.factura.pk if hasattr(venta, 'factura') else None
    }
    return JsonResponse(data)

@login_required
def api_notificaciones_admin(request):
    """Consulta el contador de pagos pendientes para el admin."""
    if not (request.user.is_superuser or request.user.rol in ['Administrador', 'Vendedor']):
        return JsonResponse({'success': False}, status=403)
    
    count = Pago.objects.filter(estado='Pendiente').count()
    return JsonResponse({'count': count})

@login_required
def esperando_pago(request, pk):
    """Muestra la pantalla de espera mientras el admin confirma el pago."""
    venta = get_object_or_404(Venta, pk=pk, usuario=request.user)
    
    # Si ya está pagada y tiene factura, redirigir directo
    if venta.estado == 'Pagada' and hasattr(venta, 'factura'):
        return redirect('detalle_factura', pk=venta.factura.pk)
        
    return render(request, 'celulares/esperando_pago.html', {'venta': venta})


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
    doc = request.GET.get('doc') or request.GET.get('q', '')
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

# --- MÓDULO DE PROVEEDORES ---

class ProveedorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Proveedor
    template_name = 'proveedores/lista_proveedores.html'
    context_object_name = 'proveedores'

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

    def get_queryset(self):
        queryset = Proveedor.objects.all()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) | Q(nit_documento__icontains=q)
            )
        return queryset

class ProveedorCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'proveedores/formulario_proveedor.html'
    success_url = reverse_lazy('lista_proveedores')

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

class ProveedorUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'proveedores/formulario_proveedor.html'
    success_url = reverse_lazy('lista_proveedores')

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

class ProveedorDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Proveedor
    template_name = 'proveedores/detalle_proveedor.html'
    context_object_name = 'proveedor'

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Resumen de compras
        context['compras_recientes'] = self.object.compras.all().order_by('-fecha')[:10]
        context['total_comprado'] = self.object.compras.aggregate(Sum('total'))['total__sum'] or 0
        # Resumen de reclamos
        context['reclamos_historial'] = self.object.reclamos.all().order_by('-fecha_reclamo')
        context['num_reclamos'] = self.object.reclamos.count()
        return context

class CompraDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Compra
    template_name = 'proveedores/detalle_compra.html'
    context_object_name = 'compra'

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

# --- GESTIÓN DE COMPRAS (APROVISIONAMIENTO) ---

class CompraListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Compra
    template_name = 'proveedores/lista_compras.html'
    context_object_name = 'compras'
    ordering = ['-fecha']

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

@login_required
def registrar_compra(request):
    """
    Vista personalizada para registro masivo de compras.
    Permite añadir múltiples productos e incluso crear nuevos.
    """
    if not (request.user.rol in ['Administrador', 'Vendedor'] or request.user.is_superuser):
        return redirect('inicio')

    if request.method == 'POST':
        try:
            data = json.loads(request.POST.get('detalle_compra'))
            proveedor_id = request.POST.get('proveedor')
            tipo_doc = request.POST.get('tipo_documento')
            num_doc = request.POST.get('numero_documento')
            obs = request.POST.get('observaciones')

            proveedor = get_object_or_404(Proveedor, pk=proveedor_id)
            
            from django.db import transaction
            with transaction.atomic():
                compra = Compra.objects.create(
                    proveedor=proveedor,
                    usuario=request.user,
                    tipo_documento=tipo_doc,
                    numero_documento=num_doc,
                    observaciones=obs
                )
                
                total_compra = 0
                for item in data:
                    # 'item' puede ser un producto existente o uno nuevo
                    id_prod = item.get('id')
                    sku = item.get('sku')
                    nombre = item.get('nombre')
                    cantidad = int(item.get('cantidad'))
                    costo = float(item.get('costo'))
                    
                    if id_prod:
                        producto = Producto.objects.get(pk=id_prod)
                    else:
                        # Crear producto nuevo si no existe
                        categoria_id = item.get('categoria_id')
                        categoria = CategoriaProducto.objects.get(pk=categoria_id)
                        producto = Producto.objects.create(
                            sku_codigo=sku,
                            nombre=nombre,
                            categoria=categoria,
                            precio=costo / 0.9, # El costo representa el 90% del precio (10% de margen sobre venta)
                            stock=0
                        )
                    
                    # Registrar detalle
                    subtotal = cantidad * costo
                    DetalleCompra.objects.create(
                        compra=compra,
                        producto=producto,
                        cantidad=cantidad,
                        costo_unitario=costo,
                        subtotal=subtotal
                    )
                    
                    # Incrementar Stock y registrar movimiento
                    producto.stock += cantidad
                    producto.save()
                    
                    MovimientoInventario.objects.create(
                        producto=producto,
                        usuario=request.user,
                        compra=compra,
                        tipo_movimiento='Entrada',
                        cantidad=cantidad,
                        motivo=f"Compra {num_doc}"
                    )
                    
                    total_compra += subtotal
                
                compra.total = total_compra
                compra.save()
                
            messages.success(request, f"Compra {num_doc} registrada exitosamente.")
            return JsonResponse({'success': True, 'redirect': reverse_lazy('lista_compras')})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    proveedores = Proveedor.objects.filter(estado='Activo')
    productos = Producto.objects.filter(estado='Activo')
    categorias = CategoriaProducto.objects.all()
    
    return render(request, 'proveedores/registrar_compra.html', {
        'proveedores': proveedores,
        'productos': productos,
        'categorias': categorias,
        'form_producto': ProductoQuickForm()
    })

# --- RECLAMOS ---

class ReclamoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ReclamoProveedor
    template_name = 'proveedores/lista_reclamos.html'
    context_object_name = 'reclamos'
    ordering = ['-fecha_reclamo']

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser

class ReclamoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ReclamoProveedor
    form_class = ReclamoProveedorForm
    template_name = 'proveedores/formulario_reclamo.html'
    success_url = reverse_lazy('lista_reclamos')

    def test_func(self):
        return self.request.user.rol in ['Administrador', 'Vendedor'] or self.request.user.is_superuser
    
    def form_valid(self, form):
        # Al registrar un reclamo, si es una devolución, restamos del stock
        reclamo = form.save(commit=False)
        if reclamo.estado == 'Devuelto':
            producto = reclamo.producto
            if producto.stock >= reclamo.cantidad:
                producto.stock -= reclamo.cantidad
                producto.save()
                MovimientoInventario.objects.create(
                    producto=producto,
                    usuario=self.request.user,
                    tipo_movimiento='Salida',
                    cantidad=reclamo.cantidad,
                    motivo=f"Devolución a Proveedor (Reclamo #{reclamo.pk})"
                )
            else:
                messages.error(self.request, "No hay stock suficiente para realizar la devolución física.")
                return self.form_invalid(form)
        
        reclamo.save()
        return super().form_valid(form)