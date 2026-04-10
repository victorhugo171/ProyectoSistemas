import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.conf import settings

# --- USUARIO ---
class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Vendedor', 'Vendedor'),
        ('Almacenero', 'Almacenero'),
    ]
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    
    nombre_completo = models.CharField(max_length=100) # Django's first_name/last_name can also be used
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='Vendedor')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

# --- CLIENTE ---
class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    documento = models.CharField(max_length=20, unique=True, blank=True, null=True) # Manteniendo compatibilidad
    estado = models.CharField(max_length=10, default='Activo')

    class Meta:
        db_table = 'cliente'

    def __str__(self):
        return f"{self.nombre} {self.apellido if self.apellido else ''} ({self.documento if self.documento else self.id_cliente})"

# --- CANAL_VENTA ---
class CanalVenta(models.Model):
    id_canal = models.AutoField(primary_key=True)
    nombre_canal = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'canal_venta'

    def __str__(self):
        return self.nombre_canal

# --- PRODUCTO_CATEGORIA ---
class CategoriaProducto(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'producto_categoria'
        verbose_name_plural = 'Categorías de Producto'

    def __str__(self):
        return self.nombre_categoria

# --- PROVEEDOR ---
class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre

# --- PRODUCTO ---
class Producto(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Borrador', 'Borrador'),
        ('Inactivo', 'Inactivo'),
    ]
    
    id_producto = models.AutoField(primary_key=True)
    sku_codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_categoria') 
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')
    descripcion = models.TextField(blank=True, null=True)
    
    # Campos extra para mantener la UI "MOBILESTORE"
    imagen1 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='productos/', blank=True, null=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return f"{self.nombre} ({self.sku_codigo})"

    def reducir_stock(self, cantidad, usuario, motivo="Venta", venta=None):
        if self.stock >= cantidad:
            self.stock -= cantidad
            self.save()
            MovimientoInventario.objects.create(
                producto=self,
                usuario=usuario,
                venta=venta,
                tipo_movimiento='Salida',
                cantidad=cantidad,
                motivo=motivo
            )
            return True
        return False

# --- VENTA ---
class Venta(models.Model):
    ESTADO_CHOICES = [
        ('Iniciada', 'Iniciada'),
        ('Pagada', 'Pagada'),
        ('Cancelada', 'Cancelada'),
    ]
    
    id_venta = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='id_cliente')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario')
    canal = models.ForeignKey(CanalVenta, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_canal')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Iniciada')

    class Meta:
        db_table = 'venta'

    def finalizar_venta(self, metodo_pago='Efectivo', nit='', razon_social=''):
        """Genera el pago y la factura para esta venta."""
        self.estado = 'Pagada'
        self.save()
        
        # Crear Pago
        pago = Pago.objects.create(
            venta=self,
            metodo=metodo_pago,
            monto=self.total,
            estado='Completado',
            fecha_pago=self.fecha
        )
        
        # Crear Factura
        ultimo_id = Factura.objects.all().order_by('id_factura').last()
        nuevo_numero = f"FAC-{ (ultimo_id.id_factura + 1) if ultimo_id else 1:06d}"
        
        factura = Factura.objects.create(
            venta=self,
            numero_factura=nuevo_numero,
            nit=nit,
            razon_social=razon_social,
            total=self.total,
            estado='Emitida'
        )
        return factura

# --- DETALLE_VENTA ---
class DetalleVenta(models.Model):
    id_detalleVenta = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, db_column='id_venta', related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='id_producto')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_venta'

# --- PAGO ---
class Pago(models.Model):
    METODO_CHOICES = [
        ('Efectivo', 'Efectivo'),
        ('Tarjeta', 'Tarjeta'),
        ('Transferencia', 'Transferencia'),
    ]
    
    id_pago = models.AutoField(primary_key=True)
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, db_column='id_venta')
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='Completado')
    fecha_pago = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pago'

# --- FACTURA ---
class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True)
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, db_column='id_venta')
    numero_factura = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    nit = models.CharField(max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=100, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='Emitida')

    class Meta:
        db_table = 'factura'

# --- COMPRA ---
class Compra(models.Model):
    id_compra = models.AutoField(primary_key=True)
    fecha = models.DateTimeField(auto_now_add=True)
    numero_nota = models.CharField(max_length=50, unique=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, db_column='id_proveedor')

    class Meta:
        db_table = 'compra'

# --- DETALLE_COMPRA ---
class DetalleCompra(models.Model):
    id_detalleCompra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, db_column='id_compra', related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='id_producto')
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_compra'

# --- MOVIMIENTO_INVENTARIO ---
class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ('Entrada', 'Entrada'),
        ('Salida', 'Salida'),
        ('Ajuste', 'Ajuste'),
    ]
    
    id_movimiento = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='id_producto')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario')
    venta = models.ForeignKey(Venta, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_venta')
    compra = models.ForeignKey(Compra, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_compra')
    tipo_movimiento = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimiento_inventario'

# --- CARRITO ---
class Carrito(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Procesado', 'Procesado'),
        ('Abandonado', 'Abandonado'),
    ]
    
    id_carrito = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Activo')
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carrito'

    def __str__(self):
        return f"Carrito {self.id_carrito} - {self.usuario.username}"

    def total(self):
        return sum(item.subtotal() for item in self.detalles.all())

# --- DETALLE_CARRITO ---
class DetalleCarrito(models.Model):
    id_detalleCarrito = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, db_column='id_carrito', related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='id_producto')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_carrito'

    def subtotal(self):
        return self.cantidad * self.precio_unitario