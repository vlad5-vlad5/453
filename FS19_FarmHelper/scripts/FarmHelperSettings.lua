--
-- FarmHelperSettings
--
-- Загрузка/сохранение настроек мода в
--   <Мои документы>/My Games/FarmingSimulator2019/modSettings/FS19_FarmHelper.xml
--
-- Author: Your Name
--

FarmHelperSettings = {}

FarmHelperSettings.defaults = {
    hudVisible     = true,      -- показывать HUD при старте
    posX           = 0.012,     -- позиция панели (0..1 от ширины экрана)
    posY           = 0.62,      -- позиция панели (0..1 от высоты экрана)
    showWeather    = true,
    showFieldInfo  = true,
    textSize       = 0.016
}

local function getSettingsPath()
    -- getUserProfileAppPath() возвращает путь к .../My Games/FarmingSimulator2019/
    local dir = getUserProfileAppPath() .. "modSettings/"
    createFolder(dir)
    return dir .. "FS19_FarmHelper.xml"
end

function FarmHelperSettings.load()
    local settings = {}
    for k, v in pairs(FarmHelperSettings.defaults) do
        settings[k] = v
    end

    local path = getSettingsPath()
    if not fileExists(path) then
        return settings
    end

    local xml = loadXMLFile("FarmHelperSettings", path)
    if xml == nil or xml == 0 then
        return settings
    end

    settings.hudVisible    = Utils.getNoNil(getXMLBool(xml,  "farmHelper.hud#visible"),       settings.hudVisible)
    settings.posX          = Utils.getNoNil(getXMLFloat(xml, "farmHelper.hud#posX"),          settings.posX)
    settings.posY          = Utils.getNoNil(getXMLFloat(xml, "farmHelper.hud#posY"),          settings.posY)
    settings.textSize      = Utils.getNoNil(getXMLFloat(xml, "farmHelper.hud#textSize"),      settings.textSize)
    settings.showWeather   = Utils.getNoNil(getXMLBool(xml,  "farmHelper.hud#showWeather"),   settings.showWeather)
    settings.showFieldInfo = Utils.getNoNil(getXMLBool(xml,  "farmHelper.hud#showFieldInfo"), settings.showFieldInfo)

    delete(xml)

    return settings
end

function FarmHelperSettings.save(settings)
    local path = getSettingsPath()
    local xml = createXMLFile("FarmHelperSettings", path, "farmHelper")
    if xml == nil or xml == 0 then
        return false
    end

    setXMLBool(xml,  "farmHelper.hud#visible",       settings.hudVisible)
    setXMLFloat(xml, "farmHelper.hud#posX",          settings.posX)
    setXMLFloat(xml, "farmHelper.hud#posY",          settings.posY)
    setXMLFloat(xml, "farmHelper.hud#textSize",      settings.textSize)
    setXMLBool(xml,  "farmHelper.hud#showWeather",   settings.showWeather)
    setXMLBool(xml,  "farmHelper.hud#showFieldInfo", settings.showFieldInfo)

    saveXMLFile(xml)
    delete(xml)

    return true
end
