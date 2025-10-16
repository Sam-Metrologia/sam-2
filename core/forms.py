# core/forms.py - VERSION MEJORADA

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm as DjangoAuthenticationForm, PasswordChangeForm
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor, Documento
)
from .services import ValidationService

from django.forms.widgets import DateInput, FileInput, ClearableFileInput, TextInput
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
import re
import logging

logger = logging.getLogger('core')

# Formulario de Autenticación personalizado para usar CustomUser
class AuthenticationForm(DjangoAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Nombre de usuario'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Contraseña'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        
        if username:
            # Log intento de login para seguridad
            logger.info(f"Intento de login para usuario: {username}")
        
        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Mínimo 8 caracteres, no solo numérica'
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Ingresa la misma contraseña para verificación'
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'email', 'first_name', 'last_name', 'empresa', 'rol_usuario',
            'is_staff', 'is_superuser', 'groups', 'user_permissions',
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'rol_usuario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if request and not request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].empty_label = None
            self.fields['empresa'].initial = request.user.empresa
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Validar formato de username
            if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', username):
                raise ValidationError(
                    "El nombre de usuario debe tener entre 3-30 caracteres y solo contener letras, números, guiones y guiones bajos."
                )
        return username


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'empresa', 'rol_usuario')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'rol_usuario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if request and not request.user.is_superuser:
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
            if self.instance and self.instance != request.user:
                self.fields['is_active'].widget.attrs['disabled'] = 'disabled'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar que el email no esté en uso por otro usuario
            qs = CustomUser.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'empresa', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'disabled': 'disabled', 'class': 'form-select'}),
            'username': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        if self.instance and not self.instance.is_superuser:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['empresa'].help_text = "Tu empresa no puede ser cambiada desde aquí."
            self.fields['empresa'].required = False

        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].help_text = "El nombre de usuario no puede ser cambiado."

    def clean_empresa(self):
        if self.instance and self.instance.empresa and self.fields['empresa'].widget.attrs.get('readonly'):
            return self.instance.empresa
        return self.cleaned_data.get('empresa')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = CustomUser.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un usuario con este correo electrónico.")
        return email


class EmpresaForm(forms.ModelForm):
    fecha_inicio_plan = forms.DateField(
        label="Fecha Inicio Plan",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        required=False
    )

    class Meta:
        model = Empresa
        fields = [
            'nombre', 'nit', 'direccion', 'telefono', 'email', 'logo_empresa',
            'formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa',
            'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
            'limite_equipos_empresa', 'limite_almacenamiento_mb', 'duracion_suscripcion_meses',
            'acceso_manual_activo', 'estado_suscripcion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'nit': forms.TextInput(attrs={'class': 'form-input'}),
            'direccion': forms.TextInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'logo_empresa': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'es_periodo_prueba': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'duracion_prueba_dias': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '365'}),
            'limite_equipos_empresa': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '10000'}),
            'limite_almacenamiento_mb': forms.NumberInput(attrs={'class': 'form-input', 'min': '100', 'max': '100000', 'step': '100'}),
            'duracion_suscripcion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '120'}),
            'acceso_manual_activo': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'estado_suscripcion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Hacer email obligatorio
        self.fields['email'].required = True

        if self.instance and self.instance.fecha_inicio_plan:
            if isinstance(self.instance.fecha_inicio_plan, datetime):
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.date().strftime('%d/%m/%Y')
            else:
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.strftime('%d/%m/%Y')

        if request and not request.user.is_superuser:
            # Ocultar campos de gestión para usuarios no superusuarios
            subscription_fields = [
                'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
                'limite_equipos_empresa', 'limite_almacenamiento_mb', 'duracion_suscripcion_meses',
                'acceso_manual_activo', 'estado_suscripcion'
            ]
            
            for field in subscription_fields:
                self.fields[field].widget = forms.HiddenInput()
                self.fields[field].required = False
                if self.instance and self.instance.pk:
                    self.fields[field].initial = getattr(self.instance, field)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = Empresa.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe una empresa con este correo electrónico.")
        return email

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        if nit:
            # Validar formato de NIT (básico)
            nit_clean = re.sub(r'[^0-9]', '', nit)
            if len(nit_clean) < 9:
                raise ValidationError("El NIT debe tener al menos 9 dígitos.")
            
            qs = Empresa.objects.filter(nit=nit)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe una empresa con este NIT.")
        return nit

    def clean_limite_equipos_empresa(self):
        limite = self.cleaned_data.get('limite_equipos_empresa')
        if limite is not None and limite < 1:
            raise ValidationError("El límite de equipos debe ser mayor a 0.")
        return limite

    def clean_limite_almacenamiento_mb(self):
        limite = self.cleaned_data.get('limite_almacenamiento_mb')
        if limite is not None and limite < 100:
            raise ValidationError("El límite de almacenamiento debe ser mayor a 100 MB.")
        return limite


class EquipoForm(forms.ModelForm):
    fecha_adquisicion = forms.DateField(
        label="Fecha de Adquisición",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_version_formato = forms.DateField(
        label="Fecha de Versión del Formato",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_ultima_calibracion = forms.DateField(
        label="Fecha Última Calibración",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_ultimo_mantenimiento = forms.DateField(
        label="Fecha Último Mantenimiento",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    fecha_ultima_comprobacion = forms.DateField(
        label="Fecha Última Comprobación",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Equipo
        exclude = ('fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion')
        widgets = {
            'codigo_interno': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '20'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'tipo_equipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'modelo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'rango_medida': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'resolucion': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'error_maximo_permisible': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'archivo_compra_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'manual_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'otros_documentos_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'imagen_equipo': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.jpg,.jpeg,.png'}),
            'version_formato': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'codificacion_formato': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'frecuencia_calibracion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
            'frecuencia_mantenimiento_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
            'frecuencia_comprobacion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'max': '120', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa asignada no puede crear equipos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

        # Inicializar fechas en formato DD/MM/YYYY
        if self.instance:
            date_fields = ['fecha_ultima_calibracion', 'fecha_ultimo_mantenimiento', 'fecha_ultima_comprobacion']
            for field_name in date_fields:
                date_value = getattr(self.instance, field_name, None)
                if date_value:
                    self.fields[field_name].initial = date_value.strftime('%d/%m/%Y')

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó en el formulario
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre asignar su empresa
                if self.instance and self.instance.pk:
                    # Al editar, mantener la empresa actual
                    return self.instance.empresa
                elif self.request.user.empresa:
                    # Al crear, asignar empresa del usuario
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')

    def clean_codigo_interno(self):
        codigo = self.cleaned_data.get('codigo_interno')
        if codigo:
            # Validar formato del código
            if not re.match(r'^[A-Z0-9\-_]{3,20}$', codigo):
                raise ValidationError("El código interno debe tener 3-20 caracteres alfanuméricos, guiones o guiones bajos")

            # Verificar unicidad del código interno por empresa
            empresa = self.cleaned_data.get('empresa') or (self.request.user.empresa if self.request else None)
            if empresa:
                qs = Equipo.objects.filter(codigo_interno=codigo, empresa=empresa)
                if self.instance.pk:
                    # CORRECCIÓN: Excluir el equipo actual al editar
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError(f"Ya existe un equipo con código '{codigo}' en {empresa.nombre}")
        return codigo

    def clean_numero_serie(self):
        numero_serie = self.cleaned_data.get('numero_serie')
        if numero_serie:
            # Verificar unicidad del número de serie
            qs = Equipo.objects.filter(numero_serie=numero_serie)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un equipo con este número de serie.")
        return numero_serie

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar fechas lógicas
        fecha_adquisicion = cleaned_data.get('fecha_adquisicion')
        if fecha_adquisicion and fecha_adquisicion > timezone.now().date():
            raise ValidationError("La fecha de adquisición no puede ser futura.")

        # Validar frecuencias
        for field_name in ['frecuencia_calibracion_meses', 'frecuencia_mantenimiento_meses', 'frecuencia_comprobacion_meses']:
            freq = cleaned_data.get(field_name)
            if freq is not None and freq <= 0:
                raise ValidationError(f"La {field_name.replace('_', ' ')} debe ser positiva.")

        return cleaned_data

    def save(self, commit=True):
        # Validar límite de equipos al crear
        if not self.instance.pk:
            empresa = self.cleaned_data.get('empresa')
            if empresa:
                limite_equipos = empresa.get_limite_equipos()
                if limite_equipos is not None and limite_equipos != float('inf') and limite_equipos > 0:
                    equipos_actuales = Equipo.objects.filter(empresa=empresa).count()
                    if equipos_actuales >= limite_equipos:
                        raise ValidationError(f"La empresa ya alcanzó su límite de {limite_equipos} equipos.")

        instance = super().save(commit=commit)
        
        # Log de auditoría
        if self.request:
            from .services import AuditService
            action = "created" if not self.instance.pk else "updated"
            AuditService.log_equipment_action(action, instance, self.request.user)
        
        return instance


# Formularios de actividades mejorados
class CalibracionForm(forms.ModelForm):
    fecha_calibracion = forms.DateField(
        label="Fecha de Calibración",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Calibracion
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'numero_certificado': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'documento_calibracion': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'confirmacion_metrologica_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'intervalos_calibracion_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_calibracion:
            self.fields['fecha_calibracion'].initial = self.instance.fecha_calibracion.strftime('%d/%m/%Y')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Calibración', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_calibracion(self):
        fecha = self.cleaned_data.get('fecha_calibracion')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de calibración no puede ser futura.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que al menos se proporcione proveedor o nombre_proveedor
        proveedor = cleaned_data.get('proveedor')
        nombre_proveedor = cleaned_data.get('nombre_proveedor')
        
        if not proveedor and not nombre_proveedor:
            raise ValidationError("Debe seleccionar un proveedor o ingresar el nombre del proveedor.")
        
        return cleaned_data


class MantenimientoForm(forms.ModelForm):
    fecha_mantenimiento = forms.DateField(
        label="Fecha de Mantenimiento",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Mantenimiento
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'costo': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_mantenimiento': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_mantenimiento:
            self.fields['fecha_mantenimiento'].initial = self.instance.fecha_mantenimiento.strftime('%d/%m/%Y')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Mantenimiento', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_mantenimiento(self):
        fecha = self.cleaned_data.get('fecha_mantenimiento')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de mantenimiento no puede ser futura.")
        return fecha

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo is not None and costo < 0:
            raise ValidationError("El costo no puede ser negativo.")
        return costo


class ComprobacionForm(forms.ModelForm):
    fecha_comprobacion = forms.DateField(
        label="Fecha de Comprobación",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Comprobacion
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_comprobacion': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_comprobacion:
            self.fields['fecha_comprobacion'].initial = self.instance.fecha_comprobacion.strftime('%d/%m/%Y')

        # Filtrar proveedores por tipo de servicio y empresa
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(
                empresa=empresa,
                tipo_servicio__in=['Comprobación', 'Otro']
            )
        else:
            # Fallback: sin proveedores si no hay empresa
            self.fields['proveedor'].queryset = Proveedor.objects.none()

    def clean_fecha_comprobacion(self):
        fecha = self.cleaned_data.get('fecha_comprobacion')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de comprobación no puede ser futura.")
        return fecha


class BajaEquipoForm(forms.ModelForm):
    fecha_baja = forms.DateField(
        label="Fecha de Baja",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )
    
    class Meta:
        model = BajaEquipo
        exclude = ('equipo', 'dado_de_baja_por',)
        widgets = {
            'razon_baja': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'maxlength': '1000'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
            'documento_baja': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_baja:
            if isinstance(self.instance.fecha_baja, datetime):
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.date().strftime('%d/%m/%Y')
            else:
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.strftime('%d/%m/%Y')

    def clean_fecha_baja(self):
        fecha = self.cleaned_data.get('fecha_baja')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha de baja no puede ser futura.")
        return fecha

    def clean_razon_baja(self):
        razon = self.cleaned_data.get('razon_baja')
        if razon and len(razon.strip()) < 10:
            raise ValidationError("La razón de baja debe tener al menos 10 caracteres.")
        return razon


# Formularios de configuración mejorados
class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = '__all__'
        widgets = {
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear ubicaciones
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        empresa = self.cleaned_data.get('empresa')

        if nombre and empresa:
            # Verificar unicidad por empresa
            qs = Ubicacion.objects.filter(nombre=nombre, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe una ubicación con el nombre '{nombre}' en {empresa.nombre}.")
        return nombre

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre su empresa
                if self.instance and self.instance.pk:
                    return self.instance.empresa
                elif self.request.user.empresa:
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')


class ProcedimientoForm(forms.ModelForm):
    fecha_emision = forms.DateField(
        label="Fecha de Emisión",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Procedimiento
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
            'version': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'documento_pdf': ClearableFileInput(attrs={'class': 'form-input-file', 'accept': '.pdf'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear procedimientos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

        if self.instance and self.instance.fecha_emision:
            self.fields['fecha_emision'].initial = self.instance.fecha_emision.strftime('%d/%m/%Y')

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        empresa = self.cleaned_data.get('empresa') or (self.request.user.empresa if self.request else None)
        
        if codigo and empresa:
            # Verificar unicidad por empresa
            qs = Procedimiento.objects.filter(codigo=codigo, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe un procedimiento con el código '{codigo}' en {empresa.nombre}.")
        return codigo

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data.get('empresa')


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'
        widgets = {
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '20'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '200'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-input'}),
            'pagina_web': forms.URLInput(attrs={'class': 'form-input'}),
            'alcance': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
            'servicio_prestado': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '1000'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear proveedores
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_nombre_empresa(self):
        nombre_empresa = self.cleaned_data.get('nombre_empresa')
        empresa = self.cleaned_data.get('empresa') or (self.request.user.empresa if self.request else None)
        
        if nombre_empresa and empresa:
            # Verificar unicidad por empresa
            qs = Proveedor.objects.filter(nombre_empresa=nombre_empresa, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"Ya existe un proveedor con el nombre '{nombre_empresa}' en {empresa.nombre}.")
        return nombre_empresa

    def clean_correo_electronico(self):
        email = self.cleaned_data.get('correo_electronico')
        if email:
            # Validación básica adicional de email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise ValidationError("Ingrese una dirección de correo electrónico válida.")
        return email

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data.get('empresa')


# Formularios adicionales
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Seleccionar archivo Excel",
        help_text="Sube un archivo .xlsx con el listado de equipos.",
        widget=forms.FileInput(attrs={'class': 'form-input-file', 'accept': '.xlsx'})
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        if excel_file:
            if not excel_file.name.endswith('.xlsx'):
                raise ValidationError('El archivo debe ser un Excel (.xlsx)')
            
            # Validar tamaño (máximo 5MB para archivos Excel)
            if excel_file.size > 5 * 1024 * 1024:
                raise ValidationError('El archivo Excel no puede ser mayor a 5MB')
        
        return excel_file


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['nombre_archivo', 'descripcion', 'empresa']
        widgets = {
            'nombre_archivo': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '255'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'maxlength': '500'}),
            # 'empresa' widget se configura dinámicamente en __init__ (HiddenInput para seguridad)
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Manejo diferenciado del campo empresa
        if self.request:
            if self.request.user.is_superuser:
                # SUPERUSUARIO: Puede seleccionar cualquier empresa
                self.fields['empresa'].queryset = Empresa.objects.all()
                self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select'})
                self.fields['empresa'].required = True
            elif self.request.user.empresa:
                # USUARIO NORMAL: Campo oculto, solo su empresa
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.request.user.empresa.id)
                self.fields['empresa'].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.fields['empresa'].initial = self.request.user.empresa
                else:
                    self.fields['empresa'].initial = self.instance.empresa
                self.fields['empresa'].required = False
            else:
                # Usuario sin empresa no puede crear documentos
                self.fields['empresa'].queryset = Empresa.objects.none()
                self.fields['empresa'].widget = forms.HiddenInput()
                self.fields['empresa'].required = False

    def clean_empresa(self):
        # SEGURIDAD: Manejo diferenciado por tipo de usuario
        if self.request:
            if self.request.user.is_superuser:
                # Superusuario: retornar lo que seleccionó
                return self.cleaned_data.get('empresa')
            else:
                # Usuario normal: siempre su empresa
                if self.instance and self.instance.pk:
                    return self.instance.empresa
                elif self.request.user.empresa:
                    return self.request.user.empresa
        return self.cleaned_data.get('empresa')


# Formulario específico para formato de empresa
class EmpresaFormatoForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa']
        widgets = {
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '50'}),
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100'}),
        }
        labels = {
            'formato_version_empresa': "Versión del Formato",
            'formato_codificacion_empresa': "Codificación del Formato",
        }

    def clean_formato_fecha_version_empresa(self):
        fecha = self.cleaned_data.get('formato_fecha_version_empresa')
        if fecha and fecha > timezone.localdate():
            raise ValidationError("La fecha de versión no puede ser en el futuro.")
        return fecha