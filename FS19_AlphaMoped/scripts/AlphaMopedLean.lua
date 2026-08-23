--
-- AlphaMopedLean
--
-- Специализация FS19: наклоняет корпус мопеда в поворотах.
-- Чисто визуальный эффект — на физику не влияет, поэтому безопасен
-- в мультиплеере и не ломает управление.
--
-- Подключается через modDesc.xml:
--   <specialization name="alphaMopedLean" className="AlphaMopedLean"
--                   filename="scripts/AlphaMopedLean.lua"/>
--
-- Настройки в alphaMoped.xml:
--   <alphaMopedLean node="bodyLean" maxAngle="22" speedFactor="0.055" smoothing="3.5"/>
--
--   node        — узел, который крутим (родитель всей косметики мопеда)
--   maxAngle    — максимальный крен в градусах
--   speedFactor — при какой скорости крен выходит на максимум (1 / км/ч)
--   smoothing   — скорость сглаживания, больше = резче
--

AlphaMopedLean = {}

AlphaMopedLean.MOD_NAME  = g_currentModName
AlphaMopedLean.SPEC_NAME = string.format("spec_%s.alphaMopedLean", g_currentModName)

--- Имя spec-таблицы зависит от того, как игра зарегистрировала специализацию.
--  Проверяем оба варианта, чтобы не гадать.
function AlphaMopedLean.getSpec(self)
    return self[AlphaMopedLean.SPEC_NAME] or self["spec_alphaMopedLean"]
end

function AlphaMopedLean.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(Drivable, specializations)
        and SpecializationUtil.hasSpecialization(Wheels, specializations)
end

function AlphaMopedLean.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad",       AlphaMopedLean)
    SpecializationUtil.registerEventListener(vehicleType, "onDelete",     AlphaMopedLean)
    SpecializationUtil.registerEventListener(vehicleType, "onUpdateTick", AlphaMopedLean)
end

function AlphaMopedLean:onLoad(savegame)
    local spec = AlphaMopedLean.getSpec(self)
    local key  = "vehicle.alphaMopedLean"
    if spec == nil then
        print("[AlphaMoped] spec-таблица не найдена, наклон отключён")
        return
    end

    spec.node = nil
    spec.currentAngle = 0

    local nodeStr = getXMLString(self.xmlFile, key .. "#node")
    if nodeStr ~= nil then
        spec.node = I3DUtil.indexToObject(self.components, nodeStr, self.i3dMappings)
    end

    if spec.node == nil then
        print(string.format("[AlphaMoped] Warning: узел наклона не найден (%s#node). Наклон отключён.", key))
        return
    end

    spec.maxAngle    = math.rad(Utils.getNoNil(getXMLFloat(self.xmlFile, key .. "#maxAngle"),    20))
    spec.speedFactor = Utils.getNoNil(getXMLFloat(self.xmlFile, key .. "#speedFactor"), 0.05)
    spec.smoothing   = Utils.getNoNil(getXMLFloat(self.xmlFile, key .. "#smoothing"),   3.5)

    -- запоминаем исходный поворот, чтобы крен складывался с ним, а не затирал
    local rx, ry, rz = getRotation(spec.node)
    spec.baseRotation = { rx, ry, rz }
end

function AlphaMopedLean:onDelete()
    local spec = AlphaMopedLean.getSpec(self)

    if spec ~= nil and spec.node ~= nil and entityExists(spec.node) and spec.baseRotation ~= nil then
        setRotation(spec.node, spec.baseRotation[1], spec.baseRotation[2], spec.baseRotation[3])
    end
end

function AlphaMopedLean:onUpdateTick(dt, isActiveForInput, isActiveForInputIgnoreSelection, isSelected)
    local spec = AlphaMopedLean.getSpec(self)
    if spec == nil or spec.node == nil then
        return
    end

    local targetAngle = 0

    -- self.rotatedTime лежит в диапазоне [-maxRotTime; maxRotTime] и отражает поворот руля
    local maxRotTime = self.maxRotTime
    if maxRotTime ~= nil and maxRotTime > 0 and self.rotatedTime ~= nil then
        local steer = math.max(-1, math.min(1, self.rotatedTime / maxRotTime))

        -- крен растёт со скоростью: на месте мопед стоит ровно
        local speedKmh    = math.abs((self.lastSpeedReal or 0) * 3600)
        local speedRatio  = math.max(0, math.min(1, speedKmh * spec.speedFactor))

        -- знак: наклоняемся внутрь поворота. Если в игре кренит наружу — поменяйте знак.
        targetAngle = -steer * speedRatio * spec.maxAngle
    end

    -- экспоненциальное сглаживание, независимое от FPS
    local alpha = math.min(1, (dt / 1000) * spec.smoothing)
    spec.currentAngle = spec.currentAngle + (targetAngle - spec.currentAngle) * alpha

    -- крен = вращение вокруг продольной оси (Z в системе координат GIANTS)
    setRotation(spec.node,
        spec.baseRotation[1],
        spec.baseRotation[2],
        spec.baseRotation[3] + spec.currentAngle)
end
