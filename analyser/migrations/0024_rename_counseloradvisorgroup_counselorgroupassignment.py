# Generated by Django 3.2.5 on 2021-11-26 20:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0023_counseloradvisorgroup'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CounselorAdvisorGroup',
            new_name='CounselorGroupAssignment',
        ),
    ]
