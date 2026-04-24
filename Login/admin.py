from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Cliente, Producto, Venta, DetalleVenta, Pago, Factura, 
    MovimientoInventario, CanalVenta, CategoriaProducto, Proveedor, 
    Compra, DetalleCompra, Carrito, DetalleCarrito, ReclamoProveedor
)

class UsuarioCustomAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('nombre_completo', 'rol', 'estado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('nombre_completo', 'rol', 'estado')}),
    )

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

class VentaAdmin(admin.ModelAdmin):
    list_display = ('id_venta', 'cliente', 'usuario', 'canal', 'fecha', 'total', 'estado')
    inlines = [DetalleVentaInline]

class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1

class CompraAdmin(admin.ModelAdmin):
    list_display = ('id_compra', 'proveedor', 'tipo_documento', 'numero_documento', 'total', 'fecha', 'usuario')
    inlines = [DetalleCompraInline]

class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('id_proveedor', 'nombre', 'nit_documento', 'tipo', 'telefono', 'estado')
    list_filter = ('tipo', 'estado')
    search_fields = ('nombre', 'nit_documento')

class ReclamoProveedorAdmin(admin.ModelAdmin):
    list_display = ('id_reclamo', 'proveedor', 'producto', 'cantidad', 'estado', 'fecha_reclamo')
    list_filter = ('estado', 'proveedor')

class DetalleCarritoInline(admin.TabularInline):
    model = DetalleCarrito
    extra = 1

class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id_carrito', 'usuario', 'fecha_creacion', 'estado')
    inlines = [DetalleCarritoInline]

admin.site.register(Usuario, UsuarioCustomAdmin)
admin.site.register(Cliente)
admin.site.register(Producto)
admin.site.register(Venta, VentaAdmin)
admin.site.register(Pago)
admin.site.register(Factura)
admin.site.register(MovimientoInventario)
admin.site.register(CanalVenta)
admin.site.register(CategoriaProducto)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Compra, CompraAdmin)
admin.site.register(ReclamoProveedor, ReclamoProveedorAdmin)
admin.site.register(Carrito, CarritoAdmin)
