# Generated by Django 3.2.5 on 2021-10-10 17:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0019_alter_personnel_designation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CounselorAdvisorAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('advisor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_a_user', to=settings.AUTH_USER_MODEL)),
                ('counselor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='r_c_user', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]