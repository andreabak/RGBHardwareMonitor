#include "lights.h"


float randFloat() {
    return random(512) / 511.0;
}

float mixValues(float firstValue, float secondValue, float strength) {
    return (1.0 - strength) * firstValue + strength * secondValue;
}

RingLights::RingLights(uint16_t _stripPin, uint16_t _numLEDs, neoPixelType stripType=DEFAULT_STRIP_TYPE) {
    stripPin = _stripPin;
    numLEDs = _numLEDs;
    ringPixels = new Color[numLEDs];
    ringFlameForce = new float[numLEDs];
    strip = new Adafruit_NeoPixel(numLEDs, stripPin, stripType);
    // TODO: Apply max 32 somewhere on the divisor so to obtain semi-fixed-length repeat
    period = max(8, min(32, numLEDs)) / 2;
    initRing();
}

void RingLights::initRing() {
    for (uint16_t i=0; i<numLEDs; i++)
        ringFlameForce[i] = 0.0;

    for (uint16_t i=0; i<numLEDs; i++)
        ringPixels[i].set(0.0, 0.0, 0.0);

    heat = settingHeat;
    load = settingLoad;
    rpm = settingRpm;

    strip->begin();
    strip->show();
    strip->setBrightness(255);

    updateIdle();
    displayRing();
}

void RingLights::mixFlame(Color& outColor, Color& idleColor, float flameForce, float heat, float dim=1.0) {
    // flameForce 0.0-200.0
    if (!flameForce)
        return;
    flameForce = dim * (0.5 + 0.5 * heat) * (100.0 - abs(flameForce - 100.0)) / 100.0;
    Color flameColor = Color::fromMix(idleColor, ringFlameHotColor, (1.0 - invHeat*invHeat));
    outColor.mixWith(flameColor, flameForce);
}

// TODO: Consider making this function signature a generic interface for more effects (per pixel calculation?)
Color RingLights::makeIdle(float pos, float offset=0.0) {
    return Color::fromHSV(fmod((pos + offset) / numLEDs, 1.0), 1.0, 1.0);
}

void RingLights::mixIdle(Color& outColor, float pos, float offset=0.0, float mixStrength=1.0) {
    if (!mixStrength)
        return;
    Color idleColor = makeIdle(pos, offset);
    outColor.mixWith(idleColor, mixStrength);
}

void RingLights::mixDim(Color& outColor, float pos, float offset=0.0, float mixStrength=1.0) {
//    float baseDim = fabs(((fmod(pos + offset, period)) - (period / 2)) / float(period / 2));
    float baseDim = (1.0 + cos(2.0 * PI * (pos + offset) / period)) / 2.0;
    if (baseDim) {
        baseDim *= (1.0 - 0.125 * randFloat());
        outColor.mixWith(ringBaseColor, baseDim * mixStrength);
    }
}

void RingLights::displayRing() {
    for (uint16_t i=0; i<numLEDs; i++) {
        // Get actual decimal offset based on rotation for current position
        Color mix;
        if (idleDynamic)
            mix = makeIdle(i, ringOffset);
        else {
            float oi = i + ringOffset;
            float pixOffset = oi - int(oi);
            uint16_t srcPix0 = uint16_t(oi) % numLEDs;
            // Mix colors from offsets to create actual output base color
            mix = Color(ringPixels[srcPix0]);
            if (pixOffset) {
                uint16_t srcPix1 = (uint16_t(oi)+1) % numLEDs;
                mix.mixWith(ringPixels[srcPix1], pixOffset);
            }
        }
        Color flameCoolColor = Color(mix);
        flameCoolColor *= 2.0;
        // Apply idle brightness
        mix *= mixValues(idleBrightness, 1.0, load);
        // Apply hot color
        mix.mixWith(ringHotColor, heat);
        // Mix flame effect
        if (ringFlameForce[i])
            mixFlame(mix, flameCoolColor, ringFlameForce[i], heat, 1.0 - (0.75 * randFloat() * load*load));
        // Dim based on rotation speed
        mixDim(mix, i, ringOffset * dimSpeedup, 1.0*rpm);
        // Global brightness
        if (ringBrightness != 1.0)
            mix *= ringBrightness;
        // Value clipping
        uint8_t r = max(0.0, min(255.0, mix.r));
        uint8_t g = max(0.0, min(255.0, mix.g));
        uint8_t b = max(0.0, min(255.0, mix.b));
        // Gamma and set
        strip->setPixelColor(i, strip->gamma32(strip->Color(r, g, b)));
    }
    strip->show();
}

void RingLights::updateContext() {
    invSmooth = 1.0 / settingSmoothing;
    heat = mixValues(heat, settingHeat, invSmooth);
    load = mixValues(load, settingLoad, invSmooth);
    rpm = mixValues(rpm, settingRpm, invSmooth);
    
    invHeat = 1.0 - heat;
    invLoad = 1.0 - load;
    invRpm = 1.0 - rpm;
    rotation = (rotationBaseSpeed / fpsAvg) * rpm*rpm;
    entropy = 99000 * load*load;
    fade = 0.5 * (0.25 + 0.75 * heat) * (0.5 + 0.5 * load);

    ringOffset += rotation;
    if (ringOffset >= numLEDs * period)
        ringOffset -= numLEDs * period;
    else if (ringOffset < 0)
        ringOffset += numLEDs * period;
}

void RingLights::updateIdle() {
    for (uint16_t i=0; i<numLEDs; i++) {
        mixIdle(ringPixels[i], i);
    }
}

void RingLights::updateRing() {  // float values range 0.0-1.0
    updateContext();

    for (uint8_t c=0; c<=(numLEDs / 8); c++) {
        if (random(100000) <= entropy) {
            uint16_t i = random(numLEDs);
            if (ringFlameForce[i] < 100.0)
                ringFlameForce[i] = 200.0 - ringFlameForce[i];
            else 
                ringFlameForce[i] = 100.0 + 0.25 * (ringFlameForce[i] - 100.0);
//            mixFlame(ringPixels[i], ringFlameForce[i], heat, 0.33);
        }
    }
    for (uint16_t i=0; i<numLEDs; i++) {
        if (ringFlameForce[i] > 0.0)
            ringFlameForce[i] *= 0.9 * (1.0 - ((entropy/150000.0) * (ringFlameForce[i] / 200.0)));
        if (ringFlameForce[i] <= 1.0)
            ringFlameForce[i] = 0.0;
    }
}

void RingLights::setSensors(float _heat, float _load, float _rpm) {
    settingHeat = _heat;
    settingLoad = _load;
    settingRpm = _rpm;
}

void RingLights::setFps(float _fps) {
    fpsAvg = _fps;
}

void RingLights::loopStep() {
    updateRing();
    displayRing();
}

