# Generated by Django 3.1.3 on 2021-08-15 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatgroup', '0003_auto_20210815_1841'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatgroup',
            name='name',
            field=models.TextField(unique=True, verbose_name='chat_group_name'),
        ),
    ]
