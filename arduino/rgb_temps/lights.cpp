#include "lights.h"


float randFloat() {
    return random(512) / 511.0;
}

float mixValues(float firstValue, float secondValue, float strength) {
    return (1.0 - strength) * firstValue + strength * secondValue;
}

float fract(float x) { return x - int(x); }

float mix(float a, float b, float t) { return a + (b - a) * t; }

float step(float e, float x) { return x < e ? 0.0 : 1.0; }

float* hsv2rgb(float h, float s, float b, float* rgb) {
  rgb[0] = b * mix(1.0, constrain(abs(fract(h + 1.0) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  rgb[1] = b * mix(1.0, constrain(abs(fract(h + 0.6666666) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  rgb[2] = b * mix(1.0, constrain(abs(fract(h + 0.3333333) * 6.0 - 3.0) - 1.0, 0.0, 1.0), s);
  return rgb;
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
    strip->setBrightness(255);

    displayRing();
}

void RingLights::mixFlame(Color& outColor, float flameForce, float heat, float dim=1.0) {  // flameForce 0.0-200.0
//    heat = 0.5 + 0.3398 * atan(20.0 * (heat - 0.5));
    flameForce = dim * (0.5 + 0.5 * heat) * (100.0 - abs(flameForce - 100.0)) / 100.0;
    Color flameColor = Color::fromMix(ringFlameCoolColor, ringFlameHotColor, heat);
    flameColor.mixWith(ringFlameIdleColor, idleMix);
    outColor.mixWith(flameColor, flameForce);
}

// TODO: Consider making this function signature a generic interface for more effects (per pixel calculation?)
void RingLights::mixIdle(Color& outColor, float pos, float offset, float mixStrength=1.0) {
    Color idleColor = Color::fromHSV(fmod((pos + offset) / numLEDs, 1.0), 1.0, max(0.33, min(1.0, load*2)));
    outColor.mixWith(idleColor, idleMix * mixStrength);
}

void RingLights::displayRing() {
    for (uint16_t i=0; i<numLEDs; i++) {
        float oi = i + ringOffset;
        float pixOffset = oi - int(oi);
        uint16_t srcPix0 = uint16_t(oi) % numLEDs;
        uint16_t srcPix1 = (uint16_t(oi)+1) % numLEDs;
        Color mix = Color::fromMix(ringPixels[srcPix0], ringPixels[srcPix1], pixOffset);
        mixIdle(mix, i, ringOffset * 0.5);
        mixFlame(mix, ringFlameForce[i], heat, 1.0 - (0.5 * randFloat() * load*load));
        mix *= ringBrightness;
        uint8_t r = max(0.0, min(255.0, mix.r));  // perceived brightness is ca. logarithmic
        uint8_t g = max(0.0, min(255.0, mix.g));
        uint8_t b = max(0.0, min(255.0, mix.b));
        strip->setPixelColor(i, strip->gamma32(strip->Color(r, g, b)));
    }
    strip->show();
}

void RingLights::updateContext() {
    invSmooth = 1.0 / settingSmoothing;
    heat = mixValues(heat, settingHeat, invSmooth);
    load = mixValues(load, settingLoad, invSmooth);
    rpm = mixValues(rpm, settingRpm, invSmooth);
    
    invLoad = 1.0 - load;
    invHeat = 1.0 - heat;
    rotation = 0.75 * rpm * (1.0 - 0.5 * invLoad*invLoad);
    entropy = 99000 * load * load;
    fade = 0.5 * (0.25 + 0.75 * heat) * (0.5 + 0.5 * load);
    idleMix = max(0.0, min(1.0, 2.0 * (0.5 - (1.0 - invLoad * invHeat))));
}

void RingLights::updateRing() {  // float values range 0.0-1.0
    updateContext();
  
    ringOffset -= rotation;
    if (ringOffset >= numLEDs * 10.0)
        ringOffset -= numLEDs * 10.0;
    else if (ringOffset < 0)
        ringOffset += numLEDs * 10.0;
        
    int period = max(8, min(32, numLEDs)) / 2;  // TODO: Apply max 32 somewhere on the divisor so to obtain semi-fixed-length repeat
    Color ringHeatMix = Color::fromMix(ringCoolColor, ringHotColor, heat);
    
    for (uint16_t i=0; i<numLEDs; i++) {
        Color mix = Color(ringHeatMix);
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

