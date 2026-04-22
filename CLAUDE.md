# Графовые модели для анализа эффективности криптеров

> ВКР: Гильметдинов Т.И., группа 09-241, КФУ ИВМиИТ, 2026  
> Науч. рук.: Коннов И.В.

---

## О проекте

**Тема**: Графовые модели для анализа эффективности криптеров  
**Цель**: разработка послойной графовой модели (layered DAG) для формализации, анализа и оптимизации архитектуры криптеров бинарных PE-файлов под Windows x64.

Репозиторий состоит из двух крупных частей:
1. **`crypters/`** — экспериментальные криптеры на C++ (основной фокус сейчас)
2. **`app/`** — Python-приложение с GUI, визуализацией графа, базой эталонных решений и конструктором

---

## Архитектура проекта

```
coursework/
├── crypters/                  # C++ экспериментальные криптеры (x64 Windows PE)
│   ├── common/                # Общие утилиты: PE-парсер, таймеры, энтропия
│   │   ├── pe_reader.hpp
│   │   ├── profiler.hpp       # QueryPerformanceCounter-обёртка
│   │   └── entropy.hpp        # Формула Шеннона побайтово
│   ├── encryption/            # Модули шифрования (слой L2)
│   │   ├── xor_cipher.hpp/.cpp
│   │   ├── aes128_cbc.hpp/.cpp
│   │   └── aes256_cbc.hpp/.cpp
│   ├── compression/           # Модули компрессии (слой L3)
│   │   ├── no_compress.hpp
│   │   ├── lz4_compress.hpp/.cpp
│   │   └── lzma_compress.hpp/.cpp
│   ├── obfuscation/           # Обфускация stub-кода (слой L4)
│   │   ├── no_obf.hpp
│   │   ├── metamorphic.hpp/.cpp
│   │   ├── virtualization.hpp/.cpp
│   │   └── polymorphic.hpp/.cpp
│   ├── stub/                  # Генерация и внедрение stub (слой L5)
│   │   └── stub_builder.hpp/.cpp
│   ├── variants/              # Собранные варианты криптеров A/B/C/D
│   │   ├── crypter_a/         # XOR, без компрессии
│   │   ├── crypter_b/         # AES-256 CBC + LZMA
│   │   ├── crypter_c/         # AES-256 + метаморфика stub
│   │   └── crypter_d/         # XOR + AES-128, динамические ключи
│   ├── experiments/           # Скрипты профилирования и сбора метрик
│   │   └── run_experiments.ps1
│   └── CMakeLists.txt
│
├── app/                       # Python-приложение (PyQt5)
│   ├── main.py
│   ├── graph/                 # Графовая модель G=(V,E)
│   │   ├── model.py           # DAG, узлы, рёбра, метрики
│   │   ├── optimizer.py       # Алгоритм Дейкстры для DAG (мультикритерий)
│   │   └── visualizer.py      # NetworkX + Matplotlib рендер графа
│   ├── db/                    # База эталонных конфигураций
│   │   ├── schema.sql
│   │   ├── repository.py      # CRUD поверх SQLite
│   │   └── crypters.db        # SQLite-файл (120 конфигураций)
│   ├── builder/               # Модульный конструктор-сборщик
│   │   └── assembler.py
│   ├── ui/                    # PyQt5 виджеты
│   │   ├── main_window.py
│   │   ├── graph_widget.py
│   │   ├── config_form.py
│   │   └── results_panel.py
│   └── requirements.txt
│
├── data/                      # Экспериментальные данные, CSV с метриками
├── docs/                      # Документация, TeX/Word
└── CLAUDE.md
```

---

## Графовая модель (ключевая сущность)

Граф G = (V, E) — послойный DAG с K=6 слоями, 14 узлами, 35 рёбрами.

### Слои

| Слой | Назначение | Узлы |
|------|-----------|------|
| L1 | Чтение PE-файла | v_read |
| L2 | Шифрование | v_XOR, v_AES128, v_AES256 |
| L3 | Компрессия | v_nocomp, v_LZ4, v_LZMA |
| L4 | Обфускация stub | v_noobf, v_meta, v_virt, v_poly |
| L5 | Генерация stub + внедрение | v_stubgen |
| L6 | Выполнение результирующего файла | v_exec |

### Характеристики узла C(v) = {t(v), s(v), e(v), d(v)}

- **t(v)** — время выполнения алгоритма, мс (QueryPerformanceCounter, avg по 100 запускам)
- **s(v)** — криптостойкость [0.0–1.0]
- **e(v)** — энтропия выходных данных, бит/байт (формула Шеннона по байтам 0–255)
- **d(v)** — показатель обнаруживаемости [0.0–1.0] (VirusTotal: detected/total)

### Агрегированные метрики пути P = (v1..v6)

- T(P) = Σt(vk) + Σw(vk, vk+1)  — суммарное время
- S(P) = max s(v)                 — криптостойкость (самое слабое звено)
- E(P) = mean e(v)                — средняя энтропия
- D(P) = 1 − Π(1 − d(v))         — итоговая детектируемость

### Веса рёбер w(u, v)

Overhead в мс при переходе между алгоритмами смежных слоёв. Пример: w(AES256, LZMA) = 40 мс (зашифрованные данные плохо сжимаются), w(XOR, LZ4) = 3 мс.

---

## Экспериментальные криптеры (C++)

### Варианты

| Криптер | Шифрование | Компрессия | Обфускация stub | t (мс) | e (б/б) | s | d |
|---------|-----------|-----------|-----------------|--------|---------|---|---|
| A | XOR фикс. ключ | нет | нет | 12 | 4.2 | 0.2 | 0.85 |
| B | AES-256 CBC | LZMA | нет | 156 | 7.8 | 1.0 | 0.42 |
| C | AES-256 CBC | нет | метаморфика | 203 | 7.9 | 1.0 | 0.18 |
| D | XOR + AES-128 | нет | нет (дин. ключи) | 89 | 7.3 | 0.8 | 0.35 |

### Технические детали реализации

- **Платформа**: Windows x64 PE, MSVC / MinGW-w64
- **Сборка**: CMake 3.20+
- **Шифрование**: Windows CNG (BCryptEncrypt) или OpenSSL 3.x
- **Компрессия**: lz4 (статик), liblzma (статик)
- **Внедрение нагрузки**: resource section в stub-PE (RCDATA ресурс)
- **Профилирование**: QueryPerformanceCounter, усреднение по 100 запускам
- **Анализ энтропии**: Bintropy (внешний инструмент), блоки по 256 байт

### Соглашения по коду C++

- Стандарт: **C++17**
- Каждый модуль (шифрование / компрессия / обфускация) реализует единый интерфейс:
```cpp
// Пример интерфейса модуля (encryption/base.hpp)
struct EncryptionResult {
    std::vector<uint8_t> data;
    double time_ms;
    double entropy;
};

class IEncryption {
public:
    virtual EncryptionResult encrypt(std::span<const uint8_t> payload) = 0;
    virtual double cryptostrength() const = 0;  // s(v) [0.0–1.0]
    virtual ~IEncryption() = default;
};
```
- **Профилирование** оборачивать через `common/profiler.hpp`, не inline-замеры
- **Ключи** не хардкодить в тестовых образцах (передавать через аргументы / генерировать через BCryptGenRandom)
- Обфускация stub: код stub хранится отдельно в `stub/`, собирается как raw binary и потом встраивается через `bin2c`-подход или `.asm` инклюд
- Все экспериментальные замеры писать в `data/metrics_raw.csv` формата:
  `crypter_id,layer,algorithm,time_ms,entropy,strength,detectability`
- Никаких глобальных синглтонов — всё через RAII и передачу зависимостей

---

## Python-приложение (app/)

### Стек

- **Python 3.11+**
- **PyQt5** — GUI
- **NetworkX** — граф DAG
- **Matplotlib** — визуализация графа
- **SQLite3** (stdlib) — база эталонных конфигураций (120 записей)

### База данных SQLite — схема

```sql
CREATE TABLE configurations (
    id INTEGER PRIMARY KEY,
    enc_layer TEXT,          -- 'XOR'|'AES128'|'AES256'
    comp_layer TEXT,         -- 'nocomp'|'LZ4'|'LZMA'
    obf_layer TEXT,          -- 'noobf'|'meta'|'virt'|'poly'
    total_time_ms REAL,
    crypto_strength REAL,
    avg_entropy REAL,
    detectability REAL,
    validated INTEGER        -- 0/1, экспериментально подтверждено
);
```

### Алгоритм подбора конфигурации (optimizer.py)

Многоуровневая стратегия:
1. **Поиск в БД** по ограничениям R = {t_max, s_min, d_max}
2. **Модульная сборка** — модифицированный Дейкстра по DAG, O(|V|+|E|)
3. **Компромиссный выбор** — минимизация штрафной функции P(c) с весами приоритетов w1, w2, w3

### Соглашения по коду Python

- **PEP8** обязательно, форматтер `black`
- Типизация через `typing` / `dataclasses`
- Модули `graph/` не должны зависеть от `ui/` — только `ui/` импортирует из `graph/`
- Репозиторий БД изолирован в `db/repository.py`, никаких raw SQL в UI
- Все данные графовой модели при инициализации загружать из `graph/model.py`, не хардкодить в UI

---

## Текущий фокус разработки

**Сейчас делаем: экспериментальные криптеры (crypters/)**

Приоритет задач:
1. `crypters/common/` — pe_reader, profiler, entropy (фундамент для всего)
2. `crypters/encryption/` — xor_cipher, aes128, aes256 с единым интерфейсом
3. `crypters/compression/` — lz4 и lzma модули
4. `crypters/obfuscation/` — metamorphic (переименование регистров, junk-код)
5. `crypters/stub/` — stub_builder, resource-секция
6. `crypters/variants/` — сборка криптеров A, B, C, D
7. Эксперименты: сбор метрик в CSV, профилирование 100 итераций

---

## Сборка криптеров

```bash
# Windows, CMake + MSVC/MinGW
cd crypters
cmake -B build -DCMAKE_BUILD_TYPE=Release -A x64
cmake --build build --config Release

# Запуск конкретного варианта:
build/Release/crypter_a.exe <payload.exe> <output.exe>
```

Зависимости (vcpkg или ручная установка):
- `openssl` или Windows CNG (предпочтительно CNG, без зависимостей)
- `lz4`
- `liblzma`

---

## Запуск Python-приложения

```bash
cd app
pip install -r requirements.txt
python main.py
```

`requirements.txt`:
```
PyQt5>=5.15
networkx>=3.0
matplotlib>=3.7
```

---

## Важные ограничения и контекст

- Целевая платформа криптеров — **только Windows x64 PE**
- Все замеры производительности — только под Windows (QueryPerformanceCounter)
- Детектируемость (d) замеряется через **VirusTotal** вручную, результаты кладём в CSV
- Энтропия считается через **Bintropy** (внешний Python-инструмент) либо собственная реализация в `common/entropy.hpp`
- Проект **исследовательский** — код должен быть воспроизводимым и задокументированным, но не production-ready
- Модель содержит ровно **120 конфигураций** в базе (3 enc × 3 comp × 4 obf = 36 уникальных + валидированные подмножества)

---

## Метрики качества модели

- Точность прогноза времени: MAE ≤ ±4.2 мс (цель по ВКР)
- Точность прогноза детектируемости: MAE ≤ ±0.03 (цель по ВКР)
- Общая точность модели: ≥ 95%