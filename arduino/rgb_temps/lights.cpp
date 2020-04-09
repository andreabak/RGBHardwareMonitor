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

    displayRing();
}

void RingLights::mixFlame(Color& outColor, float flameForce, float heat, float dim=1.0) {  // flameForce 0.0-200.0
//    heat = 0.5 + 0.3398 * atan(20.0 * (heat - 0.5));
    flameForce = dim * (0.5 + 0.5 * heat) * (100.0 - abs(flameForce - 100.0)) / 100.0;
    Color flameColor = Color::fromMix(ringFlameCoolColor, ringFlameHotColor, heat);
    outColor.mixWith(flameColor, flameForce);
}

void RingLights::displayRing() {
    for (uint16_t i=0; i<numLEDs; i++) {
        float oi = i + ringOffset;
        float pixOffset = oi - int(oi);
        uint16_t srcPix0 = uint16_t(oi) % numLEDs;
        uint16_t srcPix1 = (uint16_t(oi)+1) % numLEDs;
        Color mix = Color::fromMix(ringPixels[srcPix0], ringPixels[srcPix1], pixOffset);
        mixFlame(mix, ringFlameForce[i], heat, (1.0 - 0.5 * randFloat() * load));
        mix *= ringBrightness;
        uint8_t r = max(0.0, min(255.0, mix.r));  // perceived brightness is ca. logarithmic
        uint8_t g = max(0.0, min(255.0, mix.g));
        uint8_t b = max(0.0, min(255.0, mix.b));
        strip->setPixelColor(i, strip->gamma32(strip->Color(r, g, b)));
    }
    strip->show();
}

void RingLights::updateRing() {  // float values range 0.0-1.0
    float invSmooth = 1.0 / settingSmoothing;
    heat = mixValues(heat, settingHeat, invSmooth);
    load = mixValues(load, settingLoad, invSmooth);
    rpm = mixValues(rpm, settingRpm, invSmooth);

    float invLoad = 1.0 - load;
    float rotation = 0.75 * rpm * (1.0 - invLoad*invLoad);
    float entropy = 99000 * load * load;
    float fade = 0.75 * (0.25 + 0.75 * heat) * (0.5 + 0.5 * load);
  
    ringOffset -= rotation;
    if (ringOffset >= numLEDs)
        ringOffset -= numLEDs;
    else if (ringOffset < 0)
        ringOffset += numLEDs;
    
    for (uint16_t i=0; i<numLEDs; i++) {
        Color mix = Color::fromMix(ringCoolColor, ringHotColor, heat);
        int period = max(8, min(32, numLEDs)) / 2;
        float baseDim = abs(((int(i) % period) - (period / 2)) / float(period / 2));
        baseDim *= (1.0 - 0.125 * randFloat());
        mix.mixWith(ringBaseColor, baseDim);
        float iFade = 2 * fade * (0.75 - 0.5 * baseDim);
        ringPixels[i].mixWith(mix, iFade);
    }

    for (uint8_t c=0; c<=(numLEDs / 8); c++) {
        if (random(100000) <= entropy) {
            uint16_t i = random(numLEDs);
            if (ringFlameForce[i] < 100.0)
                ringFlameForce[i] = 200.0 - ringFlameForce[i];
            else 
                ringFlameForce[i] = 100.0 + 0.25 * (ringFlameForce[i] - 100.0);
            mixFlame(ringPixels[i], ringFlameForce[i], heat, 0.33);
        }
    }
    for (uint16_t i=0; i<numLEDs; i++) {
        if (ringFlameForce[i] > 0.0)
            ringFlameForce[i] *= 0.975 * (1.0 - ((entropy/150000.0) * (ringFlameForce[i] / 200.0)));
        if (ringFlameForce[i] <= 1.0)
            ringFlameForce[i] = 0.0;
    }
}

void RingLights::setSensors(float _heat, float _load, float _rpm) {
    settingHeat = _heat;
    settingLoad = _load;
    settingRpm = _rpm;
}

void RingLights::loopStep() {
    updateRing();
    displayRing();
}

