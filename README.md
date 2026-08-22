# FS19_FarmHelper — каркас скриптового мода для Farming Simulator 19

Рабочий пример мода на Lua для FS19: HUD-панель с балансом фермы, игровым временем,
погодой и информацией о поле, на котором вы стоите. Сделан как **шаблон**, от которого
удобно отталкиваться при создании своего мода.

## Что внутри

```
FS19_FarmHelper/
├── modDesc.xml                  # манифест мода (descVersion="53" — это FS19)
├── icon_FarmHelper.dds          # иконка мода 256x256
├── icon_FarmHelper.png          # исходник иконки
├── scripts/
│   ├── FarmHelper.lua           # основная логика: loadMap / update / draw
│   └── FarmHelperSettings.lua   # чтение и запись настроек в modSettings
└── translations/
    ├── translation_en.xml
    └── translation_ru.xml
build.sh                         # проверка XML/Lua + сборка zip (+ install)
```

## Сборка и установка

```bash
./build.sh            # -> build/FS19_FarmHelper.zip
./build.sh install    # то же + копирование в папку модов, если она найдена
```

Вручную: заархивируйте **содержимое** папки `FS19_FarmHelper` (чтобы `modDesc.xml`
лежал в корне архива) в файл `FS19_FarmHelper.zip` и положите его в

```
Документы\My Games\FarmingSimulator2019\mods\
```

Имя zip-файла обязано совпадать с именем мода и не содержать пробелов.

## Как пользоваться

Клавиша по умолчанию: **Right Ctrl + H** — включить/выключить HUD.
Переназначается в игре: *Настройки → Управление → Farm Helper*.

Настройки сохраняются в
`Документы\My Games\FarmingSimulator2019\modSettings\FS19_FarmHelper.xml`:

```xml
<farmHelper>
    <hud visible="true" posX="0.012" posY="0.62" textSize="0.016"
         showWeather="true" showFieldInfo="true"/>
</farmHelper>
```

## Разработка

**Инструменты**

| Что | Чем |
|---|---|
| Скрипты | GIANTS Studio (есть отладчик Lua) или VS Code + Lua-плагин |
| 3D-модели, карты | GIANTS Editor (входит в GIANTS Editor & Studio SDK) |
| Документация API | GDN → Scripting Documentation FS19 |

**Полезные аргументы запуска игры** (свойства ярлыка):

```
-cheats -autoStartSavegameId 1
```

Быстрый старт в сохранение №1 плюс консоль разработчика (`~`). Обратите внимание:
**Lua в FS19 не перезагружается на лету** — после правки скрипта игру нужно перезапустить.

**Лог игры** (первое место, куда смотреть при ошибке):

```
Документы\My Games\FarmingSimulator2019\log.txt
```

Все `print()` из мода попадают именно туда.

**Тестирование без сборки zip**: положите распакованную папку `FS19_FarmHelper`
прямо в `mods\` — игра подхватывает и папки тоже, это удобнее при отладке.

## Ключевые точки расширения

- `FarmHelper:loadMap()` — инициализация после загрузки карты.
- `FarmHelper:update(dt)` — логика каждый кадр (тут стоит троттлинг на 500 мс).
- `FarmHelper:draw()` — отрисовка HUD через `renderText`.
- `FarmHelperSettings` — шаблон хранения настроек, переиспользуется как есть.
- `modDesc.xml` → `<actions>` / `<inputBinding>` — добавление своих клавиш.

Чтобы сделать мод техники вместо HUD-мода, добавьте в `modDesc.xml` секцию
`<specializations>` со своей специализацией и подключите её к `vehicleType`.

## Замечания по иконке

`icon_FarmHelper.dds` сохранён как несжатый RGBA 256×256. Игра его читает, но
для магазина каноничнее DXT5. Пересобрать можно, например, плагином Intel Texture
Works для Photoshop, через GIMP или `texconv -f BC3_UNORM icon_FarmHelper.png`.
