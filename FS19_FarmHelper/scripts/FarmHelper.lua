--
-- FarmHelper
--
-- Простой HUD-помощник для Farming Simulator 19.
-- Показывает: баланс фермы, игровое время/день, погоду и данные поля под игроком.
--
-- Точка входа: addModEventListener(FarmHelper) в конце файла.
-- Игра сама вызывает loadMap / update / draw / keyEvent / mouseEvent / deleteMap.
--
-- Author: Your Name
--

FarmHelper = {}
FarmHelper.name = "FS19_FarmHelper"
FarmHelper.dir  = g_currentModDirectory

-- как часто пересчитывать данные (мс). Каждый кадр считать поле — дорого.
FarmHelper.REFRESH_INTERVAL = 500

FarmHelper.settings   = nil
FarmHelper.isReady    = false
FarmHelper.timer      = 0
FarmHelper.eventId    = nil

-- кэш выводимых данных
FarmHelper.data = {
    money     = 0,
    timeText  = "--:--",
    dayText   = "",
    weather   = "",
    temp      = nil,
    fieldId   = nil,
    fieldArea = 0
}

-- ============================================================
-- Хелперы
-- ============================================================

local function log(...)
    print(string.format("[FarmHelper] %s", table.concat({...}, " ")))
end

--- Мировые координаты игрока или управляемой техники
local function getPlayerWorldPosition()
    local mission = g_currentMission
    if mission == nil then
        return nil
    end

    local node = nil

    if mission.controlledVehicle ~= nil and mission.controlledVehicle.rootNode ~= nil then
        node = mission.controlledVehicle.rootNode
    elseif mission.player ~= nil and mission.player.rootNode ~= nil then
        node = mission.player.rootNode
    end

    if node == nil or not entityExists(node) then
        return nil
    end

    return getWorldTranslation(node)
end

--- Название текущей погоды через локализацию игры
local function getWeatherName()
    local env = g_currentMission ~= nil and g_currentMission.environment or nil
    if env == nil or env.weather == nil then
        return nil, nil
    end

    local weatherType = env.weather:getCurrentWeatherType()
    local names = {
        [WeatherType.SUN]    = "ui_weatherSun",
        [WeatherType.RAIN]   = "ui_weatherRain",
        [WeatherType.CLOUDY] = "ui_weatherCloudy",
        [WeatherType.SNOW]   = "ui_weatherSnow"
    }

    local key  = names[weatherType]
    local name = key ~= nil and g_i18n:getText(key) or "-"
    local temp = nil

    if env.weather.getCurrentTemperature ~= nil then
        temp = env.weather:getCurrentTemperature()
    end

    return name, temp
end

-- ============================================================
-- Управление (клавиша)
-- ============================================================

function FarmHelper:registerInput()
    if self.eventId ~= nil then
        return
    end

    local success, eventId = g_inputBinding:registerActionEvent(
        InputAction.FARMHELPER_TOGGLE, -- действие из modDesc.xml
        self,                          -- target
        FarmHelper.onToggleHud,        -- callback
        false,                         -- triggerUp
        true,                          -- triggerDown
        false,                         -- triggerAlways
        true                           -- startActive
    )

    if success then
        self.eventId = eventId
        g_inputBinding:setActionEventText(eventId, g_i18n:getText("fh_toggleHud"))
        g_inputBinding:setActionEventTextVisibility(eventId, false) -- не засорять подсказки
    else
        log("не удалось зарегистрировать действие FARMHELPER_TOGGLE")
    end
end

function FarmHelper:onToggleHud()
    self.settings.hudVisible = not self.settings.hudVisible
    FarmHelperSettings.save(self.settings)

    local key = self.settings.hudVisible and "fh_hudOn" or "fh_hudOff"
    if g_currentMission ~= nil and g_currentMission.hud ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 1500)
    end
end

-- ============================================================
-- Жизненный цикл мода
-- ============================================================

function FarmHelper:loadMap(name)
    self.settings = FarmHelperSettings.load()
    self:registerInput()
    self.isReady = true

    log("загружен, версия 1.0.0.0")
end

function FarmHelper:deleteMap()
    if self.settings ~= nil then
        FarmHelperSettings.save(self.settings)
    end

    self.isReady = false
    self.eventId = nil
end

function FarmHelper:mouseEvent(posX, posY, isDown, isUp, button)
end

function FarmHelper:keyEvent(unicode, sym, modifier, isDown)
end

function FarmHelper:update(dt)
    if not self.isReady or not self.settings.hudVisible then
        return
    end

    self.timer = self.timer + dt
    if self.timer < FarmHelper.REFRESH_INTERVAL then
        return
    end
    self.timer = 0

    self:refreshData()
end

function FarmHelper:refreshData()
    local mission = g_currentMission
    if mission == nil then
        return
    end

    local d = self.data

    -- деньги активной фермы
    local farmId = mission:getFarmId()
    local farm   = g_farmManager ~= nil and g_farmManager:getFarmById(farmId) or nil
    d.money = farm ~= nil and farm.money or 0

    -- время и день
    local env = mission.environment
    if env ~= nil then
        local hours   = math.floor(env.dayTime / (60 * 60 * 1000))
        local minutes = math.floor((env.dayTime - hours * 60 * 60 * 1000) / (60 * 1000))
        d.timeText = string.format("%02d:%02d", hours, minutes)
        d.dayText  = string.format("%s %d", g_i18n:getText("ui_day"), env.currentDay or 0)
    end

    -- погода
    if self.settings.showWeather then
        d.weather, d.temp = getWeatherName()
    end

    -- поле под игроком
    d.fieldId   = nil
    d.fieldArea = 0

    if self.settings.showFieldInfo and g_fieldManager ~= nil then
        local x, _, z = getPlayerWorldPosition()
        if x ~= nil then
            local field = g_fieldManager:getFieldAtWorldPosition(x, z)
            if field ~= nil then
                d.fieldId   = field.fieldId
                d.fieldArea = field.fieldArea or 0
            end
        end
    end
end

-- ============================================================
-- Отрисовка HUD
-- ============================================================

function FarmHelper:draw()
    if not self.isReady or not self.settings.hudVisible then
        return
    end
    if g_currentMission == nil or g_gui:getIsGuiVisible() then
        return
    end

    local s    = self.settings
    local d    = self.data
    local size = s.textSize
    local x    = s.posX
    local y    = s.posY
    local step = size * 1.35

    setTextBold(false)
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextVerticalAlignment(RenderText.VERTICAL_ALIGN_BASELINE)

    local lines = {}

    table.insert(lines, {
        text  = g_i18n:formatMoney(d.money, 0, true, true),
        color = d.money < 0 and {1, 0.3, 0.3, 1} or {0.6, 1, 0.6, 1}
    })

    table.insert(lines, {
        text  = string.format("%s  %s", d.timeText, d.dayText),
        color = {1, 1, 1, 1}
    })

    if s.showWeather and d.weather ~= nil then
        local text = d.weather
        if d.temp ~= nil then
            text = string.format("%s  %d\194\176C", d.weather, math.floor(d.temp + 0.5))
        end
        table.insert(lines, { text = text, color = {0.85, 0.9, 1, 1} })
    end

    if s.showFieldInfo then
        local text
        if d.fieldId ~= nil then
            text = string.format("%s %d  -  %s",
                g_i18n:getText("fh_field"), d.fieldId, g_i18n:formatArea(d.fieldArea, 2))
        else
            text = g_i18n:getText("fh_noField")
        end
        table.insert(lines, { text = text, color = {1, 0.95, 0.7, 1} })
    end

    -- заголовок
    setTextBold(true)
    setTextColor(1, 1, 1, 1)
    renderText(x, y, size * 1.05, g_i18n:getText("fh_title"))
    setTextBold(false)

    for i, line in ipairs(lines) do
        local c = line.color
        setTextColor(c[1], c[2], c[3], c[4])
        renderText(x, y - step * i, size, line.text)
    end

    -- сброс состояния текста, иначе поедет остальной UI игры
    setTextColor(1, 1, 1, 1)
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextBold(false)
end

addModEventListener(FarmHelper)
