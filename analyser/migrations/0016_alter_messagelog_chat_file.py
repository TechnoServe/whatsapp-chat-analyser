# Generated by Django 3.2.5 on 2021-08-12 11:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0015_auto_20210811_0416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messagelog',
            name='chat_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_chat_file', to='analyser.whatsappchatfile'),
        ),
    ]
