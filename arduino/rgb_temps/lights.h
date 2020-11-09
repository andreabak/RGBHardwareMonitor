#include <math.h>
#include <Adafruit_NeoPixel.h>
#include "fast_hsv2rgb.h"



/* ------------------------------- CONSTANTS ------------------------------- */


#define DEFAULT_STRIP_TYPE  NEO_GRB + NEO_KHZ800

#define RING_BASE_COLOR         0.0,   0.0,   0.0
#define RING_HOT_COLOR        191.0,   0.0,   0.0
#define RINGFLAME_HOT_COLOR   255.0, 159.0,   0.0
#define SETTING_SMOOTHING        64
#define INITIAL_VALUES          0.5

#define GAMMA_TABLE_SIZE 512
const uint8_t PROGMEM _GammaTable[GAMMA_TABLE_SIZE] = {  /* gamma = 1.4 */
  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   1,   1,   1,   1,   1,   1,
  2,   2,   2,   2,   2,   2,   3,   3,   3,   3,   3,   4,   4,   4,   4,   5,
  5,   5,   5,   5,   6,   6,   6,   6,   7,   7,   7,   7,   8,   8,   8,   9,
  9,   9,   9,  10,  10,  10,  10,  11,  11,  11,  12,  12,  12,  13,  13,  13,
 13,  14,  14,  14,  15,  15,  15,  16,  16,  16,  17,  17,  17,  18,  18,  18,
 19,  19,  19,  20,  20,  20,  21,  21,  21,  22,  22,  22,  23,  23,  23,  24,
 24,  24,  25,  25,  26,  26,  26,  27,  27,  27,  28,  28,  28,  29,  29,  30,
 30,  30,  31,  31,  32,  32,  32,  33,  33,  33,  34,  34,  35,  35,  35,  36,
 36,  37,  37,  37,  38,  38,  39,  39,  40,  40,  40,  41,  41,  42,  42,  42,
 43,  43,  44,  44,  45,  45,  45,  46,  46,  47,  47,  48,  48,  48,  49,  49,
 50,  50,  51,  51,  52,  52,  52,  53,  53,  54,  54,  55,  55,  56,  56,  56,
 57,  57,  58,  58,  59,  59,  60,  60,  61,  61,  62,  62,  62,  63,  63,  64,
 64,  65,  65,  66,  66,  67,  67,  68,  68,  69,  69,  70,  70,  71,  71,  72,
 72,  73,  73,  74,  74,  74,  75,  75,  76,  76,  77,  77,  78,  78,  79,  79,
 80,  80,  81,  81,  82,  82,  83,  84,  84,  85,  85,  86,  86,  87,  87,  88,
 88,  89,  89,  90,  90,  91,  91,  92,  92,  93,  93,  94,  94,  95,  95,  96,
 97,  97,  98,  98,  99,  99, 100, 100, 101, 101, 102, 102, 103, 103, 104, 105,
105, 106, 106, 107, 107, 108, 108, 109, 109, 110, 111, 111, 112, 112, 113, 113,
114, 114, 115, 116, 116, 117, 117, 118, 118, 119, 119, 120, 121, 121, 122, 122,
123, 123, 124, 125, 125, 126, 126, 127, 127, 128, 129, 129, 130, 130, 131, 131,
132, 133, 133, 134, 134, 135, 136, 136, 137, 137, 138, 139, 139, 140, 140, 141,
141, 142, 143, 143, 144, 144, 145, 146, 146, 147, 147, 148, 149, 149, 150, 150,
151, 152, 152, 153, 153, 154, 155, 155, 156, 156, 157, 158, 158, 159, 160, 160,
161, 161, 162, 163, 163, 164, 164, 165, 166, 166, 167, 168, 168, 169, 169, 170,
171, 171, 172, 173, 173, 174, 174, 175, 176, 176, 177, 178, 178, 179, 179, 180,
181, 181, 182, 183, 183, 184, 185, 185, 186, 186, 187, 188, 188, 189, 190, 190,
191, 192, 192, 193, 194, 194, 195, 195, 196, 197, 197, 198, 199, 199, 200, 201,
201, 202, 203, 203, 204, 205, 205, 206, 207, 207, 208, 209, 209, 210, 211, 211,
212, 213, 213, 214, 215, 215, 216, 217, 217, 218, 219, 219, 220, 221, 221, 222,
223, 223, 224, 225, 225, 226, 227, 227, 228, 229, 229, 230, 231, 231, 232, 233,
233, 234, 235, 235, 236, 237, 237, 238, 239, 240, 240, 241, 242, 242, 243, 244,
244, 245, 246, 246, 247, 248, 249, 249, 250, 251, 251, 252, 253, 253, 254, 255};



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


uint8_t applyGamma(float input);


// TODO: Add more light effects
// TODO: Add idle effect mode (like rainbow, when load & temp < threshold%)

class RingLights {
    private:
        uint16_t stripPin, numLEDs;
        Adafruit_NeoPixel* strip;
        uint16_t period = 5;

        // Update Context
        float invSmooth = 1.0 / SETTING_SMOOTHING;
        float invHeat = 1.0 - INITIAL_VALUES;
        float invLoad = 1.0 - INITIAL_VALUES;
        float invRpm = 1.0 - INITIAL_VALUES;
        float rotation = 0.0;
        float entropy = 0.0;
        float fade = 0.0;
        float fpsAvg = 30.0;

        void mixFlame(Color& outColor, Color& idleColor, float flameForce, float heat, float dim=1.0);
        Color makeIdle(float pos, float offset=0.0);
        void mixIdle(Color& outColor, float pos, float offset, float mixStrength);
        void mixDim(Color& outColor, float pos, float offset, float mixStrength);
        void updateIdle();
        void updateContext();

    public:
        Color* ringPixels;
        float rotationBaseSpeed = 8.0;
        float ringOffset = 0.0;
        Color ringBaseColor = Color(RING_BASE_COLOR);
        Color ringHotColor  = Color(RING_HOT_COLOR);
        float* ringFlameForce;
        Color ringFlameHotColor  = Color(RINGFLAME_HOT_COLOR);
        float ringBrightness = 1.0;
        float idleBrightness = 0.5;
        bool idleDynamic = true;
        uint8_t dimSpeedup = 4;

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

