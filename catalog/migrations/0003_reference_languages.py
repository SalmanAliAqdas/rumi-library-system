from django.db import migrations


def add_languages(apps, schema_editor):
    language = apps.get_model("catalog", "Language")
    for code, name in [("en", "English"), ("ur", "اردو"), ("ar", "العربية")]:
        language.objects.using(schema_editor.connection.alias).get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_submission")]
    operations = [migrations.RunPython(add_languages, migrations.RunPython.noop)]
