#include <math.h>
#include <Adafruit_NeoPixel.h>
#include "fast_hsv2rgb.h"



/* ------------------------------- CONSTANTS ------------------------------- */


#define DEFAULT_STRIP_TYPE  NEO_GRB + NEO_KHZ800

#define RING_BASE_COLOR         0.0,   0.0,   0.0
#define RING_COOL_COLOR         0.0,  95.0, 127.0
#define RING_HOT_COLOR        191.0,   0.0,   0.0
#define RINGFLAME_IDLE_COLOR  255.0, 255.0, 255.0
#define RINGFLAME_COOL_COLOR    0.0,   0.0, 255.0
#define RINGFLAME_HOT_COLOR   255.0, 191.0,   0.0
#define SETTING_SMOOTHING        64
#define INITIAL_VALUES          0.5



/* -------------------------------- CLASSES -------------------------------- */


float randFloat();

float mixValues(float firstValue, float secondValue, float strength);

class Color {
    public:
        float r, g, b;

        Color() {
            r = 0.0; g = 0.0; b = 0.0;  
        }
        Color(float _r, float _g, float _b) {
            set(_r, _g, _b);
        }
        void set(float _r, float _g, float _b) {
            r = _r; g = _g; b = _b;
        }
        Color operator *= (Color const &other) {
            r *= other.r; g *= other.g; b *= other.b;
        }
        Color operator *= (float const other) {
            r *= other; g *= other; b *= other;
        }
        Color operator * (Color const &other) {
            Color result = Color(r, g, b);
            result *= other;
            return result;
        }
        Color operator * (float const other) {
            Color result = Color(r, g, b);
            result *= other;
            return result;
        }
        void mixColors(Color& outColor, Color& firstColor, Color& secondColor, float strength) {
            outColor.r = mixValues(firstColor.r, secondColor.r, strength);
            outColor.g = mixValues(firstColor.g, secondColor.g, strength);
            outColor.b = mixValues(firstColor.b, secondColor.b, strength);
        }
        void setMixed(Color& firstColor, Color& secondColor, float strength) {
            mixColors(*this, firstColor, secondColor, strength);
        }
        static Color fromMix(Color& firstColor, Color& secondColor, float strength) {
            Color newColor;
            newColor.setMixed(firstColor, secondColor, strength);
            return newColor;
        }
        void mixWith(Color& secondColor, float strength) {
            setMixed(*this, secondColor, strength);
        }
        static Color fromHSV(float _h, float _s, float _v) {
            uint16_t h = _h * HSV_HUE_MAX;
            uint8_t s = _s * HSV_SAT_MAX, v = _v * HSV_VAL_MAX;
            uint8_t r, g, b;
            fast_hsv2rgb_32bit(h, s, v, &r, &g, &b);
            return Color(r, g, b);
        }
};


// TODO: Add more light effects
// TODO: Add idle effect mode (like rainbow, when load & temp < threshold%)

class RingLights {
    private:
        uint16_t stripPin, numLEDs;
        Adafruit_NeoPixel* strip;

        // Update Context
        float invSmooth = 1.0 / SETTING_SMOOTHING;
        float invHeat = 1.0 - INITIAL_VALUES;
        float invLoad = 1.0 - INITIAL_VALUES;
        float invRpm = 1.0 - INITIAL_VALUES;
        float rotation = 0.0;
        float entropy = 0.0;
        float fade = 0.0;
        float idleMix = 0.0;
        const uint8_t idleSlowdown = 4;
        float fpsAvg = 30.0;

        void mixFlame(Color& outColor, float flameForce, float heat, float dim=1.0);
        void mixIdle(Color& outColor, float pos, float offset, float mixStrength);
        void updateContext();

    public:
        Color* ringPixels;
        float ringOffset = 0.0;
        Color ringBaseColor = Color(RING_BASE_COLOR);
        Color ringCoolColor = Color(RING_COOL_COLOR);
        Color ringHotColor  = Color(RING_HOT_COLOR);
        float* ringFlameForce;
        Color ringFlameIdleColor = Color(RINGFLAME_IDLE_COLOR);
        Color ringFlameCoolColor = Color(RINGFLAME_COOL_COLOR);
        Color ringFlameHotColor  = Color(RINGFLAME_HOT_COLOR);
        float ringBrightness = 1.0;

        uint16_t settingSmoothing = SETTING_SMOOTHING;
        float settingHeat = INITIAL_VALUES, settingLoad = INITIAL_VALUES, settingRpm = INITIAL_VALUES;
        float heat, load, rpm;

        RingLights();
        RingLights(uint16_t stripPin, uint16_t numLEDs, neoPixelType stripType=DEFAULT_STRIP_TYPE);
        void initRing();
        void displayRing();
        void updateRing();
        void setSensors(float _heat, float _load, float _rpm);
        void setFps(float _fps);
        void loopStep();
};

