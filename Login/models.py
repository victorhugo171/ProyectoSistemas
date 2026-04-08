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
    ]
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    
    nombre_completo = models.CharField(max_length=100) # Mapeado de 'nombre' en SQL
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='Vendedor')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

# --- CLIENTE ---
class Cliente(models.Model):
    ESTADO_CHOICES = [('Activo', 'Activo'), ('Inactivo', 'Inactivo')]
    
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, unique=True)
    documento = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')

    class Meta:
        db_table = 'cliente'

    def __str__(self):
        return f"{self.nombre} ({self.documento})"

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
    tipo = models.CharField(max_length=50) # Ej: Celular, Accesorio
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

    def reducir_stock(self, cantidad, usuario, motivo="Venta"):
        if self.stock >= cantidad:
            self.stock -= cantidad
            self.save()
            MovimientoInventario.objects.create(
                producto=self,
                usuario=usuario,
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
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Iniciada')

    class Meta:
        db_table = 'venta'

    def finalizar_venta(self, metodo_pago='Efectivo'):
        """Genera el pago y la factura para esta venta."""
        self.estado = 'Pagada'
        self.save()
        
        # Crear Pago
        pago = Pago.objects.create(
            venta=self,
            metodo=metodo_pago,
            monto=self.total,
            estado='Completado'
        )
        
        # Crear Factura con número correlativo simple
        ultimo_id = Factura.objects.all().order_by('id_factura').last()
        nuevo_numero = f"FAC-{ (ultimo_id.id_factura + 1) if ultimo_id else 1:06d}"
        
        factura = Factura.objects.create(
            venta=self,
            numero=nuevo_numero,
            total=self.total,
            estado='Emitida'
        )
        return factura

# --- DETALLE_VENTA ---
class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
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
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, db_column='id_venta')
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='Completado')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pago'

# --- FACTURA ---
class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True)
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, db_column='id_venta')
    numero = models.CharField(max_length=50, unique=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='Emitida')

    class Meta:
        db_table = 'factura'

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
    tipo_movimiento = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimiento_inventario'

# --- CARRITO (Mantenido para funcionalidad de tienda) ---
class ItemCarrito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE) # Antes era Celular
    cantidad = models.PositiveIntegerField(default=1)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'item_carrito'
        verbose_name_plural = 'Items del Carrito'

    def subtotal(self):
        return self.cantidad * self.producto.precio