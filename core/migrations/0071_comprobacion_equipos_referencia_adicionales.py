from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_empresa_stats_dashboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='comprobacion',
            name='equipos_referencia_adicionales',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Lista de equipos de referencia adicionales (nombre, marca, modelo, certificado)',
                verbose_name='Equipos de Referencia Adicionales',
            ),
        ),
    ]
