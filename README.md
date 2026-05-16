# js-arch-collector

**Инструмент для автоматического архитектурного анализа больших JavaScript-файлов.**

Быстро извлекает структуру кода, глобальное состояние, логические группы функций и точки входа, генерируя чистый отчёт, оптимизированный для работы с LLM.

---

### Возможности

- AST-анализ через `esprima`
- Выявление и классификация mutable state
- Автоматическая семантическая группировка функций
- Поиск точек входа и инициализации
- Генерация структурированного Markdown-отчёта

---

### 🎯 Идеальный результат анализа (эталон)

# JS Architecture Analysis: `app.js`

**Generated:** 2026-05-16 08:15 | Size: 46 KB | Functions: 15

## Module System
- **Type**: Global Script (IIFE + `window.App`)
- **Bundler**: Not detected
- **ES6 Imports**: No
- **CommonJS**: Yes (`module.exports`)

## Global State & Data Structures

| Variable           | Type       | Mutations | Global | Description                  |
|--------------------|------------|-----------|--------|------------------------------|
| `selectedRoofs`    | array      | **3**     | ✅     | Основной массив объектов     |
| `userFavorites`    | array      | **3**     | ✅     | Избранное пользователя       |
| `currentFilters`   | object     | **2**     | ✅     | Фильтры поиска               |
| `renderedCount`    | number     | **2**     | ✅     | Счётчик отрендеренных элементов |
| `mapInstance`      | instance   | **1**     | ✅     | Экземпляр карты              |

## Function Groups

### UI/Events (6 functions)
- `bindEvents()`
- `toggleFavorite(roofId)`
- `resetFilters()`
- `recalcRenderedCount()`
- `userFavorites.filter_callback_0(id)`
- `roofs.filter_callback_0(r)`

### Map/Geo (4 functions)
- `initMap()`
- `applyLoc(location)`
- `onChunk(data)`
- `clientFilter(roofs)`

### Data/API (2 functions)
- `scheduleLoad()`
- ...

### Init/Boot (2 functions)
- `init()`
- `initModule()`

### Utils (2 functions)
- `getState()`
- `debouncedSearch(query)`

## Entry Points & Lifecycle
- `DOMContentLoaded` → `init()`
- `IIFE` → `initModule`
- Global exposure → `window.App`
________________________________________
Установка

git clone https://github.com/VladMazoff/js-arch-collector.git
cd js-arch-collector
pip install -r requirements.txt

Использование
Анализ одного файла:    python main.py --file examples/app.js

Анализ папки:    python main.py --dir src/
________________________________________
Roadmap
•	Базовый AST-парсер и отчёт
•	Call Graph (дерево вызовов функций)
•	Улучшенный детектор модульной системы и бандлеров
•	Data Flow Analysis
•	Метрики сложности
•	Поддержка TypeScript
•	Анализ нескольких файлов + общий проектный отчёт
________________________________________
Для кого этот инструмент
•	Разработчики, занимающиеся рефакторингом legacy JavaScript-кода
•	Архитекторы frontend-приложений
•	AI-ассистенты (LLM), которым нужен качественный структурный контекст вместо сырого кода

