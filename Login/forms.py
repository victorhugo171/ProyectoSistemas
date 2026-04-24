from django import forms
from .models import Proveedor, Compra, DetalleCompra, ReclamoProveedor, Producto, CategoriaProducto

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'tipo', 'nit_documento', 'telefono', 'email', 'direccion', 'estado', 'observaciones']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre o Razón Social'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nit_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT o CI'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'tipo_documento', 'numero_documento', 'observaciones']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select select2'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: FAC-1234'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ReclamoProveedorForm(forms.ModelForm):
    class Meta:
        model = ReclamoProveedor
        fields = ['proveedor', 'compra', 'producto', 'cantidad', 'motivo', 'estado', 'resolucion']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'compra': forms.Select(attrs={'class': 'form-select'}),
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'resolucion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ProductoQuickForm(forms.ModelForm):
    """Formulario rápido para crear productos desde el flujo de compra."""
    class Meta:
        model = Producto
        fields = ['sku_codigo', 'nombre', 'categoria', 'precio', 'descripcion']
        widgets = {
            'sku_codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
