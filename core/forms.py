# core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm as DjangoAuthenticationForm, PasswordChangeForm
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor,
    Documento # Importar el nuevo modelo Documento
)

from django.forms.widgets import DateInput, FileInput, ClearableFileInput, TextInput
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime # Asegúrate de que datetime esté importado aquí

# Formulario de Autenticación personalizado para usar CustomUser
class AuthenticationForm(DjangoAuthenticationForm):
    pass

# Formulario para CustomUser (Creación)
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Incluir explícitamente 'groups' y 'user_permissions' para asegurar su presencia
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'empresa', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}), # Widget para la selección de grupos
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}), # Widget para permisos
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filtrar el queryset de empresa y deshabilitar campos para usuarios no superusuarios
        if request and not request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].empty_label = None
            self.fields['empresa'].initial = request.user.empresa
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            # Los campos 'groups' y 'user_permissions' deben ser deshabilitados también para no superusuarios
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()

        # Aplicar clases de Tailwind CSS a todos los campos visibles por defecto
        # Se excluyen is_staff, is_superuser, groups, user_permissions de esta aplicación genérica
        # porque ya tienen widgets específicos o son manejados por el template.
        for field_name, field in self.fields.items():
            if field_name not in ['is_staff', 'is_superuser', 'groups', 'user_permissions']:
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.PasswordInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})


# Formulario para CustomUser (Cambio/Edición)
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        # Incluir explícitamente 'groups' y 'user_permissions'
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'empresa',)
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Si el usuario que edita NO es superusuario, restringir ciertos campos
        if request and not request.user.is_superuser:
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_staff'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_superuser'].widget.attrs['disabled'] = 'disabled'
            self.fields['groups'].widget.attrs['disabled'] = 'disabled'
            self.fields['user_permissions'].widget.attrs['disabled'] = 'disabled'
            # Permitir que un usuario no-superusuario edite su propio is_active, pero no el de otros
            if self.instance and self.instance != request.user:
                self.fields['is_active'].widget.attrs['disabled'] = 'disabled'

        # Aplicar clases de Tailwind CSS a los campos restantes
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']: # Excluir checkboxes y campos selectmultiple
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})


# Formulario para el perfil de usuario (solo para que el usuario edite su propio perfil)
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'empresa', 'username']
        widgets = {
            'empresa': forms.Select(attrs={'disabled': 'disabled'}),
            'username': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.is_superuser:
            self.fields['empresa'].widget.attrs['readonly'] = True
            self.fields['empresa'].help_text = "Tu empresa no puede ser cambiada desde aquí."
            self.fields['empresa'].required = False

        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].help_text = "El nombre de usuario no puede ser cambiado."

        # Aplicar clases de Tailwind a los campos restantes
        for field_name, field in self.fields.items():
            if field_name not in ['empresa', 'username']: # Excluir los que ya tienen attrs
                 if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                 elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})

    def clean_empresa(self):
        # Esta lógica asegura que la empresa no se cambie si el campo está en solo lectura
        if self.instance and self.instance.empresa and self.fields['empresa'].widget.attrs.get('readonly'):
            return self.instance.empresa
        return self.cleaned_data.get('empresa')


# Formularios de Empresa
class EmpresaForm(forms.ModelForm):
    # Añadir los nuevos campos y quitar los que ya no se usan del modelo
    duracion_suscripcion_meses = forms.IntegerField(
        label="Duración Suscripción (meses)",
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        help_text="Número de meses que dura la suscripción de la empresa."
    )
    limite_equipos_empresa = forms.IntegerField(
        label="Límite Máximo de Equipos",
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        help_text="Cantidad máxima de equipos permitidos para esta empresa."
    )

    # AJUSTE: Usar forms.DateField con TextInput para fecha_inicio_plan
    fecha_inicio_plan = forms.DateField(
        label="Fecha Inicio Plan",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'], # Añadir estos formatos para parseo
        required=False # Mantener como False si es opcional
    )

    class Meta:
        model = Empresa
        # Ajustar los campos que se muestran en el formulario
        fields = [
            'nombre', 'nit', 'direccion', 'telefono', 'email', 'logo_empresa',
            'formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa',
            'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan', # Asegurarse de que esté aquí
            'limite_equipos_empresa', 'duracion_suscripcion_meses', # Nuevos campos
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
            'duracion_prueba_dias': forms.NumberInput(attrs={'class': 'form-input'}),
            # 'fecha_inicio_plan': DateInput(attrs={'type': 'date', 'class': 'form-input'}), # ELIMINAR O COMENTAR ESTA LÍNEA si usas forms.DateField arriba
            'acceso_manual_activo': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'}),
            'estado_suscripcion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # AJUSTE: Inicializar fecha_inicio_plan para edición
        if self.instance and self.instance.fecha_inicio_plan:
            # Asegurarse de que el formato sea 'DD/MM/YYYY' para el TextInput
            if isinstance(self.instance.fecha_inicio_plan, datetime):
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.date().strftime('%d/%m/%Y')
            else:
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan.strftime('%d/%m/%Y')

        # Si el usuario NO es superusuario, deshabilitar/ocultar campos de suscripción
        if request and not request.user.is_superuser:
            # Ocultar o deshabilitar campos de gestión de suscripción
            self.fields['es_periodo_prueba'].widget = forms.HiddenInput()
            self.fields['duracion_prueba_dias'].widget = forms.HiddenInput()
            self.fields['fecha_inicio_plan'].widget = forms.HiddenInput() # Asegúrate de que este también se oculte
            self.fields['limite_equipos_empresa'].widget = forms.HiddenInput() # Ocultar para no superusuarios
            self.fields['duracion_suscripcion_meses'].widget = forms.HiddenInput() # Ocultar para no superusuarios
            self.fields['acceso_manual_activo'].widget = forms.HiddenInput()
            self.fields['estado_suscripcion'].widget = forms.HiddenInput()
            
            # Asegurarse de que los datos no sean modificados accidentalmente si están ocultos
            if self.instance and self.instance.pk:
                self.fields['es_periodo_prueba'].initial = self.instance.es_periodo_prueba
                self.fields['duracion_prueba_dias'].initial = self.instance.duracion_prueba_dias
                self.fields['fecha_inicio_plan'].initial = self.instance.fecha_inicio_plan # Inicializar aunque esté oculto
                self.fields['limite_equipos_empresa'].initial = self.instance.limite_equipos_empresa
                self.fields['duracion_suscripcion_meses'].initial = self.instance.duracion_suscripcion_meses
                self.fields['acceso_manual_activo'].initial = self.instance.acceso_manual_activo
                self.fields['estado_suscripcion'].initial = self.instance.estado_suscripcion
            
            # Establecer required=False para los campos ocultos
            self.fields['es_periodo_prueba'].required = False
            self.fields['duracion_prueba_dias'].required = False
            self.fields['fecha_inicio_plan'].required = False
            self.fields['limite_equipos_empresa'].required = False
            self.fields['duracion_suscripcion_meses'].required = False
            self.fields['acceso_manual_activo'].required = False
            self.fields['estado_suscripcion'].required = False
        
        # Aplicar clases de Tailwind CSS a los campos visibles restantes
        for field_name, field in self.fields.items():
            # Solo aplicar si el widget no es HiddenInput (es decir, el campo es visible)
            if not isinstance(field.widget, forms.HiddenInput):
                if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.URLInput)):
                    field.widget.attrs.update({'class': 'form-input'})
                elif isinstance(field.widget, ClearableFileInput):
                    field.widget.attrs.update({'class': 'form-input-file'})


    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

# NUEVO Formulario para la información de formato de la Empresa
class EmpresaFormatoForm(forms.ModelForm):
    # Ya está usando DateInput type='date' en Meta.widgets, que es preferible
    # a TextInput para fechas en la interfaz si se busca un selector de fecha nativo.
    # Si quieres DD/MM/YYYY en el campo de texto, puedes mantenerlo como estaba:
    # fecha_version_formato_empresa = forms.DateField( # Cambia a DateField
    #     label="Fecha de Versión (DD/MM/YYYY)",
    #     widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
    #     input_formats=['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'], # Asegura estos formatos
    #     required=False
    # )

    class Meta:
        model = Empresa
        fields = ['formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa']
        widgets = {
            'formato_version_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            # Mantener DateInput type='date' para facilitar la selección de fecha
            'formato_fecha_version_empresa': DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'formato_codificacion_empresa': forms.TextInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'formato_version_empresa': "Versión del Formato",
            'formato_codificacion_empresa': "Codificación del Formato",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si usas DateInput type='date', Django ya se encarga de la inicialización a 'YYYY-MM-DD'
        # Si prefieres TextInput y DD/MM/YYYY, descomenta esta parte:
        # if self.instance and self.instance.formato_fecha_version_empresa:
        #     self.fields['formato_fecha_version_empresa'].initial = self.instance.formato_fecha_version_empresa.strftime('%d/%m/%Y')
        pass # No se necesita inicialización explícita si el widget es type='date'

    def clean_formato_fecha_version_empresa(self):
        fecha = self.cleaned_data.get('formato_fecha_version_empresa')
        if fecha and fecha > timezone.localdate():
            raise ValidationError("La fecha de versión no puede ser en el futuro.")
        return fecha

    # El método save no necesita ser sobreescrito si los campos están mapeados correctamente
    # y la validación clean ya se encarga de transformar el valor.
    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     if commit:
    #         instance.save()
    #     return instance


# Formularios de Ubicacion
class UbicacionForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = '__all__'
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None) # Asegúrate de obtener 'request' aquí
        super().__init__(*args, **kwargs)
        if request and not request.user.is_superuser and request.user.empresa:
            self.fields['empresa'].queryset = Empresa.objects.filter(pk=request.user.empresa.pk)
            self.fields['empresa'].initial = request.user.empresa.pk
            self.fields['empresa'].widget.attrs['disabled'] = 'disabled'
        elif request and request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()
        else:
            self.fields['empresa'].queryset = Empresa.objects.none() # Manejar caso sin empresa si no superusuario

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})


# Formularios de Procedimiento
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
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input'}),
            'version': forms.TextInput(attrs={'class': 'form-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk:
                self.fields['empresa'].initial = self.request.user.empresa
            else:
                self.fields['empresa'].initial = self.instance.empresa
            self.fields['empresa'].required = False
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()
            self.fields['empresa'].required = True

        if self.instance and self.instance.fecha_emision:
            self.fields['fecha_emision'].initial = self.instance.fecha_emision.strftime('%d/%m/%Y')

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']


# Formularios de Proveedores (se mantienen, aunque Calibracion ya no use ProveedorCalibracionForm directamente)
# Considera eliminar estas clases si ya no usas ProveedorCalibracion, ProveedorMantenimiento, ProveedorComprobacion
# y solo usas el modelo general Proveedor.
# class ProveedorCalibracionForm(forms.ModelForm):
#     class Meta:
#         # Asegúrate de que ProveedorCalibracion existe o elimínalo
#         # model = ProveedorCalibracion
#         fields = '__all__'
#         # Widgets existentes...

# class ProveedorMantenimientoForm(forms.ModelForm):
#     class Meta:
#         # Asegúrate de que ProveedorMantenimiento existe o elimínalo
#         # model = ProveedorMantenimiento
#         fields = '__all__'
#         # Widgets existentes...

# class ProveedorComprobacionForm(forms.ModelForm):
#     class Meta:
#         # Asegúrate de que ProveedorComprobacion existe o elimínalo
#         # model = ProveedorComprobacion
#         fields = '__all__'
#         # Widgets existentes...

# NUEVO FORMULARIO: Proveedor General
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}),
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'form-input'}),
            'numero_contacto': forms.TextInput(attrs={'class': 'form-input'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-input'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-input'}),
            'pagina_web': forms.URLInput(attrs={'class': 'form-input'}),
            'alcance': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'servicio_prestado': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk:
                self.fields['empresa'].initial = self.request.user.empresa
            else:
                self.fields['empresa'].initial = self.instance.empresa
            self.fields['empresa'].required = False
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].required = True

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput):
                field.widget.attrs.update({'class': 'form-input-file'})

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']


# Formulario para Equipo
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

    class Meta:
        model = Equipo
        exclude = ('fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion')
        widgets = {
            'codigo_interno': forms.TextInput(attrs={'class': 'form-input'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'empresa': forms.Select(attrs={'class': 'form-select w-full'}),
            'tipo_equipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-input'}),
            'modelo': forms.TextInput(attrs={'class': 'form-input'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-input'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'rango_medida': forms.TextInput(attrs={'class': 'form-input'}),
            'resolucion': forms.TextInput(attrs={'class': 'form-input'}),
            'error_maximo_permisible': forms.TextInput(attrs={'class': 'form-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'archivo_compra_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'ficha_tecnica_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'manual_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'otros_documentos_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'imagen_equipo': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'version_formato': forms.TextInput(attrs={'class': 'form-input'}),
            'codificacion_formato': forms.TextInput(attrs={'class': 'form-input'}),
            'fecha_ultima_calibracion': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'fecha_ultimo_mantenimiento': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'fecha_ultima_comprobacion': forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
            'frecuencia_calibracion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
            'frecuencia_mantenimiento_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
            'frecuencia_comprobacion_meses': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
        }
        input_formats = {
            'fecha_ultima_calibracion': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'fecha_ultimo_mantenimiento': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'fecha_ultima_comprobacion': ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        }


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk:
                self.fields['empresa'].initial = self.request.user.empresa
            else:
                self.fields['empresa'].initial = self.instance.empresa
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.Select(attrs={'class': 'form-select w-full'})
            self.fields['empresa'].required = True

        if self.instance:
            if self.instance.fecha_ultima_calibracion:
                self.fields['fecha_ultima_calibracion'].initial = self.instance.fecha_ultima_calibracion.strftime('%d/%m/%Y')
            if self.instance.fecha_ultimo_mantenimiento:
                self.fields['fecha_ultimo_mantenimiento'].initial = self.instance.fecha_ultimo_mantenimiento.strftime('%d/%m/%Y')
            if self.instance.fecha_ultima_comprobacion:
                self.fields['fecha_ultima_comprobacion'].initial = self.instance.fecha_ultima_comprobacion.strftime('%d/%m/%Y')

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']

    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk:
                return self.instance.empresa
            elif self.request.user.empresa:
                return self.request.user.empresa
        return self.cleaned_data['empresa']

    def save(self, commit=True):
        # Antes de guardar, verificar el límite de equipos si se está creando uno nuevo
        if not self.instance.pk:
            # Obtener la empresa, ya sea del formulario (para superusuarios) o del usuario
            if self.request and not self.request.user.is_superuser:
                empresa = self.request.user.empresa
            else:
                empresa = self.cleaned_data.get('empresa')

            if empresa:
                equipos_actuales = Equipo.objects.filter(empresa=empresa).count()
                limite_equipos = empresa.limite_equipos

                if limite_equipos is not None and limite_equipos > 0:
                    if equipos_actuales >= limite_equipos:
                        raise forms.ValidationError(
                            f"Esta empresa ya ha alcanzado su límite de {limite_equipos} equipos. No se puede agregar más."
                        )
        
        # Después de la validación, guardar el objeto
        return super().save(commit)

# Formulario para Calibracion
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
            'proveedor': forms.Select(attrs={'class': 'form-select'}), # Añadir el widget para el nuevo campo proveedor
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'numero_certificado': forms.TextInput(attrs={'class': 'form-input'}),
            'documento_calibracion': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'confirmacion_metrologica_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}),
            'intervalos_calibracion_pdf': ClearableFileInput(attrs={'class': 'form-input-file'}), # Nuevo campo de documento
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_calibracion:
            self.fields['fecha_calibracion'].initial = self.instance.fecha_calibracion.strftime('%d/%m/%Y')
        # Filtrar proveedores por tipo de servicio "Calibración" o "Otro"
        self.fields['proveedor'].queryset = Proveedor.objects.filter(tipo_servicio__in=['Calibración', 'Otro'])


    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


# Formulario para Mantenimiento
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
            'proveedor': forms.Select(attrs={'class': 'form-select'}), # Añadir el widget para el nuevo campo proveedor
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}),
            'tipo_mantenimiento': forms.Select(attrs={'class': 'form-select'}),
            'costo': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_mantenimiento': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_mantenimiento:
            self.fields['fecha_mantenimiento'].initial = self.instance.fecha_mantenimiento.strftime('%d/%m/%Y')
        # Filtrar proveedores por tipo de servicio "Mantenimiento" o "Otro"
        self.fields['proveedor'].queryset = Proveedor.objects.filter(tipo_servicio__in=['Mantenimiento', 'Otro'])


    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

# Formulario para Comprobacion
class ComprobacionForm(forms.ModelForm):
    fecha_comprobacion = forms.DateField(
        label="Fecha de Comprobación",
        widget=forms.TextInput(attrs={'placeholder': 'DD/MM/YYYY', 'class': 'form-input'}),
        input_formats=['%d/%m/%Y', '%d-%m/%Y', '%Y-%m-%d']
    )

    class Meta:
        model = Comprobacion
        exclude = ('equipo',)
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}), # Añadir el widget para el nuevo campo proveedor
            'nombre_proveedor': forms.TextInput(attrs={'class': 'form-input'}),
            'responsable': forms.TextInput(attrs={'class': 'form-input'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_comprobacion': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_comprobacion:
            self.fields['fecha_comprobacion'].initial = self.instance.fecha_comprobacion.strftime('%d/%m/%Y')
        # Filtrar proveedores por tipo de servicio "Comprobación" o "Otro"
        self.fields['proveedor'].queryset = Proveedor.objects.filter(tipo_servicio__in=['Comprobación', 'Otro'])


    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

# Formulario para BajaEquipo
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
            'razon_baja': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'documento_baja': ClearableFileInput(attrs={'class': 'form-input-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.fecha_baja:
            if isinstance(self.instance.fecha_baja, datetime):
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.date().strftime('%d/%m/%Y')
            else:
                self.fields['fecha_baja'].initial = self.instance.fecha_baja.strftime('%d/%m/%Y')

# NUEVO FORMULARIO: Para la subida de archivos Excel
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Seleccionar archivo Excel",
        help_text="Sube un archivo .xlsx con el listado de equipos.",
        widget=forms.FileInput(attrs={'class': 'form-input-file'})
    )

# MODIFICADO: DocumentoForm para usar el modelo Documento
class DocumentoForm(forms.ModelForm):
    # Aquí ya no necesitamos el campo 'archivo' directamente, se manejará en la vista
    # y su ruta se guardará en 'archivo_s3_path' del modelo.
    
    class Meta:
        model = Documento
        # Solo incluimos los campos que el usuario introducirá o que serán llenados automáticamente por el formulario
        fields = ['nombre_archivo', 'descripcion', 'empresa']
        widgets = {
            # nombre_archivo se podría inferir, o hacerlo TextInput
            'nombre_archivo': forms.TextInput(attrs={'class': 'form-input'}), # Dejarlo editable para que el usuario pueda poner un nombre
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}), # Cambiado a Textarea
            'empresa': forms.Select(attrs={'class': 'form-select'}), # Permitir seleccionar empresa
            # 'archivo_s3_path' no se incluye aquí porque es llenado por la vista
            # 'subido_por' y 'fecha_subida' son auto-llenados por el modelo
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) # Recibir request para filtrar empresa
        super().__init__(*args, **kwargs)

        if self.request and not self.request.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if not self.instance.pk: # Si es una nueva instancia, establecer la empresa del usuario
                self.fields['empresa'].initial = self.request.user.empresa
            else: # Si se edita una existente, mantener la empresa actual
                self.fields['empresa'].initial = self.instance.empresa
            self.fields['empresa'].required = False
        elif self.request and self.request.user.is_superuser:
            self.fields['empresa'].queryset = Empresa.objects.all()
            self.fields['empresa'].required = True
        
        # Aplicar clases de Tailwind CSS a los campos visibles
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Textarea, forms.Select, forms.DateInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs.update({'class': 'form-input'})
            elif isinstance(field.widget, ClearableFileInput): # Aunque no hay FileInput directo, por si acaso
                field.widget.attrs.update({'class': 'form-input-file'})
            
    def clean_empresa(self):
        if self.request and not self.request.user.is_superuser:
            if self.instance and self.instance.pk: # Si ya existe, no permitir cambio
                return self.instance.empresa
            elif self.request.user.empresa: # Si es nuevo, asignar la empresa del usuario
                return self.request.user.empresa
        return self.cleaned_data.get('empresa') # Para superusuarios o si no se asignó automáticamente