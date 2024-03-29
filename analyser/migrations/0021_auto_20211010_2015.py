# Generated by Django 3.2.5 on 2021-10-10 17:15

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0020_counseloradvisorassignment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='counseloradvisorassignment',
            name='advisor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_advisor_counselor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='counseloradvisorassignment',
            name='counselor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_counselor_advisor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='AdvisorManagerAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('advisor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_advisor_manage', to=settings.AUTH_USER_MODEL)),
                ('manager', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_manager_advisor', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
