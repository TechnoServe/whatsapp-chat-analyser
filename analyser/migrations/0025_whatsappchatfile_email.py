# Generated by Django 3.2.5 on 2023-08-14 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0024_rename_counseloradvisorgroup_counselorgroupassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappchatfile',
            name='email',
            field=models.EmailField(blank=True, max_length=200, null=True),
        ),
    ]
