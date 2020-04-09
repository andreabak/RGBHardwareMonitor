#include "lights.h"



/* ------------------------------- CONSTANTS ------------------------------- */


// TODO: Consider allowing to set these parameters directly from python config
const uint8_t ringsCount = 2;
RingLights* rings[ringsCount];

void setupRings() {
    rings[0] = new RingLights(2, 16, DEFAULT_STRIP_TYPE);
    rings[1] = new RingLights(4, 13, DEFAULT_STRIP_TYPE);
}



/* ------------------------------- MAIN CODE ------------------------------- */


uint8_t mode = 1;
const unsigned int readDelay = 1;

// TODO: Skip fps and print(s) when not debugging
unsigned int lastus = micros();
float fps = 0.0;
float fpsAvg = 0.0;
const float fpsAvgSamples = 300.0;

void setup() {
    Serial.begin(115200);
    Serial.flush();
    Serial.setTimeout(readDelay);
    setupRings();
}

// TODO: Fix Serial connect crash/reset
void loop() {  // TODO: Implement commands to set custom colors, then save in Flash/EEPROM
    if (Serial.available()) {  // TODO: Validate input
        uint8_t rawMode = Serial.parseInt();
        if (rawMode != 0) {
            Serial.setTimeout(100);
            mode = rawMode;
            uint8_t ringId = Serial.parseInt();
            if (!ringId || ringId > ringsCount) {
                Serial.print("Invalid ring id: "); Serial.println(ringId);
            } else {
                uint8_t rawHeat = Serial.parseInt();
                uint8_t rawLoad = Serial.parseInt();
                uint8_t rawRpm = Serial.parseInt();
                float inHeat = max(0.0, min(1.0, (rawHeat / 255.0)));
                float inLoad = max(0.0, min(1.0, (rawLoad / 255.0)));
                float inRpm  = max(0.0, min(1.0, (rawRpm / 255.0)));
                Serial.print("Parsed input (mode: "); Serial.print(mode);
                            Serial.print(", ring: "); Serial.print(ringId);
                            Serial.print(", heat: "); Serial.print(inHeat);
                            Serial.print(", load: "); Serial.print(inLoad);
                            Serial.print(", rpm: "); Serial.print(inRpm); Serial.println(")");
                rings[ringId-1]->setSensors(inHeat, inLoad, inRpm);
            }
            Serial.setTimeout(readDelay);
            Serial.print("Current fps: "); Serial.print(fps);
            Serial.print(", average fps: "); Serial.println(fpsAvg);
        }
        Serial.flush();
    }
    for (uint8_t i=0; i<ringsCount; i++)
        rings[i]->loopStep();
    unsigned int currus = micros();
    fps = 1000000.0 / (currus - lastus);
    fpsAvg = mixValues(fpsAvg, fps, 1.0 / fpsAvgSamples);
    lastus = currus;
}
