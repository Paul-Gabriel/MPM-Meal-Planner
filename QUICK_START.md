# 🚀 QUICK START GUIDE - Funcționalități Noi

## 📦 Instalare Dependențe Noi

```bash
pip install -r requirements.txt
```

Aceasta va instala:
- `python-dotenv` - pentru gestionarea variabilelor de mediu
- `pytest-cov` - pentru test coverage

## 🔐 Configurare Environment Variables

1. **Copiază fișierul exemplu:**
```bash
copy .env.example .env
```

2. **Editează `.env` și adaugă API key-ul tău:**
```
SPOONACULAR_API_KEY=your_actual_api_key_here
```

3. **API key-ul va fi încărcat automat din `.env`**

## 💾 Backup Automat

### Creare Backup Manual
```bash
python -m meal.utilities.backup
```

### Programare Backup în Python
```python
from meal.utilities.backup import BackupManager
from meal.infra.paths import DATA_DIR

manager = BackupManager(DATA_DIR)

# Backup toate fișierele
results = manager.backup_all()

# Backup un singur fișier
manager.create_backup("recipes.json")

# Listare backup-uri
backups = manager.list_backups("recipes.json")
for backup in backups:
    print(f"{backup['name']} - {backup['created']}")

# Restaurare backup
manager.restore_backup("recipes_20250118_143022.json")
```

## 📤 Export/Import Date

### Export Rețete (JSON)
```bash
python -m meal.utilities.export_import export --type recipes --file my_recipes.json
```

### Export Pantry (CSV pentru Excel)
```bash
python -m meal.utilities.export_import export --type pantry --format csv
```

### Export Tot (ZIP Archive)
```bash
python -m meal.utilities.export_import export --type all --format zip --file backup.zip
```

### Import Rețete (cu merge)
```bash
python -m meal.utilities.export_import import --file my_recipes.json --merge
```

### Import din ZIP
```bash
python -m meal.utilities.export_import import --file backup.zip
```

### Folosire în Python
```python
from meal.utilities.export_import import DataExporter, DataImporter
from meal.infra.paths import DATA_DIR

# Export
exporter = DataExporter(DATA_DIR)
exporter.export_recipes()
exporter.export_pantry()
exporter.export_all()  # ZIP cu tot
exporter.export_to_csv("recipes")  # CSV pentru Excel

# Import
importer = DataImporter(DATA_DIR)
importer.import_recipes(Path("my_recipes.json"), merge=True)
importer.import_from_zip(Path("backup.zip"))
```

## 📊 Statistici și Rapoarte

### Generare Raport Complet
```bash
python -m meal.utilities.statistics
```

Acest raport include:
- ✅ Top 10 rețete cele mai gătite
- ✅ Frecvența gătirii pe zile (Luni, Marți, etc.)
- ✅ Medii nutriționale (ultimele 4 săptămâni)
- ✅ Distribuția tag-urilor pentru rețete
- ✅ Scor diversitate meselor (0-100)
- ✅ Statistici pantry (greutate, volum, valoare estimată)
- ✅ Rețete nefolosite niciodată

### Folosire în Python
```python
from meal.utilities.statistics import MealPlannerStats
from meal.infra.paths import DATA_DIR

stats = MealPlannerStats(DATA_DIR)

# Top rețete
top_recipes = stats.most_cooked_recipes(10)
print(top_recipes)

# Frecvență pe zile
cooking_days = stats.cooking_frequency_by_day()
print(cooking_days)

# Nutriție medie
nutrition = stats.average_nutrition_per_week(weeks=4)
print(f"Calorii/zi: {nutrition['calories_per_day']}")

# Scor diversitate
diversity = stats.meal_diversity_score(weeks=4)
print(f"Diversitate: {diversity}/100")

# Rețete neutilizate
unused = stats.unused_recipes()
print(f"Rețete neutilizate: {len(unused)}")

# Raport complet
report = stats.generate_report()
```

## ✅ Validare Input cu Pydantic

Noile schema-uri asigură date valide:

```python
from meal.utilities.validators import RecipeInput, IngredientInput

# Validare automată
try:
    recipe = RecipeInput(
        name="Pasta Carbonara",
        servings=4,
        ingredients=[
            IngredientInput(
                name="Spaghetti",
                unit="g",
                default_quantity=400
            )
        ]
    )
    print("✓ Date valide")
except ValidationError as e:
    print(f"✗ Eroare: {e}")
```

## 🔧 Îmbunătățiri în Cod

### 1. Error Handling Îmbunătățit
```python
# meal/infra/Recipe_Repository.py acum returnează [] în loc să crash-uiască
recipes = reading_from_recipes()  # Sigur, nu va da eroare
```

### 2. Validare Cantități
```python
# meal/domain/Pantry.py acum validează cantități negative
pantry.update_quantity("Salt", -5)  # Raises ValueError
```

### 3. Configurare Centralizată
```python
# Folosește meal/utilities/config.py pentru toate setările
from meal.utilities.config import (
    SPOONACULAR_API_KEY,
    DAYS_BEFORE_EXPIRY,
    LOW_STOCK_THRESHOLD
)
```

## 📝 Teste

### Rulare Toate Testele
```bash
pytest meal/tests/ -v
```

### Test Coverage
```bash
pytest --cov=meal --cov-report=html
```

Apoi deschide `htmlcov/index.html` în browser pentru a vedea coverage-ul detaliat.

## 🎯 Recomandări de Utilizare

### Workflow Zilnic
1. **Dimineața**: Verifică lista de cumpărături pentru ziua curentă
2. **După cumpărături**: Actualizează pantry-ul cu ingredientele noi
3. **După gătit**: Marchează rețeta ca "cooked" în plan
4. **Săptămânal**: Generează raport statistici pentru a vedea progresul

### Workflow Săptămânal
1. **Duminica**: Planifică mesele pentru săptămâna următoare
2. **Luni dimineața**: Generează lista de cumpărături
3. **Vineri seara**: Creează backup automat al datelor
4. **Weekend**: Exportă rețetele tale favorite

### Backup Schedule Recomandat
```python
# Rulează automat în cron/task scheduler
from meal.utilities.backup import auto_backup

# În fiecare vineri la 18:00
auto_backup()
```

## 🐛 Depanare

### Problema: API Key nu funcționează
**Soluție**: Verifică că `.env` există și conține cheia corectă:
```bash
type .env
```

### Problema: Import eșuează
**Soluție**: Verifică formatul JSON:
```bash
python -m json.tool my_recipes.json
```

### Problema: Statistici nu arată date
**Soluție**: Asigură-te că ai rețete gătite în `Pantry_recipe_cooked.json`

## 📚 Documentație Completă

Pentru detalii complete despre toate îmbunătățirile, vezi:
- `IMPROVEMENTS.md` - Lista completă de sugestii
- `README.md` - Documentație generală
- Comentarii inline în fiecare modul nou

## 🆘 Suport

Pentru probleme sau întrebări:
1. Verifică log-urile în `logs/meal_planner.log` (după configurare)
2. Rulează testele pentru a identifica probleme
3. Consultă documentația inline în cod

---

**Îmbunătățiri implementate cu succes! 🎉**

