# Generated by Django 3.1.3 on 2021-08-15 21:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_auto_20210804_2131'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupevent',
            name='event_details',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='groupevent',
            name='event_type',
            field=models.TextField(),
        ),
    ]
