# Generated by Django 3.2.5 on 2021-08-10 07:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analyser', '0012_auto_20210810_1015'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='groupdailystats',
            name='no_emojis',
        ),
        migrations.RemoveField(
            model_name='userdailystats',
            name='no_emojis',
        ),
        migrations.AddField(
            model_name='userdailystats',
            name='chat_file',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='analyser.whatsappchatfile'),
            preserve_default=False,
        ),
    ]
