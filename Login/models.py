import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.conf import settings

# --- USUARIO DE SISTEMA ---
# Extiende AbstractUser de Django para añadir roles y estados personalizados.
class Usuario(AbstractUser):
    # Definición de roles permitidos en la plataforma.
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),  # Acceso total
        ('Vendedor', 'Vendedor'),            # Acceso a ventas e inventario
        ('Usuario', 'Usuario'),              # Cliente final (pestaña de compras)
    ]
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    
    nombre_completo = models.CharField(max_length=100, null=True, blank=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='Usuario')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

# --- CLIENTE (Para Facturación) ---
# Almacena los datos de la persona que compra (NIT/Carnet, Nombre, etc.)
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
# Representa a los suministradores de mercadería (Personas o Empresas).
class Proveedor(models.Model):
    TIPO_CHOICES = [
        ('Natural', 'Persona Natural'),
        ('Empresa', 'Empresa/Jurídica'),
    ]
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='Empresa')
    nit_documento = models.CharField(max_length=20, unique=True, verbose_name="NIT o Documento")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=10, default='Activo')
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return f"{self.nombre} ({self.nit_documento})"

# --- PRODUCTO (Celulares y Accesorios) ---
# Representa los artículos físicos a la venta en el catálogo.
class Producto(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Borrador', 'Borrador'),
        ('Inactivo', 'Inactivo'),
    ]
    
    id_producto = models.AutoField(primary_key=True)
    sku_codigo = models.CharField(max_length=50, unique=True) # Código único de identificación
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_categoria') 
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')
    descripcion = models.TextField(blank=True, null=True)
    
    # Imágenes que se muestran en el catálogo (lista_celulares.html)
    imagen1 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='productos/', blank=True, null=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return f"{self.nombre} ({self.sku_codigo})"

    # --- FLUJO DE INVENTARIO ---
    # Este método se llama desde 'procesar_venta' para descontar stock automáticamente.
    def reducir_stock(self, cantidad, usuario, motivo="Venta", venta=None):
        if self.stock >= cantidad:
            self.stock -= cantidad
            self.save()
            # Registra el historial del movimiento para auditoría.
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

# --- VENTA (Encabezado) ---
# Representa el inicio de la transacción comercial.
class Venta(models.Model):
    ESTADO_CHOICES = [
        ('Iniciada', 'Iniciada'), # Creada pero sin pago confirmado
        ('Pagada', 'Pagada'),     # Transacción completada con éxito
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

    # --- FLUJO DE CIERRE DE VENTA ---
    def finalizar_venta(self, metodo_pago='Efectivo', nit='', razon_social=''):
        """Registra el pago y determina si genera la factura inmediatamente."""
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # El estado de la Venta solo cambia a 'Pagada' si es Efectivo
                is_cash = (metodo_pago == 'Efectivo')
                self.estado = 'Pagada' if is_cash else 'Iniciada'
                self.save()
                
                # 1. Registrar el Pago (Pendiente si no es efectivo)
                estado_pago = 'Completado' if is_cash else 'Pendiente'
                Pago.objects.update_or_create(
                    venta=self,
                    defaults={
                        'metodo': metodo_pago,
                        'monto': self.total,
                        'estado': estado_pago,
                        'fecha_pago': self.fecha
                    }
                )
                
                # 2. Generar Factura solo si es efectivo
                if is_cash:
                    return self.generar_factura(nit=nit, razon_social=razon_social)
                
                return None # No hay factura aún para transferencias
        except Exception as e:
            raise e

    # --- LÓGICA DE FACTURACIÓN ---
    def generar_factura(self, nit='', razon_social=''):
        """Crea el registro legal de la factura con número correlativo."""
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Generar número correlativo (FAC-XXXXXX)
                max_id = Factura.objects.all().aggregate(models.Max('id_factura'))['id_factura__max'] or 0
                nuevo_numero = f"FAC-{(max_id + 1):06d}"
                
                # Verificación de unicidad
                counter = 1
                while Factura.objects.filter(numero_factura=nuevo_numero).exists():
                    nuevo_numero = f"FAC-{(max_id + 1 + counter):06d}"
                    counter += 1

                # Crear la Factura
                factura = Factura.objects.create(
                    venta=self,
                    numero_factura=nuevo_numero,
                    nit=nit if nit else self.cliente.documento,
                    razon_social=razon_social if razon_social else self.cliente.nombre,
                    total=self.total,
                    estado='Emitida'
                )
                return factura
        except Exception as e:
            raise e

    # --- REVERSIÓN DE STOCK ---
    # Se llama cuando un administrador rechaza un pago o cancela una venta.
    def cancelar_y_devolver_stock(self, usuario, motivo="Pago Rechazado"):
        from django.db import transaction
        try:
            with transaction.atomic():
                self.estado = 'Cancelada'
                self.save()
                
                # Si hay un pago, lo marcamos como rechazado
                if hasattr(self, 'pago'):
                    self.pago.estado = 'Rechazado'
                    self.pago.save()

                # Devolvemos cada producto al inventario
                for detalle in self.detalles.all():
                    producto = detalle.producto
                    producto.stock += detalle.cantidad
                    producto.save()
                    
                    # Registramos el movimiento de Entrada por devolución
                    MovimientoInventario.objects.create(
                        producto=producto,
                        usuario=usuario,
                        venta=self,
                        tipo_movimiento='Entrada',
                        cantidad=detalle.cantidad,
                        motivo=motivo
                    )
                return True
        except Exception:
            return False

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
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Completado', 'Completado'),
        ('Rechazado', 'Rechazado'),
    ]
    
    id_pago = models.AutoField(primary_key=True)
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, db_column='id_venta')
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Completado')
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

# --- COMPRA (Aprovisionamiento) ---
# Registro de entrada de mercadería masiva.
class Compra(models.Model):
    TIPO_DOC_CHOICES = [
        ('Factura', 'Factura Legal'),
        ('Nota de Venta', 'Nota de Venta'),
        ('Recibo', 'Recibo'),
        ('Referencia Libre', 'Referencia Libre / Comprobante Informal'),
    ]
    id_compra = models.AutoField(primary_key=True)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOC_CHOICES, default='Factura')
    numero_documento = models.CharField(max_length=50, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, db_column='id_proveedor', related_name='compras')

    class Meta:
        db_table = 'compra'

    def __str__(self):
        return f"Compra {self.numero_documento} ({self.fecha.strftime('%d/%m/%Y')})"

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

# --- RECLAMO A PROVEEDOR ---
# Permite registrar devoluciones o reclamos por fallas de origen.
class ReclamoProveedor(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Resuelto (Garantía)', 'Resuelto (Garantía)'),
        ('Devuelto', 'Devuelto al Proveedor'),
        ('Rechazado', 'Rechazado por Proveedor'),
    ]
    id_reclamo = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='reclamos')
    compra = models.ForeignKey(Compra, on_delete=models.SET_NULL, null=True, blank=True, related_name='reclamos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    motivo = models.TextField()
    fecha_reclamo = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='Pendiente')
    resolucion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'reclamo_proveedor'

    def __str__(self):
        return f"Reclamo #{self.pk} - {self.producto.nombre} ({self.estado})"

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